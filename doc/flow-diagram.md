# Simplified ASCII flow diagram

One-word/short technical components. Skeleton after cleanup: Frontend → Node → FastAPI → Agent (MCP + new tools TBD).

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│ FRONTEND                                                                                  │
│   [Vite]  [React]  ──►  [Node] (proxy)  ──►  [FastAPI] (start_server)                     │
└─────────────────────────────────────────────────────────────────────────────────────────┘
        │
        │ chat
        ▼
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│ AGENT (LangChain/LangGraph, MLflow, ChatDatabricks)                                       │
│   optional: [MCP] (Genie)   │   New tools (TBD)                                           │
└─────────────────────────────────────────────────────────────────────────────────────────┘
```

## Block legend (short)

| Block | Meaning |
|-------|--------|
| Vite / React | Frontend app (Vite dev server, React UI) |
| Node | Node server (proxy to FastAPI for chat) |
| FastAPI | Backend (start_server): agent invocations |
| Agent | LangChain/LangGraph agent, MLflow, ChatDatabricks; optional MCP (Genie); new same-domain tools TBD |

## Note

Old report/email features (PDF, email, download ZIP) were removed. New agent tools in the same domain are to be added under `tools/<name>/` and registered in `agent_server/agent.py`.
