import os
import sys
from pathlib import Path
from typing import AsyncGenerator, Optional

import mlflow
from databricks.sdk import WorkspaceClient
from databricks_langchain import ChatDatabricks, DatabricksMCPServer, DatabricksMultiServerMCPClient
from langchain.agents import create_agent
from mlflow.genai.agent_server import invoke, stream
from mlflow.types.responses import (
    ResponsesAgentRequest,
    ResponsesAgentResponse,
    ResponsesAgentStreamEvent,
    to_chat_completions_input,
)

from agent_server.utils import (
    get_databricks_host_from_env,
    process_agent_astream_events,
)

mlflow.langchain.autolog()
sp_workspace_client = WorkspaceClient()


def init_mcp_client(workspace_client: WorkspaceClient) -> DatabricksMultiServerMCPClient:
    host_name = get_databricks_host_from_env()
    servers = [
        DatabricksMCPServer(
            name="system-ai",
            url=f"{host_name}/api/2.0/mcp/functions/system/ai",
        ),
    ]
    genie_space_id = os.environ.get("AMADEUS_GENIE_CHECKIN", "").strip()
    if genie_space_id:
        servers.append(
            DatabricksMCPServer(
                name="genie-checkin",
                url=f"{host_name}/api/2.0/mcp/genie/{genie_space_id}",
                workspace_client=workspace_client,
            ),
        )
    return DatabricksMultiServerMCPClient(servers)


def _get_pdf_report_tool():
    """Load the PDF report tool from tools/pdf-report (pdf_tool.py)."""
    project_root = Path(__file__).resolve().parents[1]
    pdf_report_dir = project_root / "tools" / "pdf-report"
    if str(pdf_report_dir) not in sys.path:
        sys.path.insert(0, str(pdf_report_dir))
    from pdf_tool import pdf_report_tool
    return pdf_report_tool


def _get_email_report_tool():
    """Load the email report tool from tools/email-report (email_tool.py)."""
    project_root = Path(__file__).resolve().parents[1]
    email_report_dir = project_root / "tools" / "email-report"
    if str(email_report_dir) not in sys.path:
        sys.path.insert(0, str(email_report_dir))
    from email_tool import send_email_report_tool
    return send_email_report_tool


async def init_agent(workspace_client: Optional[WorkspaceClient] = None):
    mcp_client = init_mcp_client(workspace_client or sp_workspace_client)
    mcp_tools = await mcp_client.get_tools()
    pdf_tool = _get_pdf_report_tool()
    email_report_tool = _get_email_report_tool()
    tools = list(mcp_tools) + [pdf_tool, email_report_tool]
    return create_agent(tools=tools, model=ChatDatabricks(endpoint="databricks-gpt-5-2"))


@invoke()
async def non_streaming(request: ResponsesAgentRequest) -> ResponsesAgentResponse:
    outputs = [
        event.item
        async for event in streaming(request)
        if event.type == "response.output_item.done"
    ]
    return ResponsesAgentResponse(output=outputs)


def _default_logo_path() -> str:
    """Default logo path on the Volume (same as data/upload_img_to_volume.py)."""
    explicit = os.environ.get("DEFAULT_LOGO_PATH", "").strip()
    if explicit:
        return explicit
    spec = os.environ.get("AMADEUS_UNITY_CATALOG_SCHEMA", "").strip()
    if "." in spec:
        catalog, schema = spec.split(".", 1)
        return f"/Volumes/{catalog}/{schema}/reports/logos/default/logo.png"
    return "/Volumes/main/default/reports/logos/default/logo.png"


def _load_system_prompt() -> str:
    path = Path(__file__).resolve().parents[1] / "prompt" / "main.prompt"
    if path.exists():
        content = path.read_text(encoding="utf-8").strip()
        return content.replace("{{DEFAULT_LOGO_PATH}}", _default_logo_path())
    return ""


@stream()
async def streaming(
    request: ResponsesAgentRequest,
) -> AsyncGenerator[ResponsesAgentStreamEvent, None]:
    agent = await init_agent()
    user_messages = to_chat_completions_input([i.model_dump() for i in request.input])
    system_content = _load_system_prompt()
    messages = (
        {"messages": [{"role": "system", "content": system_content}] + user_messages}
        if system_content
        else {"messages": user_messages}
    )

    async for event in process_agent_astream_events(
        agent.astream(input=messages, stream_mode=["updates", "messages"])
    ):
        yield event
