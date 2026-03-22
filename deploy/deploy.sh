#!/usr/bin/env bash
# Deploy app to Databricks Apps via bundle (DAB).
# Run from project root: ./deploy/deploy.sh
#
# Uses databricks bundle deploy which uploads source from local (source_code_path: ./)
# and properly links it to the app. App name comes from target: use -t template for
# agent-langgraph (see databricks.yml targets.template).
#
# If "App already exists" error: bind first:
#   databricks bundle deployment bind agent_langgraph agent-langgraph -t template --auto-approve
set -e

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

# Load .env.local for UNITY_CATALOG_SCHEMA
[ -f "$ROOT/.env.local" ] && set -a && source "$ROOT/.env.local" && set +a

# Default target template -> agent-langgraph; override with DEPLOY_TARGET env
TARGET="${DEPLOY_TARGET:-template}"

echo "Deploying (target: $TARGET)..."
echo ""

# Sync databricks.yml from .env.local (warehouse, genie, endpoint, app name)
uv run python deploy/sync_databricks_yml_from_env.py 2>/dev/null || true

# Ensure OpenAI secret exists for voice transcription (reads OPENAI_API_KEY from .env.local)
if [ -n "${OPENAI_API_KEY:-}" ]; then
  ./deploy/setup_openai_secret.sh 2>/dev/null || echo "Warning: setup_openai_secret.sh failed (voice transcription may not work)"
fi

# If app exists but isn't bound to bundle, bind it first
case "$TARGET" in
  template) APP_NAME="agent-langgraph" ;;
  prod)     APP_NAME="agent-langgraph" ;;
  *)        APP_NAME="agent-langgraph" ;;
esac
if databricks apps get "$APP_NAME" --output json &>/dev/null; then
  echo "Binding existing app $APP_NAME to bundle..."
  databricks bundle deployment bind agent_langgraph "$APP_NAME" -t "$TARGET" --auto-approve 2>/dev/null || true
fi

echo "Validating bundle..."
databricks bundle validate -t "$TARGET"

# Verify backend imports before deploying (fail fast on SyntaxError etc.)
uv run python -c "from agent_server.start_server import app" || { echo "Backend import failed. Fix before deploying."; exit 1; }

echo "Deploying (bundle uploads source and links to app)..."
databricks bundle deploy -t "$TARGET"

echo "Starting app..."
databricks bundle run agent_langgraph -t "$TARGET"

echo ""
echo "Granting UC table access to app service principal..."
SCHEMA="${UNITY_CATALOG_SCHEMA:-edf.template}"
uv run python deploy/grant/grant_app_tables.py "$APP_NAME" --schema "$SCHEMA" || {
  echo "Warning: grant_app_tables.py failed (tables may not exist yet). Run manually: uv run python deploy/grant/grant_app_tables.py $APP_NAME --schema $SCHEMA"
}

echo ""
echo "Granting CAN_USE on SQL warehouse to app service principal..."
uv run python deploy/grant/authorize_warehouse_for_app.py "$APP_NAME" || {
  echo "Warning: authorize_warehouse_for_app.py failed. Run manually: uv run python deploy/grant/authorize_warehouse_for_app.py $APP_NAME"
}

echo ""
echo "Done."
APP_URL=$(databricks apps get "$APP_NAME" --output json 2>/dev/null | jq -r '.url // empty')
[ -n "$APP_URL" ] && echo "App URL: $APP_URL"
