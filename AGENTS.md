# Agent Development Guide

## CRITICAL: Think mode
When the user says **think mode** (or "thing mode"), I only think: no code changes, no file edits, no running commands. I reason and respond in text only.

## MANDATORY First Actions

**Ask the user interactively:**

1. **App deployment target:**
   > "Do you have an existing Databricks app you want to deploy to, or should we create a new one? If existing, what's the app name?"

   *Note: New apps should use the `agent-*` prefix (e.g., `agent-data-analyst`) unless the user specifies otherwise.*

2. **If the user mentions memory, conversation history, or persistence:**
   > "For memory capabilities, do you have an existing Lakebase instance? If so, what's the instance name?"

**Then check authentication status by running `databricks auth profiles`.**

This helps you understand:
- Which Databricks profiles are configured
- Whether authentication is already set up
- Which profile to use for subsequent commands

If no profiles exist or `.env` is missing, guide the user through running `uv run quickstart` to set up authentication and configuration. See the **quickstart** skill for details.

## Understanding User Goals

**Ask the user questions to understand what they're building:**

1. **What is the agent's purpose?** (e.g., data analyst assistant, customer support, code helper)
2. **What data or tools does it need access to?**
   - Databases/tables (Unity Catalog)
   - Documents for RAG (Vector Search)
   - Natural language data queries (Genie Spaces)
   - External APIs or services
3. **Any specific Databricks resources they want to connect?**

Use `uv run discover-tools` to show them available resources in their workspace, then help them select the right ones for their use case. **See the `add-tools` skill for how to connect tools and grant permissions.**

## Handling Deployment Errors

**If `databricks bundle deploy` fails with "An app with the same name already exists":**

Ask the user: "I see there's an existing app with the same name. Would you like me to bind it to this bundle so we can manage it, or delete it and create a new one?"

- **If they want to bind**: See the **deploy** skill for binding steps
- **If they want to delete**: Run `databricks apps delete <app-name>` then deploy again

---

## Available Skills

**Before executing any task, read the relevant skill file in `.claude/skills/`** - they contain tested commands, patterns, and troubleshooting steps.

| Task | Skill | Path |
|------|-------|------|
| First-time auth + MLflow | **quickstart** | `.claude/skills/quickstart/SKILL.md` |
| Workspace setup (all resources) | **setup** | `.claude/skills/setup/SKILL.md` |
| Find tools/resources | **discover-tools** | `.claude/skills/discover-tools/SKILL.md` |
| Deploy to Databricks | **deploy** | `.claude/skills/deploy/SKILL.md` |
| Add tools & permissions | **add-tools** | `.claude/skills/add-tools/SKILL.md` |
| Run/test locally | **run-locally** | `.claude/skills/run-locally/SKILL.md` |
| Modify agent code | **modify-agent** | `.claude/skills/modify-agent/SKILL.md` |
| Configure Lakebase storage | **lakebase-setup** | `.claude/skills/lakebase-setup/SKILL.md` |
| Add memory capabilities | **agent-memory** | `.claude/skills/agent-memory/SKILL.md` |

**Note:** All agent skills are located in `.claude/skills/` directory.

> **Adding Memory?** The **lakebase-setup** and **agent-memory** skills help you add conversation history or persistent user memory to this agent. For pre-configured memory, see the `agent-langgraph-short-term-memory` or `agent-langgraph-long-term-memory` templates.

---

## Quick Commands

| Task | Command |
|------|---------|
| First-time auth + MLflow | `uv run quickstart` |
| Workspace setup (all resources) | `uv run setup` |
| Check all resources | `uv run setup --check` |
| Discover tools | `uv run discover-tools` |
| Run locally (build + serve) | `uv run start-app` |
| Run locally with live reload (dev) | `./scripts/start_local.sh` |
| Restart dev stack (kill ports + fresh start) | `./scripts/restart_local.sh` |
| Deploy | `databricks bundle deploy && databricks bundle run agent_edf_trading_assistant` |
| View logs | `databricks apps logs <app-name> --follow` |

### Dev mode and restart/rerun (instructions for me)

- **When the user wants live frontend updates (no manual reload):** I run `./scripts/start_local.sh` from the project root. The script starts backend (8000), Node API (3001), and frontend (3000) with port cleanup. Frontend: http://localhost:3000. Stop with Ctrl+C. To **restart** (kill listeners on 8000/3000/3001 and run again), use `./scripts/restart_local.sh`.
- **When the user asks to "run the app" or "run locally" without specifying dev:** I use `uv run start-app` (after quickstart if needed). I use `./scripts/start_local.sh` when they want the full local stack with live reload.
- **When to restart/rerun:** I tell the user to rerun the same command (or I rerun it) when: (1) they change `.env` (e.g. API_PROXY, MLFLOW_EXPERIMENT_ID, profile), (2) they pull changes that affect backend or frontend deps or scripts, (3) one of the processes exits with an error and they want a clean state. For frontend-only or backend-only code edits in dev mode, no restart is needed (HMR / --reload handle it).

---

## Key Files

| File | Purpose |
|------|---------|
| `agent_server/agent.py` | Agent logic, model, instructions, MCP servers |
| `agent_server/start_server.py` | FastAPI server + MLflow setup |
| `agent_server/evaluate_agent.py` | Agent evaluation with MLflow scorers |
| `databricks.yml` | Bundle config & resource permissions |
| `scripts/quickstart.py` | One-command setup script |
| `scripts/start_app.py` | Run backend and frontend; skips build if pre-built dist exists (`--rebuild` to force) |
| `scripts/start_local.sh` | Full local stack: backend (8000) + Node API (3001) + Vite (3000), port cleanup |
| `scripts/restart_local.sh` | Kill processes on 8000/3000/3001, then `exec start_local.sh` |
| `scripts/discover_tools.py` | Discovers available workspace resources |

---

## Agent Framework Capabilities

> **IMPORTANT:** When adding any tool to the agent, you MUST also grant permissions in `databricks.yml`. See the **add-tools** skill for required steps and examples.

**Tool Types:**
1. **Unity Catalog Function Tools** - SQL UDFs managed in UC with built-in governance
2. **Agent Code Tools** - Defined directly in agent code for REST APIs and low-latency operations
3. **MCP Tools** - Interoperable tools via Model Context Protocol (Databricks-managed, external, or self-hosted)

**Built-in Tools:**
- **system.ai.python_exec** - Execute Python code dynamically within agent queries (code interpreter)

**Common Patterns:**
- **Structured data retrieval** - Query SQL tables/databases
- **Unstructured data retrieval** - Document search and RAG via Vector Search
- **Code interpreter** - Python execution for analysis via system.ai.python_exec
- **External connections** - Integrate services like Slack via HTTP connections

Reference: https://docs.databricks.com/aws/en/generative-ai/agent-framework/
