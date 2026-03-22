import os
from pathlib import Path
from typing import AsyncGenerator

import mlflow
from databricks_langchain import ChatDatabricks, DatabricksMCPServer, DatabricksMultiServerMCPClient
from langchain.agents import create_agent
from mlflow.genai.agent_server import invoke, stream
from mlflow.types.responses import (
    ResponsesAgentRequest,
    ResponsesAgentResponse,
    ResponsesAgentStreamEvent,
    to_chat_completions_input,
)

from agent_server.utils import get_databricks_host_from_env, process_agent_astream_events
from tools.placeholder_tool import placeholder_tool
from tools.query_example_data import query_example_data
from tools.query_knowledge_assistant import query_knowledge_assistant

# New same-domain tools: append to tools in init_agent and implement under tools/<name>/
mlflow.langchain.autolog()


def _get_genie_host() -> str:
    """Return Databricks host for Genie MCP URL."""
    host = os.environ.get("DATABRICKS_HOST", "").strip().rstrip("/")
    if host:
        return host
    h = get_databricks_host_from_env()
    return (h or "").rstrip("/")


async def init_agent():
    tools = [
        query_knowledge_assistant,
        query_example_data,
        placeholder_tool,
    ]

    # Add Genie MCP tools (natural language SQL over edf.chatbot tables)
    genie_room = os.environ.get("EDF_TRADING_GENIE_ROOM", "").strip()
    if genie_room:
        host = _get_genie_host()
        if host:
            genie_server = DatabricksMCPServer(
                url=f"{host}/api/2.0/mcp/genie/{genie_room}",
                name="genie_trading",
            )
            mcp_client = DatabricksMultiServerMCPClient([genie_server])
            mcp_tools = await mcp_client.get_tools()
            tools = list(tools) + list(mcp_tools)

    endpoint = os.environ.get("AGENT_MODEL_ENDPOINT", "").strip()
    if not endpoint:
        raise ValueError("AGENT_MODEL_ENDPOINT must be set (e.g. claude-sonnet-4-6, databricks-gpt-5-2)")
    return create_agent(tools=tools, model=ChatDatabricks(endpoint=endpoint))


@invoke()
async def non_streaming(request: ResponsesAgentRequest) -> ResponsesAgentResponse:
    outputs = [
        event.item
        async for event in streaming(request)
        if event.type == "response.output_item.done"
    ]
    return ResponsesAgentResponse(output=outputs)


def _load_system_prompt() -> str:
    base = Path(__file__).resolve().parents[1] / "prompt"
    main_path = base / "main.prompt"
    kb_path = base / "knowledge.base"
    content = main_path.read_text(encoding="utf-8").strip() if main_path.exists() else ""
    kb_content = kb_path.read_text(encoding="utf-8").strip() if kb_path.exists() else ""
    return content.replace("{{KNOWLEDGE_BASE}}", kb_content)


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
    except BaseException as e:
        # Unwrap ExceptionGroup (e.g. from MCP/anyio TaskGroup) so the real error is surfaced
        if isinstance(e, BaseExceptionGroup) and len(e.exceptions) == 1:
            raise e.exceptions[0] from e
        raise
