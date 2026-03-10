#!/usr/bin/env bash
# Deploy app to Databricks Apps via bundle (DAB).
# Run from project root: ./deploy/deploy.sh
#
# Uses databricks bundle deploy which uploads source from local (source_code_path: ./)
# and properly links it to the app. App name comes from target: use -t airops-checkin for
# agent-airops-checkin (see databricks.yml targets.airops-checkin).
#
# If "App already exists" error: bind first:
#   databricks bundle deployment bind agent_langgraph agent-airops-checkin -t airops-checkin --auto-approve
set -e

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

# Load .env.local for AMADEUS_UNITY_CATALOG_SCHEMA
[ -f "$ROOT/.env.local" ] && set -a && source "$ROOT/.env.local" && set +a

# Default target airops-checkin -> agent-airops-checkin; override with DEPLOY_TARGET env
TARGET="${DEPLOY_TARGET:-airops-checkin}"

echo "Deploying (target: $TARGET)..."
echo ""

# Sync databricks.yml from .env.local (warehouse, genie, endpoint, app name)
uv run python deploy/sync_databricks_yml_from_env.py 2>/dev/null || true

# If app exists but isn't bound to bundle, bind it first
case "$TARGET" in
  airops-checkin) APP_NAME="agent-airops-checkin" ;;
  airops)        APP_NAME="agent-airops" ;;
  prod)          APP_NAME="agent-langgraph" ;;
  *)             APP_NAME="agent-langgraph" ;;
esac
if databricks apps get "$APP_NAME" --output json &>/dev/null; then
  echo "Binding existing app $APP_NAME to bundle..."
  databricks bundle deployment bind agent_langgraph "$APP_NAME" -t "$TARGET" --auto-approve 2>/dev/null || true
fi

echo "Validating bundle..."
databricks bundle validate -t "$TARGET"

echo "Deploying (bundle uploads source and links to app)..."
databricks bundle deploy -t "$TARGET"

echo "Starting app..."
databricks bundle run agent_langgraph -t "$TARGET"

echo ""
echo "Granting UC table access to app service principal..."
SCHEMA="${AMADEUS_UNITY_CATALOG_SCHEMA:-mc.amadeus-checkin}"
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
