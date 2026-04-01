#!/usr/bin/env bash
# Run all grant scripts for the app service principal.
# Run from project root: ./deploy/grant/run_all_grants.sh [APP_NAME]
#
# Grants:
#   - UC tables (SELECT) via grant_app_tables.py
#   - UC functions/procedures (EXECUTE) via grant_app_functions.py
#   - SQL warehouse (CAN_USE) via authorize_warehouse_for_app.py
#   - KA serving endpoints (CAN_QUERY) via grant_ka_endpoints_for_app.py
#   - Genie space (CAN_RUN) for user + app SP via grant_genie_space_permissions.py
#
# Uses DBX_APP_NAME and UNITY_CATALOG_SCHEMA from .env.local by default.
set -e

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

[ -f "$ROOT/.env.local" ] && set -a && source "$ROOT/.env.local" && set +a

APP_NAME="${1:-${DBX_APP_NAME:-agent-edf-trading-assistant}}"
SCHEMA="${UNITY_CATALOG_SCHEMA:-edf.template}"

echo "Running all grants for app: $APP_NAME (schema: $SCHEMA)"
echo ""

echo "1. Granting UC table access..."
uv run python deploy/grant/grant_app_tables.py "$APP_NAME" --schema "$SCHEMA" || {
  echo "Warning: grant_app_tables.py failed" >&2
  exit 1
}

echo ""
echo "2. Granting UC functions/procedures access..."
uv run python deploy/grant/grant_app_functions.py "$APP_NAME" --schema "$SCHEMA" || {
  echo "Warning: grant_app_functions.py failed" >&2
  exit 1
}

echo ""
echo "3. Granting CAN_USE on SQL warehouse..."
uv run python deploy/grant/authorize_warehouse_for_app.py "$APP_NAME" || {
  echo "Warning: authorize_warehouse_for_app.py failed" >&2
  exit 1
}

echo ""
echo "4. Granting CAN_QUERY on KA endpoints..."
uv run python deploy/grant/grant_ka_endpoints_for_app.py "$APP_NAME" || {
  echo "Warning: grant_ka_endpoints_for_app.py failed" >&2
}

echo ""
echo "5. Granting Genie space permissions (current user + app SP)..."
"$ROOT/.venv/bin/python" deploy/grant/grant_genie_space_permissions.py --app-name "$APP_NAME" || {
  echo "Warning: grant_genie_space_permissions.py failed" >&2
}

echo ""
echo "Done. All grants applied."
