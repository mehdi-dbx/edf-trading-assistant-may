# Agent Chat Template – Architecture

## ASCII Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  USER (Browser)                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  e2e-chatbot-app-next                                                         │
│  ┌─────────────────┐     ┌─────────────────┐                                │
│  │ client (Vite)    │────▶│ server (Express)│                                │
│  │ React, AI SDK    │     │ /api/chat,      │                                │
│  │ 3000             │     │ /api/tables,    │                                │
│  └─────────────────┘     │ /api/events     │                                │
│                          └────────┬────────┘                                │
└───────────────────────────────────┼─────────────────────────────────────────┘
                                    │ API_PROXY
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  agent_server (FastAPI :8000)                                                │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │ agent.py  @invoke/@stream  +  prompt/main.prompt                      │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
│                                    │                                        │
│                                    ▼                                        │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │ tools/  (query_*, update_*, create_*)                                │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
└───────────────────────────────────┼─────────────────────────────────────────┘
                                    │ sql_executor
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  data/                                                                       │
│  func/*.sql (reads)   proc/*.sql (writes)   init/* (setup)                  │
└───────────────────────────────────┼─────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  Unity Catalog (Databricks)                                                  │
└─────────────────────────────────────────────────────────────────────────────┘

┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│  prompt/     │  │  scripts/     │  │  deploy/      │
│  main.prompt │  │  start_app   │  │  deploy.sh    │
│  (system)    │  │  quickstart  │  │  grant/*      │
└──────────────┘  │  reset_state  │  └──────────────┘
                  └──────────────┘
```

## Folder Blocks (Contents)

```
┌─ agent_server ───────────────────────────────────────────────────────────────┐
│ ┌─────────────────────────────────────────────────────────────────────────┐ │
│ │ agent.py          @invoke/@stream, tool wiring, system prompt load      │ │
│ │ start_server.py   FastAPI entry, /tables/*, /invocations                 │ │
│ │ utils.py          Host resolution, stream event processing (genie removed)│ │
│ │ evaluate_agent.py MLflow scorers for agent evaluation                    │ │
│ │ utils.py          Host resolution, stream event processing               │ │
│ └─────────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘

┌─ data ─────────────────────────────────────────────────────────────────────┐
│ ┌─────────────────────────────────────────────────────────────────────────┐ │
│ │ init/   Catalog, schema, tables (example_data)                          │ │
│ │ func/   Read SQL (example_query.sql)                                     │ │
│ │ proc/   (empty in template)                                              │ │
│ │ run_sql.py, sql_utils.py  Schema substitution, UC execution               │ │
│ └─────────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘

┌─ deploy ───────────────────────────────────────────────────────────────────┐
│ ┌─────────────────────────────────────────────────────────────────────────┐ │
│ │ deploy.sh                    Sync env, validate, deploy, run, grant      │ │
│ │ sync_databricks_yml_from_env.py  Sync databricks.yml, app.yaml from env │ │
│ │ grant/run_all_grants.sh      Run all grant scripts                      │ │
│ │ grant/grant_app_tables.py    UC table access for app SP                 │ │
│ │ grant/grant_app_functions.py UC function access                        │ │
│ │ grant/authorize_warehouse_for_app.py  Warehouse CAN_USE                 │ │
│ │ grant/authorize_endpoint_for_app.py    Serving endpoint CAN_QUERY        │ │
│ └─────────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘

┌─ e2e-chatbot-app-next ───────────────────────────────────────────────────────┐
│ ┌─────────────────────────────────────────────────────────────────────────┐ │
│ │ client/   React, Vite, Tailwind, AI SDK. Chat UI, TaskEventsListener    │ │
│ │ server/   Express. /api/chat, /api/tables, /api/events (SSE),           │ │
│ │           /api/reset-state. Proxies to backend                           │ │
│ │ packages/ auth, ai-sdk-providers, core, db (Drizzle/Lakebase)           │ │
│ └─────────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘

┌─ prompt ────────────────────────────────────────────────────────────────────┐
│ ┌─────────────────────────────────────────────────────────────────────────┐ │
│ │ main.prompt   Generic assistant, tool descriptions                       │ │
│ │ user.prompt   User-facing prompt template                                │ │
│ └─────────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘

┌─ scripts ───────────────────────────────────────────────────────────────────┐
│ ┌─────────────────────────────────────────────────────────────────────────┐ │
│ │ start_app.py        Backend + frontend, wait for readiness              │ │
│ │ start_local.sh      Full stack: backend 8000, Node 3001, Vite 3000     │ │
│ │ quickstart.py       Interactive setup (auth, config, deploy)             │ │
│ │ reset_state.py      Reset demo state via SQL                            │ │
│ │ init_check_dbx_env.py  Check profile, schema, warehouse, app grants     │ │
│ │ discover_tools.py   Discover workspace tools/resources                 │ │
│ └─────────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘

┌─ tools ─────────────────────────────────────────────────────────────────────┐
│ ┌─────────────────────────────────────────────────────────────────────────┐ │
│ │ query_example_data   Reads example data via UC                            │ │
│ │ placeholder_tool     Placeholder for demonstration                        │ │
│ │ sql_executor         Shared UC execution via Databricks warehouse         │ │
│ └─────────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Directory Summaries

| Directory | Purpose |
|-----------|---------|
| **agent_server** | Python backend: FastAPI `AgentServer` with `@invoke`/`@stream`, loads `prompt/main.prompt`, wires tools. Exposes `/invocations`, `/tables/*`. |
| **data** | SQL assets: `init/` (catalog, tables, Genie space), `func/` (read SQL for tools), `proc/` (write SQL for tools). |
| **deploy** | Deployment: `deploy.sh`, `sync_databricks_yml_from_env.py`, `grant/*` for app permissions (UC, warehouse, Genie, endpoint). |
| **e2e-chatbot-app-next** | Full-stack chat: React client (Vite) + Express server. Proxies `/api/*` to backend, SSE for task notifications. |
| **prompt** | System prompt: `main.prompt` for Garv agent persona, tools, response style. Loaded in `agent_server/agent.py`. |
| **scripts** | Orchestration: `start_app.py` (backend+frontend), `start_local.sh` (dev), `quickstart.py`, `reset_state.py`, `init_check_dbx_env.py`. |
| **tools** | Agent tools: `query_*` (reads via `data/func`), `update_*`/`create_*` (writes via `data/proc`). Uses `sql_executor` → Databricks warehouse. |

## Data Flow

```
User → Frontend (3000) → Node (3001) → Agent backend (8000) or Databricks
                                    → Agent + tools → UC (via data/func, data/proc)
                                    → Streamed response back
```
