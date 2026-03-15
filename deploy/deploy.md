# Databricks App Deployment Guide

This document summarizes the deployment process, lessons learned, traps to avoid, and best practices for the amadeus-checkin app (agent + e2e-chatbot-app-next frontend).

---

## 1. Prerequisites

- **Databricks CLI** authenticated (`databricks auth profiles`)
- **`.env.local`** populated (copy from `.env.example`; see Section 6)
- **Unity Catalog** schema with tables and procedures
- **SQL warehouse**, **Genie Space**, and **Foundation Model endpoint** in your workspace

---

## 2. Deployment Process (Correct Order)

### 2.0 One-time asset creation

Before first deploy, create all UC assets (catalog, schema, tables, procedures, Genie space):

```bash
uv run python data/init/create_all_assets.py
```

This runs: create_catalog_schema, init SQL (checkin_metrics, flights, checkin_agents, border_officers, border_terminals), create_genie_space, proc SQL, and verification.

### 2.1 One-time setup

1. **Sync `databricks.yml` from `.env.local`**
   ```bash
   uv run python deploy/sync_databricks_yml_from_env.py
   ```
   This updates `sql_warehouse.id`, `genie_space.space_id`, `serving_endpoint.name`, and target app name.

2. **Ensure `app.yaml` has all required env vars** (see Section 5 — **TASK_EVENTS_URL** is critical).

3. **Add resources to `databricks.yml` if missing**
   - Run `authorize_endpoint_for_app.py` if serving_endpoint is not in the bundle
   - Run `authorize_genie_for_app.py` if genie_space is not in the bundle

### 2.2 Deploy

```bash
./deploy/deploy.sh
```

Or with a specific target:
```bash
DEPLOY_TARGET=airops-checkin ./deploy/deploy.sh
```

The script:
1. Syncs `databricks.yml` from `.env.local`
2. Binds existing app if it exists (avoids "App already exists" error)
3. Validates and deploys the bundle
4. Starts the app
5. Runs `grant_app_tables.py` (UC table access)
6. Runs `authorize_warehouse_for_app.py` (warehouse CAN_USE)

### 2.3 Post-deploy grants (run manually if deploy.sh skips them)

```bash
# Tables (USE CATALOG, USE SCHEMA, ALL PRIVILEGES on tables)
uv run python deploy/grant/grant_app_tables.py agent-airops-checkin --schema mc.amadeus-checkin

# Functions and procedures (EXECUTE)
uv run python deploy/grant/grant_app_functions.py agent-airops-checkin --schema mc.amadeus-checkin

# Warehouse CAN_USE
uv run python deploy/grant/authorize_warehouse_for_app.py agent-airops-checkin
```

**Note:** `grant_app_functions.py` is not called by `deploy.sh`. Run it manually after deploy if your agent uses UC procedures (e.g. update_checkin_agent, confirm_arrival, update_border_officer, update_flight_risk).

---

## 3. Lessons Learned

| Lesson | Detail |
|--------|--------|
| **Service principal uses client ID** | Unity Catalog GRANTs use `service_principal_client_id` (UUID), not the display name. Use `retrieve_app_sp.py` to get it. |
| **Bind before deploy** | If the app already exists, run `databricks bundle deployment bind agent_langgraph agent-airops-checkin -t airops-checkin --auto-approve` before deploy. |
| **Tables and functions are separate** | Tables need `grant_app_tables.py`; functions/procedures need `grant_app_functions.py`. Both require USE CATALOG and USE SCHEMA first. |
| **Warehouse permission is separate** | The app needs CAN_USE on the SQL warehouse; `authorize_warehouse_for_app.py` does this via the Permissions API. |
| **Genie and endpoint in bundle** | The app must have `genie_space` and `serving_endpoint` resources in `databricks.yml` so the app's service principal gets CAN_RUN and CAN_QUERY. |
| **TASK_EVENTS_URL for notifications** | Task-created toasts require the agent to POST to the Node API. Without `TASK_EVENTS_URL`, notifications will not work. |

---

## 4. Traps to Avoid

| Trap | Why it fails | Fix |
|------|--------------|-----|
| **Forgetting TASK_EVENTS_URL in app.yaml** | Agent creates tasks but never notifies the frontend; "New Load Task" toast never appears. | Add `TASK_EVENTS_URL: "http://127.0.0.1:3000"` to `app.yaml` env (Node runs on CHAT_APP_PORT=3000 in deployed app). |
| **Deploying without binding** | "An app with the same name already exists" — bundle tries to create a new app. | Bind first: `databricks bundle deployment bind agent_langgraph agent-airops-checkin -t airops-checkin --auto-approve` |
| **Missing grant_app_functions** | Agent gets "permission denied" when calling UC procedures. | Run `grant_app_functions.py` after deploy. |
| **Wrong warehouse ID** | Queries fail or use wrong warehouse. | Set `DATABRICKS_WAREHOUSE_ID` in `.env.local`; sync runs before deploy. |
| **403 on Foundation Model API** | Workspace admin must enable Foundation Model APIs. | Ask admin or use a different model endpoint. |
| **DATABRICKS_HOST without https://** | SDK/CLI fails to connect. | Use `https://<workspace>.databricks.com` or `https://<workspace>.cloud.databricks.com`. |

---

## 5. app.yaml — Critical Env Vars

**TASK_EVENTS_URL** must be set for task-created notifications to work. The agent POSTs to `{TASK_EVENTS_URL}/api/events/task-created` when it creates a task; the Node server then pushes SSE to subscribed clients.

```yaml
env:
  # ... other vars ...
  - name: TASK_EVENTS_URL
    value: "http://127.0.0.1:3000"   # Node API — required for "New Load Task" toast (CHAT_APP_PORT in deployed app)
```

- **Local dev** (`./scripts/start_local.sh`): Node runs on 3001 → use `http://127.0.0.1:3001` in .env.local
- **Deployed app**: Node runs on CHAT_APP_PORT (3000) → use `http://127.0.0.1:3000`

**Other important vars in app.yaml:**
- `DATABRICKS_WAREHOUSE_ID` (or valueFrom)
- `AMADEUS_UNITY_CATALOG_SCHEMA` (or your catalog.schema, e.g. mc.amadeus-checkin)
- `AMADEUS_GENIE_CHECKIN` (Genie Space ID)
- `AGENT_MODEL_ENDPOINT`
- `API_PROXY` (for chat to reach agent)

---

## 6. .env.local Checklist

| Variable | Purpose |
|----------|---------|
| `DATABRICKS_CONFIG_PROFILE` | CLI profile (e.g. `DEFAULT`, `airops-trial`) |
| `DATABRICKS_HOST` | Workspace URL (must include `https://`) |
| `DATABRICKS_TOKEN` | PAT or OAuth token |
| `DBX_APP_NAME` | App name (e.g. `agent-airops-checkin`) |
| `AGENT_MODEL_ENDPOINT` | Foundation Model endpoint name |
| `DATABRICKS_WAREHOUSE_ID` | SQL warehouse ID for UC queries |
| `AMADEUS_UNITY_CATALOG_SCHEMA` | Catalog.schema (e.g. `mc.amadeus-checkin`) |
| `AMADEUS_GENIE_CHECKIN` | Genie Space ID |
| `MLFLOW_EXPERIMENT_ID` | For agent tracing |
| `TASK_EVENTS_URL` | Node API URL for task notifications (local: `http://127.0.0.1:3001`) |
| `API_PROXY` | Agent invocations URL (e.g. `http://localhost:8000/invocations`) |
| `OPENAI_API_KEY` | For voice transcription (Whisper). Local only; deployed app uses Databricks secret. |

**Voice transcription (deployed app):** The app needs `OPENAI_API_KEY` for Whisper. Run before first deploy:

```bash
./deploy/setup_openai_secret.sh
```

This reads `OPENAI_API_KEY` from `.env.local` and stores it in Databricks secret scope `amadeus-checkin`, key `openai-api-key`. Deploy.sh runs it automatically if the key is set.

---

## 7. Best Practices

1. **Run create_all_assets before first deploy** — Creates catalog, schema, tables, procedures, Genie space.
2. **Run sync before deploy** — `sync_databricks_yml_from_env.py` keeps `databricks.yml` aligned with `.env.local`.
3. **Use deploy.sh** — It orchestrates bind, validate, deploy, start, and grants.
4. **Run grant_app_functions after deploy** — If your agent uses UC procedures, add this step (or add it to deploy.sh).
5. **Check app URL after deploy** — `databricks apps get agent-airops-checkin --output json | jq -r '.url'`
6. **View logs on failure** — `databricks apps logs agent-airops-checkin --follow`
7. **Test locally first** — `./scripts/start_local.sh` before deploying.
8. **Document workspace-specific IDs** — Warehouse, Genie Space, and endpoint IDs vary by workspace; keep them in `.env.local`, not hardcoded.

---

## 8. File Reference

| File | Purpose |
|------|---------|
| `data/init/create_all_assets.py` | Create catalog, schema, tables, procedures, Genie space |
| `data/init/create_catalog_schema.py` | Create UC catalog and schema |
| `deploy/deploy.sh` | Main deploy script |
| `deploy/sync_databricks_yml_from_env.py` | Sync databricks.yml from .env.local |
| `deploy/grant/retrieve_app_sp.py` | Get app service principal info |
| `deploy/grant/grant_app_tables.py` | Grant UC table access to app SP |
| `deploy/grant/grant_app_functions.py` | Grant EXECUTE on functions/procedures |
| `deploy/grant/authorize_warehouse_for_app.py` | Grant CAN_USE on warehouse |
| `deploy/grant/authorize_endpoint_for_app.py` | Add serving_endpoint to databricks.yml |
| `deploy/grant/authorize_genie_for_app.py` | Add genie_space to databricks.yml |
| `app.yaml` | App env config (command, env vars) |
| `databricks.yml` | Bundle config (resources, targets) |
