# Better Deploy — Faster, Lighter Deployment

This document describes improvements to reduce deploy time, upload size, and app startup time. See [deploy.md](deploy.md) for the base deployment guide.

---

## Current State

### deploy.sh flow

1. Sync `databricks.yml` / `app.yaml` from `.env.local`
2. Bind existing app if present
3. `bundle validate`
4. `bundle deploy` (uploads `source_code_path: ./`)
5. `bundle run` (starts app)
6. `grant_app_tables.py`, `authorize_warehouse_for_app.py`

**No pre-build:** The bundle uploads source as-is. No build step runs before deploy.

### app.yaml command

```yaml
command: ["uv", "run", "start-app"]
```

### start_app.py behavior (lines 175–184)

On every app start:

1. `npm install`
2. `npm run build` (= `db:migrate` + `build:client` + `build:server`)
3. `npm run start` (Node server from `dist/index.mjs`)

So every app start runs a full npm install and build on the container. That is the main cost.

### No .databricksignore

`source_code_path: ./` uploads the entire project tree, including `.venv`, `node_modules`, etc., unless Databricks ignores them by default.

---

## Proposed Improvements

### 1. Pre-build in deploy.sh, skip build in start_app (high impact)

**Change deploy.sh** — before `bundle deploy`:

```bash
echo "Building frontend..."
(cd e2e-chatbot-app-next && npm ci && npm run build) || {
  echo "Warning: Frontend build failed. App will build on start."
}
```

**Change start_app.py** — add `--prod` (or env `SKIP_BUILD=1`) that skips the `npm install` / `npm run build` loop and only runs `npm run start`. The app must already have `dist/` from the pre-build.

**Change app.yaml**:

```yaml
command: ["uv", "run", "start-app", "--prod"]
```

**Result:** Build runs once per deploy instead of every app start. Faster startup after deploy.

---

### 2. Add .databricksignore (medium impact)

Create `.databricksignore` at project root to exclude:

```
.venv/
node_modules/
e2e-chatbot-app-next/node_modules/
e2e-chatbot-app-next/client/node_modules/
e2e-chatbot-app-next/server/node_modules/
e2e-chatbot-app-next/packages/*/node_modules/

__pycache__/
*.py[cod]
*.egg-info/
.pytest_cache/
.coverage
htmlcov/

.git/
.github/
.cursor/
.claude/
*.md
!ARCHITECTURE.md
docs/
reference/
e2e-chatbot-app-next/tests/
*.test.ts
*.spec.ts

*.log
backend.log
frontend.log
node.log
.env
.env.local
.env.*.local

.idea/
.vscode/
*.swp
```

**Result:** Smaller uploads, faster `bundle deploy`.

---

### 3. Restart-only mode (low effort)

**Change deploy.sh** — add `--restart-only` that skips `bundle deploy` and only runs `bundle run`:

```bash
if [[ "$1" == "--restart-only" ]]; then
  echo "Restarting app (no deploy)..."
  databricks bundle run agent_edf_trading_assistant -t "$TARGET"
  exit 0
fi
```

**Usage:** `./deploy/deploy.sh --restart-only` when only restarting (e.g. env change). No upload.

---

### 4. Optional: build:deploy script (skip db:migrate)

`npm run build` runs `db:migrate` first. In the deployed app, `migrate.ts` exits 0 when no DB is configured, but it still runs.

Add to `e2e-chatbot-app-next/package.json`:

```json
"build:deploy": "npm run build:client && npm run build:server"
```

Use `npm run build:deploy` in deploy.sh instead of `npm run build` to avoid the migration step entirely.

---

### 5. Add grant_app_functions to deploy.sh

`deploy/deploy.md` §2.3 notes that `grant_app_functions.py` is not called by `deploy.sh`. Add it after `grant_app_tables`:

```bash
uv run python deploy/grant/grant_app_functions.py "$APP_NAME" --schema "$SCHEMA" || {
  echo "Warning: grant_app_functions.py failed..."
}
```

---

## Summary

| Improvement              | Impact                    | Effort |
|-------------------------|---------------------------|--------|
| Pre-build + --prod      | Much faster app startup   | Medium |
| .databricksignore       | Smaller uploads           | Low    |
| --restart-only          | Faster restarts           | Low    |
| build:deploy             | Minor cleanup             | Low    |
| grant_app_functions     | Avoid manual permission   | Low    |

---

## Local dev (unchanged)

`./scripts/start_local.sh` already uses:

- `uv run start-server --reload` (backend)
- `npm run dev:built` (server)
- `npm run dev:client` (Vite HMR)

Use `start_local.sh` for day-to-day work; deploy only when testing in the Databricks Apps environment.
