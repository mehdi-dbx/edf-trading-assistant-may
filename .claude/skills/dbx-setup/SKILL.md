---
name: dbx-setup
description: "Configure workspace resources for the EDF Trading Assistant. Use when: (1) First time deploying on a new workspace, (2) User says 'setup', 'configure workspace', or 'setup environment', (3) KA endpoints need refreshing, (4) Genie space or warehouse changed, (5) User asks 'how to set up'."
---

# Workspace Setup — Interactive Guide

I run each step myself, check the result, fix errors, and tell the user what happened before moving on.

## How I execute this

I run each step via `uv run setup --step <name>`, read the output, report the result to the user, and only proceed to the next step if the current one succeeded. If a step fails, I diagnose and fix before continuing.

## Step sequence

### Step 1: Check current state first

```bash
uv run setup --check
```

Read the output. If everything passes, tell the user "All resources are configured" and ask if they want to re-configure anything specific. If some checks fail, proceed with the failing steps below.

### Step 2: DATABRICKS_HOST

```bash
uv run setup --step host
```

- **Success**: Tell user which host is configured, move to Step 3
- **Fail**: The script is interactive — if it can't run non-interactively, tell the user to set `DATABRICKS_HOST` in `.env.local` manually, then re-run

### Step 3: Authentication

```bash
uv run setup --step auth
```

- **Success**: Tell user which auth method is active (token or profile), move on
- **Fail**: Guide user to run `databricks auth login` or set `DATABRICKS_TOKEN` in `.env.local`

### Step 4: SQL Warehouse

```bash
uv run setup --step warehouse
```

- **Success**: Report warehouse name and ID
- **Fail**: Tell user to check warehouse exists and is running

### Step 5: Unity Catalog Schema

```bash
uv run setup --step schema
```

- **Success**: Report schema and table status
- **Fail**: Offer to run `uv run python data/init/create_all_assets.py` to create missing assets

### Step 6: Model Endpoint

```bash
uv run setup --step model
```

- **Success**: Report endpoint name and ready state
- **Fail**: Tell user to check serving endpoint exists (e.g. `databricks-claude-sonnet-4-6`)

### Step 7: Knowledge Assistants (critical step)

```bash
uv run setup --step ka
```

This is the most important step. It:
1. Fetches all KAs from the workspace
2. Writes `data/ka.list`
3. Syncs KA endpoints into `databricks.yml`
4. Validates prompt references

- **Success**: Report how many KAs found, whether prompt refs all resolve
- **Prompt mismatch warning**: Tell user which backtick refs in `prompt/main.prompt` don't match, and help them update the mapping table
- **No KAs found**: Tell user they need to create KAs first using the companion project [edf-trading-data](https://github.com/mehdi-dbx/edf-trading-data)
- **Fail (API error)**: Check that `DATABRICKS_HOST` and `DATABRICKS_TOKEN` are set in `.env.local`

### Step 8: Genie Space

```bash
uv run setup --step genie
```

- **Success**: Report Genie space name and ID
- **Fail**: Tell user to create a Genie space in the workspace UI first

### Step 9: MLflow Experiment

```bash
uv run setup --step mlflow
```

- **Success**: Report experiment name and ID
- **Fail**: Offer to create a new experiment

### Step 10: Final verification

```bash
uv run setup --check
```

Report the full status. If all green, tell user:
- `uv run start-app` to test locally
- `databricks bundle deploy && databricks bundle run agent_edf_trading_assistant` to deploy
- `cd deploy/grant && bash run_all_grants.sh` to grant app permissions

## Important notes

- Steps 2-9 are **interactive** (they prompt for input via stdin). When running them, use the Bash tool and let the user see and respond to prompts.
- If the user wants to skip a step, move to the next one.
- If a step needs a value the user doesn't have yet, note it and continue with other steps. Come back to it later.
- The `--check` mode is non-interactive and safe to run anytime.

## Available switches

| Command | What it does |
|---------|-------------|
| `uv run setup` | Full interactive wizard (all steps sequentially) |
| `uv run setup --check` | Non-interactive verification of all resources |
| `uv run setup --step <name>` | Run one step: `host`, `auth`, `warehouse`, `schema`, `model`, `ka`, `genie`, `mlflow`, `check` |
| `uv run setup --steps` | List all available step names |

## What gets written

| File | Written by |
|------|-----------|
| `.env.local` | All steps (env vars) |
| `data/ka.list` | `ka` step (KA endpoint mapping) |
| `databricks.yml` | `ka` step (KA resources), `genie` step (space_id) |

## Troubleshooting

| Issue | Fix |
|-------|-----|
| "DATABRICKS_HOST not set" | `uv run setup --step host` |
| "No Knowledge Assistants found" | Create KAs first with [edf-trading-data](https://github.com/mehdi-dbx/edf-trading-data) |
| Prompt refs don't match | Update `prompt/main.prompt` KA name mapping to match workspace KA display names |
| "Could not fetch KAs" | Set `DATABRICKS_HOST` and `DATABRICKS_TOKEN` in `.env.local` |
| Auth expired | `databricks auth login` |
