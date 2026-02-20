import os
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
from tools.get_current_time import get_current_time
from tools.placeholder_tool import placeholder_tool

# New same-domain tools: append to tools in init_agent and implement under tools/<name>/
mlflow.langchain.autolog()
sp_workspace_client = WorkspaceClient()


def init_mcp_client(workspace_client: WorkspaceClient) -> DatabricksMultiServerMCPClient:
    host_name = get_databricks_host_from_env()
    servers = []
    genie_turnaround_id = os.environ.get("AMADEUS_GENIE_TURNAROUND", "").strip()
    if genie_turnaround_id:
        servers.append(
            DatabricksMCPServer(
                name="genie-turnaround",
                url=f"{host_name}/api/2.0/mcp/genie/{genie_turnaround_id}",
                workspace_client=workspace_client,
            ),
        )
    return DatabricksMultiServerMCPClient(servers)


async def init_agent(workspace_client: Optional[WorkspaceClient] = None):
    mcp_client = init_mcp_client(workspace_client or sp_workspace_client)
    mcp_tools = await mcp_client.get_tools()
    tools = list(mcp_tools) + [get_current_time, placeholder_tool]
    return create_agent(tools=tools, model=ChatDatabricks(endpoint="databricks-gpt-5-2"))


@invoke()
async def non_streaming(request: ResponsesAgentRequest) -> ResponsesAgentResponse:
    outputs = [
        event.item
        async for event in streaming(request)
        if event.type == "response.output_item.done"
    ]
    return ResponsesAgentResponse(output=outputs)


def _load_system_prompt() -> str:
    path = Path(__file__).resolve().parents[1] / "prompt" / "main.prompt"
    if path.exists():
        return path.read_text(encoding="utf-8").strip()
    return ""


@stream()
async def streaming(
    request: ResponsesAgentRequest,
) -> AsyncGenerator[ResponsesAgentStreamEvent, None]:
    try:
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
    except Exception:
        raise
