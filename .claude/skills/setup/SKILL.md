---
name: setup
description: "Configure workspace resources for the EDF Trading Assistant. Use when: (1) First time deploying on a new workspace, (2) User says 'setup', 'configure workspace', or 'setup environment', (3) KA endpoints need refreshing, (4) Genie space or warehouse changed, (5) User asks 'how to set up'."
---

# Workspace Setup

Interactive wizard that configures all workspace-specific resources in `.env.local` and `databricks.yml`.

## Full Setup (all steps)

```bash
uv run setup
```

Walks through: host, auth, warehouse, schema, model endpoint, KA endpoints, Genie space, MLflow.

## Quick Check (non-interactive)

```bash
uv run setup --check
```

Verifies all resources are configured and reachable. Exits with code 1 if any check fails.

## Single Step

```bash
uv run setup --step <name>
```

Available steps:

| Step | What it configures |
|------|-------------------|
| `host` | `DATABRICKS_HOST` — workspace URL |
| `auth` | `DATABRICKS_TOKEN` or `DATABRICKS_CONFIG_PROFILE` |
| `warehouse` | `DATABRICKS_WAREHOUSE_ID` — lists available, pick one |
| `schema` | `UNITY_CATALOG_SCHEMA` — verify or create UC assets |
| `model` | `AGENT_MODEL_ENDPOINT` — lists serving endpoints, pick one |
| `ka` | Knowledge Assistants — fetch from workspace, write `data/ka.list`, sync to `databricks.yml`, validate prompt refs |
| `genie` | `EDF_TRADING_GENIE_ROOM` — lists Genie spaces, pick one, updates `.env.local` + `databricks.yml` |
| `mlflow` | `MLFLOW_EXPERIMENT_ID` — keep or create new |
| `check` | Same as `--check` |

## List Steps

```bash
uv run setup --steps
```

## KA Step Details

The `ka` step is the most important — it chains 4 operations:

1. Fetches all Knowledge Assistants from the workspace REST API
2. Writes endpoint mapping to `data/ka.list`
3. Syncs KA serving_endpoint resources into `databricks.yml`
4. Validates that backtick references in `prompt/main.prompt` resolve against the new ka.list

If prompt references don't match (e.g. KA display names differ), the user needs to update `prompt/main.prompt`.

## What Gets Written

- **`.env.local`** — All env vars (host, token, warehouse ID, Genie room, experiment ID, model endpoint)
- **`data/ka.list`** — KA endpoint mapping (by KA step)
- **`databricks.yml`** — KA serving_endpoint resources + Genie space_id (by KA and Genie steps)

## After Setup

```bash
uv run start-app        # test locally
# or
databricks bundle deploy && databricks bundle run agent_edf_trading_assistant  # deploy
cd deploy/grant && bash run_all_grants.sh  # grant app permissions
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| "DATABRICKS_HOST not set" | Run `uv run setup --step host` |
| "No Knowledge Assistants found" | Create KAs first (see [edf-trading-data](https://github.com/mehdi-dbx/edf-trading-data)) |
| Prompt refs don't match | Update `prompt/main.prompt` KA name mapping to match your KA display names |
| "Could not fetch KAs" | Ensure `DATABRICKS_HOST` and `DATABRICKS_TOKEN` are set in `.env.local` |
