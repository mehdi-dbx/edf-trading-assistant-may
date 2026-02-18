# Reference

Project reference docs and links.

---

## LangGraph MCP tool-calling agent (Databricks)

**Source:** [LangGraph MCP Tool Calling Agent](https://docs.databricks.com/gcp/en/notebooks/source/generative-ai/langgraph-mcp-tool-calling-agent.html)  
*(Same topic on AWS: [docs.databricks.com/en/notebooks/.../langgraph-mcp-tool-calling-agent.html](https://docs.databricks.com/en/notebooks/source/generative-ai/langgraph-mcp-tool-calling-agent.html))*

### Summary

- **LangGraph** – Stateful agent orchestration (durable execution, streaming, human-in-the-loop, memory).
- **MCP (Model Context Protocol)** – Lets the LLM discover and call tools via a structured API. Databricks exposes system tools (e.g. `system.ai`) over MCP.
- **Databricks stack** – `databricks-agent-core` / `databricks-agents`, `databricks-langchain`, `langchain-mcp-adapters`; agent uses `DatabricksMultiServerMCPClient` + `create_agent` + `ChatDatabricks`.

### Relevant pieces in this repo

- **Agent + MCP:** [`agent_server/agent.py`](../agent_server/agent.py) – `init_mcp_client` (e.g. `system-ai`), `create_agent(tools=..., model=ChatDatabricks(...))`, `@invoke` / `@stream`.

### External references

- [LangGraph agents + MCP (LangChain)](https://langchain-ai.github.io/langgraph/agents/mcp/)
- [MCP endpoint in Agent Server (Streamable HTTP)](https://docs.langchain.com/langgraph-platform/server-mcp)
- [langchain-mcp-adapters](https://github.com/langchain-ai/langchain-mcp-adapters) – MCP tools → LangChain tools for LangGraph.
