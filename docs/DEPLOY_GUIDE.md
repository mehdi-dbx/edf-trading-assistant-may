# Deploy EDF Trading Assistant — Quick Steps (Own Workspace)

This guide assumes the customer already has their KA data and Genie space set up in their workspace.

## Prerequisites
- Databricks CLI (`brew install databricks/tap/databricks`)
- `uv` (`brew install uv`)
- `nvm` with Node 20 (`nvm use 20`)

## 1. Clone & setup
```bash
git clone https://github.com/mehdi-dbx/edf-trading-assistant-may.git
cd edf-trading-assistant-may
uv run quickstart
```

## 2. Update KA endpoints to match your workspace

List your KA endpoints:
```bash
python scripts/list_ka_endpoints.py
```

Replace `data/ka.list` with the output, then sync to `databricks.yml`:
```bash
python deploy/sync_ka_endpoints_to_yml.py
```

## 3. Update Genie room

Set your Genie space ID in `.env.local`:
```bash
EDF_TRADING_GENIE_ROOM=<your-genie-space-id>
```

And update the `genie_space` block in `databricks.yml` with your space ID.

## 4. Update prompt KA names (if different)

If your KA display names differ from the defaults, update the mapping in `prompt/main.prompt` to match. Verify alignment:
```bash
python scripts/check_prompt_ka_names.py
```

## 5. Update warehouse & model endpoint

In `.env.local` and `databricks.yml`, set:
- `DATABRICKS_WAREHOUSE_ID` — your SQL warehouse ID
- `AGENT_MODEL_ENDPOINT` — your serving endpoint (e.g. `databricks-claude-sonnet-4-6`)
- `UNITY_CATALOG_SCHEMA` — your catalog.schema (e.g. `edf.chatbot`)

## 6. Test locally
```bash
uv run start-app
```

## 7. Deploy
```bash
databricks bundle deploy && databricks bundle run agent_edf_trading_assistant
```

## 8. Grant permissions
```bash
cd deploy/grant && bash run_all_grants.sh
```

## Key principle

Everything workspace-specific lives in 3 places: `data/ka.list`, `.env.local`, and `databricks.yml`. Get those right and the rest just works.

## Common issues

- **"App already exists"** on deploy: run `databricks apps delete agent-edf-trading-assistant` and retry, or bind the existing app
- **WeasyPrint error on macOS**: `brew install pango cairo`
- **No Genie results**: verify `EDF_TRADING_GENIE_ROOM` is set in `.env.local`
- **KA name mismatch**: run `python scripts/check_prompt_ka_names.py` to verify prompt names match endpoints
