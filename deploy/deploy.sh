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

# ─── Colors & icons ────────────────────────────────────────────────────────────
BOLD="\033[1m"
DIM="\033[2m"
RESET="\033[0m"
RED="\033[0;31m"
GREEN="\033[0;32m"
YELLOW="\033[0;33m"
BLUE="\033[0;34m"
CYAN="\033[0;36m"
WHITE="\033[1;37m"

IC_OK="  ✔"
IC_WARN="  ⚠"
IC_ERR="  ✘"
IC_RUN="  ›"
IC_INFO="  ℹ"
IC_ARROW="  →"

step()  { echo -e "\n${BOLD}${BLUE}◆ $1${RESET}"; }
ok()    { echo -e "${GREEN}${IC_OK}  $1${RESET}"; }
warn()  { echo -e "${YELLOW}${IC_WARN}  $1${RESET}"; }
err()   { echo -e "${RED}${IC_ERR}  $1${RESET}" >&2; }
info()  { echo -e "${DIM}${IC_INFO}  $1${RESET}"; }
run()   { echo -e "${CYAN}${IC_RUN}  $1${RESET}"; }
arrow() { echo -e "${WHITE}${IC_ARROW}  $1${RESET}"; }

divider() { echo -e "${DIM}  ────────────────────────────────────────────────${RESET}"; }

# ─── Bootstrap ─────────────────────────────────────────────────────────────────
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

# ─── Header ────────────────────────────────────────────────────────────────────
echo ""
echo -e "${BOLD}${WHITE}  ╔══════════════════════════════════════════════╗${RESET}"
echo -e "${BOLD}${WHITE}  ║   EDF Trading Assistant  —  Deploy           ║${RESET}"
echo -e "${BOLD}${WHITE}  ╚══════════════════════════════════════════════╝${RESET}"
echo ""

# ─── Python venv ───────────────────────────────────────────────────────────────
PYTHON="${PYTHON:-$ROOT/.venv/bin/python}"
if [ ! -f "$PYTHON" ]; then
  err "Python venv not found at $PYTHON"
  info "Run: uv sync  (or pip install -e .)"
  exit 1
fi
info "Python  →  $PYTHON"

# ─── Load .env.local ───────────────────────────────────────────────────────────
[ -f "$ROOT/.env.local" ] && set -a && source "$ROOT/.env.local" && set +a

# ─── Auth mode ─────────────────────────────────────────────────────────────────
DBC_PROFILE=""
if [ "${DEPLOY_USE_PAT:-}" = "1" ]; then
  info "Auth    →  PAT  (DEPLOY_USE_PAT=1)"
elif [ -n "${DATABRICKS_CONFIG_PROFILE:-}" ]; then
  unset DATABRICKS_TOKEN
  unset DATABRICKS_HOST
  DBC_PROFILE="${DATABRICKS_CONFIG_PROFILE}"
  info "Auth    →  OAuth profile  ${BOLD}${DBC_PROFILE}${RESET}"
fi

# ─── Config summary ────────────────────────────────────────────────────────────
APP_NAME="${DBX_APP_NAME:-agent-edf-trading-assistant}"
BUNDLE_APP_KEY="${BUNDLE_APP_KEY:-agent_edf_trading_assistant}"
TARGET="${DEPLOY_TARGET:-template}"

echo ""
divider
echo -e "  ${BOLD}App${RESET}     ${CYAN}${APP_NAME}${RESET}"
echo -e "  ${BOLD}Target${RESET}  ${CYAN}${TARGET}${RESET}"
echo -e "  ${BOLD}Key${RESET}     ${DIM}${BUNDLE_APP_KEY}${RESET}"
divider
echo ""

# ─── Step 1: Sync databricks.yml ───────────────────────────────────────────────
step "1 / 7  Sync databricks.yml"
run "sync_databricks_yml_from_env.py"
"$PYTHON" deploy/sync_databricks_yml_from_env.py 2>/dev/null && ok "databricks.yml synced from .env.local" || warn "Sync skipped (non-fatal)"

# ─── Step 2: OpenAI secret ─────────────────────────────────────────────────────
step "2 / 7  OpenAI secret (voice transcription)"
if [ -n "${OPENAI_API_KEY:-}" ]; then
  run "setup_openai_secret.sh"
  ./deploy/setup_openai_secret.sh 2>/dev/null \
    && ok "Secret provisioned" \
    || warn "setup_openai_secret.sh failed — voice transcription may not work"
else
  info "OPENAI_API_KEY not set — skipping"
fi

# ─── Step 3: Bind existing app ─────────────────────────────────────────────────
step "3 / 7  Bind app to bundle"
if databricks ${DBC_PROFILE:+-p "$DBC_PROFILE"} apps get "$APP_NAME" --output json &>/dev/null; then
  run "bundle deployment bind  $BUNDLE_APP_KEY  →  $APP_NAME"
  databricks ${DBC_PROFILE:+-p "$DBC_PROFILE"} bundle deployment bind "$BUNDLE_APP_KEY" "$APP_NAME" \
    -t "$TARGET" --auto-approve 2>/dev/null && ok "Bound" || warn "Bind skipped (may already be bound)"
else
  info "App not found — will be created on deploy"
fi

# ─── Step 4: Validate bundle ───────────────────────────────────────────────────
step "4 / 7  Validate bundle"
run "databricks bundle validate -t $TARGET"
databricks ${DBC_PROFILE:+-p "$DBC_PROFILE"} bundle validate -t "$TARGET"
ok "Bundle valid"

# Optional pre-deploy asset check
if [ "${PRE_DEPLOY_VERIFY:-}" = "1" ]; then
  run "pre_deploy_verify_assets.py"
  "$PYTHON" deploy/pre_deploy_verify_assets.py -t "$TARGET" && ok "Assets verified" || { err "Pre-deploy verification failed"; exit 1; }
fi

# ─── Step 4b: Backend import check ────────────────────────────────────────────
run "Checking backend imports…"
"$PYTHON" -c "from agent_server.start_server import app" \
  && ok "Backend imports OK" \
  || { err "Backend import failed — fix before deploying"; exit 1; }

# ─── Step 5: Deploy bundle ─────────────────────────────────────────────────────
step "5 / 7  Deploy bundle"
run "databricks bundle deploy -t $TARGET"
databricks ${DBC_PROFILE:+-p "$DBC_PROFILE"} bundle deploy -t "$TARGET"
ok "Bundle deployed"

# ─── Step 6: Start app ─────────────────────────────────────────────────────────
step "6 / 7  Start app"
run "databricks bundle run $BUNDLE_APP_KEY -t $TARGET"
databricks ${DBC_PROFILE:+-p "$DBC_PROFILE"} bundle run "$BUNDLE_APP_KEY" -t "$TARGET"
ok "App started"

# ─── Step 7: Grants ────────────────────────────────────────────────────────────
step "7 / 7  Permissions & grants"

SCHEMA="${UNITY_CATALOG_SCHEMA:-edf.template}"

run "UC table access  →  $APP_NAME  (schema: $SCHEMA)"
"$PYTHON" deploy/grant/grant_app_tables.py "$APP_NAME" --schema "$SCHEMA" \
  && ok "UC table access granted" \
  || warn "grant_app_tables.py failed — run manually:\n       $PYTHON deploy/grant/grant_app_tables.py $APP_NAME --schema $SCHEMA"

run "SQL warehouse  →  CAN_USE"
"$PYTHON" deploy/grant/authorize_warehouse_for_app.py "$APP_NAME" \
  && ok "Warehouse access granted" \
  || warn "authorize_warehouse_for_app.py failed — run manually:\n       $PYTHON deploy/grant/authorize_warehouse_for_app.py $APP_NAME"

run "Genie space permissions  →  user + SP"
"$PYTHON" deploy/grant/grant_genie_space_permissions.py --app-name "$APP_NAME" \
  && ok "Genie permissions granted" \
  || warn "grant_genie_space_permissions.py failed — run manually:\n       $PYTHON deploy/grant/grant_genie_space_permissions.py"

# ─── Done ──────────────────────────────────────────────────────────────────────
echo ""
divider
APP_URL=$(databricks ${DBC_PROFILE:+-p "$DBC_PROFILE"} apps get "$APP_NAME" --output json 2>/dev/null | jq -r '.url // empty')
echo -e "\n  ${BOLD}${GREEN}✔  Deploy complete${RESET}\n"
if [ -n "$APP_URL" ]; then
  echo -e "  ${BOLD}${WHITE}App URL${RESET}  ${CYAN}${APP_URL}${RESET}"
fi
divider
echo ""
