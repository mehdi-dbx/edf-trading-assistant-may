# EDF Trading Assistant

Weather intelligence chatbot for energy market professionals. Answers questions about weather forecasts, degree days (HDD/CDD), teleconnection indices (EPO, PNA, NAO, WPO, MJO), and their implications for US power markets (PJM, ISONE, MISO).

Built on Databricks Agent Framework with LangGraph, deployed as a Databricks App.

## What's in the box

- **LangGraph agent** powered by Claude Sonnet via Databricks Model Serving
- **15 Knowledge Assistants** for document-based Q&A (daily outlooks, CWG wind, teleconnections, ENSO, MJO, degree days)
- **Genie MCP** for natural-language SQL over 14 Delta tables in Unity Catalog
- **Full-screen chat UI** (React/Vite) with KA source cards, citations, and code blocks
- **Interactive setup wizard** (`uv run setup`) that configures all workspace resources end-to-end

## Quick Start

```bash
git clone https://github.com/mehdi-dbx/edf-trading-assistant.git
cd edf-trading-assistant
uv run setup
uv run start-app
```

## Prerequisites

| Requirement | Install |
|-------------|---------|
| Python 3.11+ | Runtime |
| [uv](https://docs.astral.sh/uv/) | `brew install uv` |
| [nvm](https://github.com/nvm-sh/nvm) + Node 20 | `nvm install 20` |
| [Databricks CLI](https://docs.databricks.com/dev-tools/cli/install.html) | `brew install databricks` |
| Databricks workspace with KAs and Genie space | Where the agent connects |

### ![Step 1](https://img.shields.io/badge/Step_1-Clone-blue?style=for-the-badge)

```bash
git clone https://github.com/mehdi-dbx/edf-trading-assistant.git
cd edf-trading-assistant
```

### ![Step 2](https://img.shields.io/badge/Step_2-Setup_Workspace-blue?style=for-the-badge)

![Setup Wizard](https://img.shields.io/badge/Recommended-Run_Setup_Wizard-ff6600?style=for-the-badge)

```bash
uv run setup
```

Single command that walks you through every workspace resource interactively (auth, warehouse, schema, model, KAs, Genie, MLflow):

| Step | Resource | What it does |
|------|----------|--------------|
| 1 | `DATABRICKS_HOST` | Set workspace URL |
| 2 | Auth | Token or CLI profile |
| 3 | `DATABRICKS_WAREHOUSE_ID` | Lists warehouses, pick one |
| 4 | `UNITY_CATALOG_SCHEMA` | Verify or create UC schema + tables |
| 5 | `AGENT_MODEL_ENDPOINT` | Lists serving endpoints, pick one |
| 6 | **Knowledge Assistants** | Fetches KAs, writes `ka.list`, syncs `databricks.yml`, validates prompt |
| 7 | `EDF_TRADING_GENIE_ROOM` | Lists Genie spaces, pick one, updates `.env.local` + `databricks.yml` |
| 8 | `MLFLOW_EXPERIMENT_ID` | Keep existing or create new |

To verify everything is configured:

```bash
uv run setup --check
```

To re-run a single step:

```bash
uv run setup --step ka      # just the KA chain
uv run setup --step genie   # just the Genie space
uv run setup --steps         # list all available steps
```

### ![Step 3](https://img.shields.io/badge/Step_3-Run_Locally-green?style=for-the-badge)

```bash
uv run start-app
```

Opens the chat UI at http://localhost:8000. The frontend ships pre-built -- `npm run build` is skipped automatically. Use `uv run start-app --rebuild` to force a frontend rebuild after modifying frontend code.

For local development with live reload:

```bash
./scripts/start_local.sh    # backend (8000) + Node API (3001) + Vite (3000)
```

### ![Step 4](https://img.shields.io/badge/Step_4-Deploy-blueviolet?style=for-the-badge)

```bash
databricks bundle deploy && databricks bundle run agent_edf_trading_assistant
```

Then grant the app service principal access to all resources:

```bash
cd deploy/grant && bash run_all_grants.sh
```

### ![Step 5](https://img.shields.io/badge/Step_5-Query-blueviolet?style=for-the-badge)

Databricks Apps are only queryable via OAuth token (not PAT):

```bash
TOKEN=$(databricks auth token | jq -r '.access_token')
curl -X POST <app-url>/invocations \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{ "input": [{ "role": "user", "content": "What are HDD forecasts for PJM?" }], "stream": true }'
```

## Architecture

```
[React Chat UI]  -->  [Node API :3001]  -->  [FastAPI Backend :8000]
                                                      |
                                              [LangGraph Agent]
                                                |           |
                                         [Genie MCP]  [Knowledge Assistants]
                                         SQL over       15 KA endpoints for
                                         Delta tables   document-based Q&A
```

## Data Sources

### Genie (structured data -- primary for quantitative queries)

Natural-language SQL over Delta tables in `edf.chatbot`:

| Table | Content |
|-------|---------|
| `bronze_degree_days_forecast` | HDD/CDD forecasts by region (PJM, ISONE, MISO) |
| `bronze_degree_days_historical` | Historical HDD/CDD by region |
| `bronze_degree_days_normals` | 10-year normals by region |
| `epo_forecast_bronze` / `epo_historical_bronze` | EPO index |
| `pna_forecast_bronze` / `pna_historical_bronze` | PNA index |
| `nao_forecast_bronze` / `nao_historical_bronze` | NAO index |
| `bronze_wpo_forecast` / `bronze_wpo_historical` | WPO index |
| `bronze_mjo_phase_forecast` / `bronze_mjo_phase_historical` | MJO phase |

### Knowledge Assistants (narrative -- for document-based Q&A)

| Topic | KA Name |
|-------|---------|
| Daily Outlooks (NOAA/CPC) | `daily_outlook_2005_2009` through `daily_outlook_2020_2025` |
| CWG Wind Forecasts | `cwg-wind-generation-forecasts` |
| Degree Days | `degree-days-energy-trading-assistant` |
| EPO | `epo-east-pacific-oscillation-trading-assistant` |
| PNA | `pna-teleconnection-trading-assistant` |
| NAO | `nao-north-atlantic-oscillation-trading-data` |
| WPO | `wpo-west-pacific-oscillation-trading-data` |
| MJO | `mjo-madden-julian-oscillation-agent` |
| MJO Phase | `mjo-phase-energy-trading-assistant` |
| ENSO | `ENSO-Climate-Trading-Assistant` |
| Global Tropics | `global-tropics-hazards-cpc-briefings` |
| Climate Learnings | `climate-teleconnections-learnings` |

## Project Structure

```
agent_server/
  agent.py               # LangGraph agent: tools, model, streaming
  start_server.py        # FastAPI server + MLflow + REST endpoints
  evaluate_agent.py      # Agent evaluation with MLflow scorers

tools/
  query_knowledge_assistant.py  # KA query tool (routes by display name)
  ka_loader.py                  # Parses data/ka.list
  sql_executor.py               # SQL against Databricks warehouse
  get_current_time.py           # Temporal awareness for the LLM

prompt/
  main.prompt            # System prompt (data source mapping, rules)
  style.prompt           # Voice and conduct guidelines
  knowledge.base         # Inline knowledge base

app/                     # React/Vite chat UI (pre-built)
data/                    # Table definitions, KA endpoint list, data loaders
deploy/                  # Deploy scripts + permission grants
scripts/                 # Dev scripts: quickstart, setup, start_local
```

## Key Files

| File | Purpose |
|------|---------|
| `agent_server/agent.py` | Agent logic, model, instructions, MCP servers |
| `data/ka.list` | KA endpoint mapping (generated by setup) |
| `databricks.yml` | Bundle config: app, KA endpoints, warehouse, Genie |
| `app.yaml` | Databricks App runtime env vars |
| `.env.local` | Local workspace-specific config (gitignored) |
| `prompt/main.prompt` | System prompt with KA + Genie routing rules |

## Companion Project

KA data provisioning (volume ingestion, KA creation, data dictionary) lives in a separate repo: [edf-trading-data](https://github.com/mehdi-dbx/edf-trading-data)

## Common Issues

| Issue | Solution |
|-------|----------|
| "App already exists" on deploy | `databricks apps delete agent-edf-trading-assistant` and retry |
| WeasyPrint error on macOS | `brew install pango cairo` |
| No Genie results | Verify `EDF_TRADING_GENIE_ROOM` in `.env.local` |
| KA name mismatch | `uv run setup --step ka` to re-fetch and validate |
| 302 redirect querying deployed app | Use OAuth token, not PAT |
| Auth token expired | `databricks auth login` |
