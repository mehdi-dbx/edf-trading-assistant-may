# Import Check Before Deploy

Before starting the local stack or deploying to Databricks, we run:

```bash
uv run python -c "from agent_server.start_server import app"
```

**Why:** Catches startup-breaking errors (e.g. `SyntaxError`, import failures) before the backend starts or before we upload the bundle. Fails fast instead of starting and crashing.

**Where it runs:**
- `scripts/start_local.sh` – before `uv run start-server`
- `deploy/deploy.sh` – before `databricks bundle deploy`

**If it fails:** Fix the error (often in `tools/` or `agent_server/`), then retry.
