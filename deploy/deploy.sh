#!/usr/bin/env bash
# Deploy app to Databricks Apps via bundle (DAB).
# Run from project root: ./deploy/deploy.sh
#
# Uses databricks bundle deploy which uploads source from local (source_code_path: ./)
# and links it to the app. App name comes from DBX_APP_NAME in .env.local (default:
# agent-edf-trading-assistant); see databricks.yml targets.template.
#
# If "App already exists" error: bind first (bundle app key = DBX_APP_NAME with - -> _):
#   databricks bundle deployment bind agent_edf_trading_assistant "$DBX_APP_NAME" -t template --auto-approve
set -e

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

# Python: use project venv only (no `uv run` — avoids PyPI sync when offline / misconfigured).
PYTHON="${PYTHON:-$ROOT/.venv/bin/python}"
if [ ! -f "$PYTHON" ]; then
  echo "Error: $PYTHON not found. Create the venv and install the project (e.g. uv sync, or pip install -e .)." >&2
  exit 1
fi

# Load .env.local for UNITY_CATALOG_SCHEMA, DBX_APP_NAME, etc.
[ -f "$ROOT/.env.local" ] && set -a && source "$ROOT/.env.local" && set +a

# Databricks CLI: use OAuth profile when DATABRICKS_CONFIG_PROFILE is set (PAT often cannot create Apps).
# Force PAT for bundle: DEPLOY_USE_PAT=1
DBC_PROFILE=""
if [ "${DEPLOY_USE_PAT:-}" = "1" ]; then
  echo "Databricks CLI: PAT (DEPLOY_USE_PAT=1)"
  echo ""
elif [ -n "${DATABRICKS_CONFIG_PROFILE:-}" ]; then
  unset DATABRICKS_TOKEN
  unset DATABRICKS_HOST
  DBC_PROFILE="${DATABRICKS_CONFIG_PROFILE}"
  echo "Databricks CLI: profile ${DBC_PROFILE}"
  echo ""
fi

APP_NAME="${DBX_APP_NAME:-agent-edf-trading-assistant}"
# Must match resources.apps.* in databricks.yml (same as sanitized default DBX_APP_NAME)
BUNDLE_APP_KEY="${BUNDLE_APP_KEY:-agent_edf_trading_assistant}"

# Default target template; override with DEPLOY_TARGET env
TARGET="${DEPLOY_TARGET:-template}"

echo "Deploying (target: $TARGET, app: $APP_NAME)..."
echo ""

# Sync databricks.yml from .env.local (warehouse, genie, endpoint, app name)
"$PYTHON" deploy/sync_databricks_yml_from_env.py 2>/dev/null || true

# Ensure OpenAI secret exists for voice transcription (reads OPENAI_API_KEY from .env.local)
if [ -n "${OPENAI_API_KEY:-}" ]; then
  ./deploy/setup_openai_secret.sh 2>/dev/null || echo "Warning: setup_openai_secret.sh failed (voice transcription may not work)"
fi

# If app exists but isn't bound to bundle, bind it first
if databricks ${DBC_PROFILE:+-p "$DBC_PROFILE"} apps get "$APP_NAME" --output json &>/dev/null; then
  echo "Binding existing app $APP_NAME to bundle..."
  databricks ${DBC_PROFILE:+-p "$DBC_PROFILE"} bundle deployment bind "$BUNDLE_APP_KEY" "$APP_NAME" -t "$TARGET" --auto-approve 2>/dev/null || true
fi

echo "Validating bundle..."
databricks ${DBC_PROFILE:+-p "$DBC_PROFILE"} bundle validate -t "$TARGET"

# Optional: verify resources in databricks.yml exist and current identity has permissions (SDK).
#   PRE_DEPLOY_VERIFY=1 ./deploy/deploy.sh
if [ "${PRE_DEPLOY_VERIFY:-}" = "1" ]; then
  echo "Pre-deploy verify (workspace assets vs databricks.yml)..."
  "$PYTHON" deploy/pre_deploy_verify_assets.py -t "$TARGET" || exit 1
fi

# Verify backend imports before deploying (fail fast on SyntaxError etc.)
"$PYTHON" -c "from agent_server.start_server import app" || { echo "Backend import failed. Fix before deploying."; exit 1; }

echo "Deploying (bundle uploads source and links to app)..."
databricks ${DBC_PROFILE:+-p "$DBC_PROFILE"} bundle deploy -t "$TARGET"

echo "Starting app..."
databricks ${DBC_PROFILE:+-p "$DBC_PROFILE"} bundle run "$BUNDLE_APP_KEY" -t "$TARGET"

echo ""
echo "Granting UC table access to app service principal..."
SCHEMA="${UNITY_CATALOG_SCHEMA:-edf.template}"
"$PYTHON" deploy/grant/grant_app_tables.py "$APP_NAME" --schema "$SCHEMA" || {
  echo "Warning: grant_app_tables.py failed (tables may not exist yet). Run manually: $PYTHON deploy/grant/grant_app_tables.py $APP_NAME --schema $SCHEMA"
}

echo ""
echo "Granting CAN_USE on SQL warehouse to app service principal..."
"$PYTHON" deploy/grant/authorize_warehouse_for_app.py "$APP_NAME" || {
  echo "Warning: authorize_warehouse_for_app.py failed. Run manually: $PYTHON deploy/grant/authorize_warehouse_for_app.py $APP_NAME"
}

echo ""
echo "Granting Genie space permissions (current user + this app's SP)..."
"$PYTHON" deploy/grant/grant_genie_space_permissions.py --app-name "$APP_NAME" || {
  echo "Warning: grant_genie_space_permissions.py failed. For your user only (no app): $PYTHON deploy/grant/grant_genie_space_permissions.py" >&2
}

echo ""
echo "Done."
APP_URL=$(databricks ${DBC_PROFILE:+-p "$DBC_PROFILE"} apps get "$APP_NAME" --output json 2>/dev/null | jq -r '.url // empty')
[ -n "$APP_URL" ] && echo "App URL: $APP_URL"
