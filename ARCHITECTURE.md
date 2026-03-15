# Amadeus Check-in – Architecture

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
│ │ start_server.py   FastAPI entry, /tables/*, /current-time, /invocations │ │
│ │ genie_capture.py  Captures Genie SQL to data/genie-capture-sql/          │ │
│ │ evaluate_agent.py MLflow scorers for agent evaluation                    │ │
│ │ utils.py          Host resolution, stream event processing               │ │
│ └─────────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘

┌─ data ─────────────────────────────────────────────────────────────────────┐
│ ┌─────────────────────────────────────────────────────────────────────────┐ │
│ │ init/   Catalog, schema, tables (checkin_agents, flights, etc.),        │ │
│ │         Genie space, MLflow experiment                                  │ │
│ │ func/   Read SQL (staffing, metrics, flights, agents, etc.)              │ │
│ │ proc/   Write SQL (update_checkin_agents, update_flight_risk, etc.)      │ │
│ │ genie-capture-sql/  Captured Genie-generated SQL                          │ │
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
│ │ grant/authorize_genie_for_app.py       Genie space CAN_RUN              │ │
│ │ grant/authorize_endpoint_for_app.py    Serving endpoint CAN_QUERY        │ │
│ └─────────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘

┌─ e2e-chatbot-app-next ───────────────────────────────────────────────────────┐
│ ┌─────────────────────────────────────────────────────────────────────────┐ │
│ │ client/   React, Vite, Tailwind, AI SDK. Chat UI, checkin cards,        │ │
│ │           TaskEventsListener, role switch (Agent/Manager)                 │ │
│ │ server/   Express. /api/chat, /api/tables, /api/events (SSE),           │ │
│ │           /api/current-time, /api/reset-state. Proxies to backend       │ │
│ │ packages/ auth, ai-sdk-providers, core, db (Drizzle/Lakebase)           │ │
│ └─────────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘

┌─ prompt ────────────────────────────────────────────────────────────────────┐
│ ┌─────────────────────────────────────────────────────────────────────────┐ │
│ │ main.prompt   Garv AI Ops Advisor persona, tool descriptions,            │ │
│ │               response style, dashboard refresh blocks                    │ │
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
│ │ query_*   query_egate_availability, query_flights_at_risk,             │ │
│ │           query_checkin_performance_metrics, query_available_agents,     │ │
│ │           query_border_officer_staffing, query_checkin_agent_staffing,   │ │
│ │           query_staffing_duties, query_border_terminal_details, etc.     │ │
│ │ update_*  update_checkin_agent, update_flight_risk, update_border_officer │ │
│ │ create_*  create_border_incident, create_checkin_incident               │ │
│ │ get_current_time, back_to_normal, confirm_arrival                       │ │
│ │ sql_executor  Shared UC execution via Databricks warehouse               │ │
│ └─────────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Directory Summaries

| Directory | Purpose |
|-----------|---------|
| **agent_server** | Python backend: FastAPI `AgentServer` with `@invoke`/`@stream`, loads `prompt/main.prompt`, wires tools. Exposes `/invocations`, `/tables/*`, `/current-time`. |
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
