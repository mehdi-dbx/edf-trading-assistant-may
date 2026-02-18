# Agent MCP and OBO (on-behalf-of)

## Workspace clients

- **`sp_workspace_client = WorkspaceClient()`** — Uses the app’s credentials (e.g. PAT from env). All MCP calls (system-ai, Genie, etc.) run as that identity. Use for local dev or when you don’t need per-user identity.

- **`get_user_workspace_client()`** — Uses the **calling user’s** token from the request (`x-forwarded-access-token` when the agent is behind model serving). Use when deployed so that MCP tools (e.g. Genie) run **on behalf of the end user** (OBO): correct UC permissions and audit.

**When to switch:** If you deploy the agent and want Genie (or other MCPs) to execute as the requesting user, pass `get_user_workspace_client()` into the MCP client for those servers instead of `sp_workspace_client`. See reference notebook `reference/langgraph-mcp-tool-calling-agent.ipynb` (OBO setup with `ModelServingUserCredentials()` or request-scoped token).
