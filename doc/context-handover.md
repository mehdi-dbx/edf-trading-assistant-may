# Context Handover – Amadeus Check-in

Purpose: empower a new Cursor instance to grasp what the project does and how it is articulated technically, so you can keep the same mechanisms and build new use cases (new data, Genie, user flows, tools).

---

## 1. Project Purpose

AI Ops Advisor for airport check-in: chat with agent, dashboard tables, suggested actions. Supports **Manager** and **Agent** roles: Manager monitors performance, recommends redeploy, assigns staffing duties; Agent receives duties, confirms arrival. The agent detects anomalies (check-in or border control), recommends staff redeploy, executes operator decisions via tools, and refreshes the dashboard. Built on Databricks (Unity Catalog, Genie, SQL Warehouse), LangChain agent, and a React chat + dashboard UI.

---

## 2. Folder Outline

| Folder | Contents |
| ------ | -------- |
| **agent_server/** | `agent.py` (tools, MCP, prompt load), `start_server.py` (FastAPI), `utils.py`, `evaluate_agent.py` |
| **data/** | `init/create_*.sql` (table DDL + seed), `proc/*_procedure.sql` (stored procedures), `create_genie_space.py`, `run_sql.py`, `csv_to_delta.py`, `verify_tables.py` |
| **prompt/** | `main.prompt` – agent system prompt, flow instructions, block formats, Genie query templates |
| **scripts/** | `start_local.sh` (full stack), `reset_state.py` (re-run create SQL), `quickstart.py`, `start_app.py` |
| **tools/** | Agent tools: `sql_executor.py`, `create_checkin_incident`, `create_border_incident`, `back_to_normal`, `update_checkin_agent`, `update_border_officer`, `update_flight_risk`, `confirm_arrival`, `placeholder_tool` |
| **e2e-chatbot-app-next/** | Cloned template: client (Vite/React), server (Express), packages (auth, ai-sdk-providers, chat-template/core) |

---

## 3. Critical Glue Pieces

- **API_PROXY** – Node chat routes to `http://localhost:8000/invocations`; agent runs on FastAPI 8000
- **prompt/main.prompt** – Drives agent behavior; add new flows and block types here
- **tools/sql_executor.py** – Shared Databricks `statement_execution`; all SQL tools use it
- **agent_server/agent.py** – Registers tools, MCP client (Genie), loads prompt; add new tools here
- **e2e-chatbot-app-next/server/src/routes/tables.ts** – `ALLOWED_TABLES`, SQL per table; add new tables and allowlist
- **e2e-chatbot-app-next/client/src/lib/response-blocks.ts** – Parses agent text into blocks; add new block types and regex
- **e2e-chatbot-app-next/client/src/components/message.tsx** – Renders blocks (RefreshTableTrigger, FollowUpActions, Cards)

---

## 4. .env.local and start_local.sh

**Required vars (in .env.local):**

| Var | Purpose |
| --- | ------- |
| `DATABRICKS_HOST` | Workspace URL |
| `DATABRICKS_TOKEN` | PAT for API calls |
| `DATABRICKS_WAREHOUSE_ID` | SQL warehouse for statements |
| `AMADEUS_UNITY_CATALOG_SCHEMA` | e.g. `mc.amadeus-checkin` (catalog.schema) |
| `AMADEUS_GENIE_CHECKIN` | Genie space ID (from `python data/create_genie_space.py`) |
| `API_PROXY` | `http://localhost:8000/invocations` (set by start_local.sh if unset) |
| `TASK_EVENTS_URL` | Node server URL for staffing event webhook (default `http://127.0.0.1:3001`) |

**start_local.sh:**

- Sources `.env` then `.env.local`; exports `API_PROXY` for Node
- Kills ports 8000, 3000, 3001 first; builds Node server before start
- Starts: backend (8000) via `uv run start-server --reload`, Node (3001) with `API_PROXY` passed to `npm run dev:built`, frontend (3000) via Vite
- Waits for backend and Node to be ready before continuing

---

## 5. UI Stack and Layout

**Stack:** Vite + React, React Router, Tailwind, shadcn/ui (SidebarProvider, etc.)

**Layout:**

- `ChatLayout` wraps `ChatSendMessageProvider`, `RoleProvider`, `TableRefreshProvider`; contains `TaskEventsListener`, `AppSidebar` + `SidebarInset` (Outlet) + `EmbeddedChatPanel` (right)
- Routes: `/` and `/chat/:id` both render `HomePage` (dashboard + chat)
- `HomePage`: TableCard grid (checkin_metrics, flights, checkin_agents, border_officers, border_terminals), MetricsOverview
- Chat: `EmbeddedChatPanel` uses `@chat-template/core` + `myProvider` (Databricks AI SDK); streams from API_PROXY

---

## 6. Table Refresh Mechanism

1. Agent emits `refresh_table\n{tableName}` in response text
2. `parseResponseBlocks` (response-blocks.ts) detects block, creates segment
3. `message.tsx` renders `RefreshTableTrigger` with `table={parsed.table}`
4. `RefreshTableTrigger` calls `refresh(table)` from `useTableRefresh` on mount
5. `TableRefreshContext` increments `refreshKeys[tableName]`
6. `useTableData(tableName, refreshKeys[tableName])` refetches when key changes
7. `GET /api/tables/:tableName` → Databricks SQL → `{ columns, rows }`
8. TableCard / MetricsOverview re-render

**Key files:**

- `e2e-chatbot-app-next/client/src/contexts/TableRefreshContext.tsx`
- `e2e-chatbot-app-next/client/src/contexts/RoleContext.tsx` (Manager/Agent dropdown)
- `e2e-chatbot-app-next/client/src/contexts/ChatSendMessageContext.tsx` (registerSendMessage, sendCheckTasks)
- `e2e-chatbot-app-next/client/src/hooks/useTableData.ts`
- `e2e-chatbot-app-next/client/src/components/message.tsx` (RefreshTableTrigger)
- `e2e-chatbot-app-next/server/src/routes/tables.ts`

---

## 7. Extending for New Use Cases

| Goal | Where to change |
| ---- | --------------- |
| New data | Add `create_*.sql` in data/init/, procedures in data/proc/; run via reset_state or run_sql; add to `ALLOWED_TABLES` in tables.ts; add `KEY_COLUMN_BY_TABLE` in useTableData.ts |
| New Genie | Create space with `create_genie_space.py`, add env var; optionally add MCP in agent.py |
| New tools | Add `tools/foo.py`, register in agent.py, document in prompt |
| New flows | Extend prompt with new triggers, tools, block formats |
| New blocks | Add regex + parser in response-blocks.ts, render branch in message.tsx |

---

## 8. Reference Docs

- [doc/technical-flow.md](technical-flow.md) – Exhaustive SQL, procedures, Genie queries, call graph
- [doc/business-flow.md](business-flow.md) – Business flow ASCII diagram
