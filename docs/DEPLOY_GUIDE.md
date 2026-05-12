# Deploy EDF Trading Assistant — Quick Steps (Own Workspace)

This guide assumes the customer already has their KA data and Genie space set up in their workspace.

## Prerequisites

- Databricks CLI (`brew install databricks/tap/databricks`)
- `uv` (`brew install uv`)
- `nvm` with Node 20 (`nvm use 20`)

## 1. Clone & first-time auth

```bash
git clone https://github.com/mehdi-dbx/edf-trading-assistant.git
cd edf-trading-assistant
uv run quickstart
```

## 2. Configure workspace resources

```bash
uv run setup
```

This single command walks you through everything:

- **Host + auth** — Databricks connection
- **Warehouse** — Lists available warehouses, pick one
- **UC schema** — Verify or create `edf.chatbot` tables
- **Model endpoint** — Lists serving endpoints, pick one (e.g. `databricks-claude-sonnet-4-6`)
- **KA endpoints** — Fetches all KAs from workspace, writes `data/ka.list`, syncs to `databricks.yml`, validates prompt references
- **Genie space** — Lists available spaces, pick one, updates `.env.local` + `databricks.yml`
- **MLflow experiment** — Keep existing or create new

To verify everything is configured:

```bash
uv run setup --check
```

To re-run a single step:

```bash
uv run setup --step ka
```

## 3. Update prompt KA names (if different)

If your KA display names differ from the defaults, update the mapping in `prompt/main.prompt` to match. The setup script warns about mismatches.

## 4. Test locally

```bash
uv run start-app
```

## 5. Deploy

```bash
databricks bundle deploy && databricks bundle run agent_edf_trading_assistant
```

## 6. Grant permissions

```bash
cd deploy/grant && bash run_all_grants.sh
```

## Common issues

- **"App already exists"** on deploy: run `databricks apps delete agent-edf-trading-assistant` and retry, or bind the existing app
- **WeasyPrint error on macOS**: `brew install pango cairo`
- **No Genie results**: verify `EDF_TRADING_GENIE_ROOM` is set in `.env.local`
- **KA name mismatch**: run `uv run setup --step ka` to re-fetch and validate
