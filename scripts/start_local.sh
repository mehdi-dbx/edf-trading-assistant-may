#!/usr/bin/env bash
# Run full stack locally: backend (8000) + Node API (3001) + Vite frontend (3000).
# Kills any process on 8000, 3000, 3001 at start. Env from .env and .env.local.
set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ ! -d e2e-chatbot-app-next ]]; then
  echo "Frontend not found. Run 'uv run start-app' once to clone it, then run this script again."
  exit 1
fi

# Free ports 8000, 3000, 3001 if in use (e.g. previous run)
for port in 8000 3000 3001; do
  pid=$(lsof -ti :$port 2>/dev/null) || true
  [[ -n "$pid" ]] && kill $pid 2>/dev/null || true
done
sleep 1

# --- BEGIN: TEMPORARY LOCAL TESTING ONLY (not used on Databricks) ---
# macOS: WeasyPrint (PDF report tool) needs Homebrew Pango/Cairo
[[ "$(uname -s)" = Darwin && -d /opt/homebrew/lib ]] && export DYLD_LIBRARY_PATH="/opt/homebrew/lib${DYLD_LIBRARY_PATH:+:$DYLD_LIBRARY_PATH}"
# --- END: TEMPORARY LOCAL TESTING ONLY ---

# Load .env then .env.local so DATABRICKS_* and API_PROXY are set for all children
set -a
[[ -f .env       ]] && source .env
[[ -f .env.local ]] && source .env.local
set +a
export API_PROXY="${API_PROXY:-http://localhost:8000/invocations}"

BACKEND_PID=""
NODE_PID=""
FRONTEND_PID=""
cleanup() {
  [[ -n $BACKEND_PID  ]] && kill $BACKEND_PID  2>/dev/null || true
  [[ -n $NODE_PID     ]] && kill $NODE_PID     2>/dev/null || true
  [[ -n $FRONTEND_PID ]] && kill $FRONTEND_PID 2>/dev/null || true
  exit 0
}
trap cleanup SIGINT SIGTERM

echo "Starting backend (8000), Node API (3001), and frontend (3000)..."
echo "Backend:  http://localhost:8000"
echo "Node API: http://localhost:3001  (/api/session)"
echo "Frontend: http://localhost:3000"
echo "Stop with Ctrl+C"
echo ""

# Build Node server if needed (avoids tsx IPC in restricted environments)
if [[ ! -f e2e-chatbot-app-next/server/dist/index.mjs ]]; then
  (cd e2e-chatbot-app-next && npm run build:server) || true
fi

# Start each process in a subshell and capture real PID (so monitor loop has correct PIDs)
(uv run start-server --reload >> "$ROOT/backend.log" 2>&1 & echo $! > "$ROOT/.backend.pid"; wait) &
sleep 5
BACKEND_PID=$(cat "$ROOT/.backend.pid" 2>/dev/null)
(env CHAT_APP_PORT=3001 PORT=3001 bash -c 'cd e2e-chatbot-app-next && npm run dev:built --workspace=@databricks/chatbot-server' >> "$ROOT/node.log" 2>&1 & echo $! > "$ROOT/.node.pid"; wait) &
sleep 4
NODE_PID=$(cat "$ROOT/.node.pid" 2>/dev/null)
(bash -c 'cd e2e-chatbot-app-next && npm run dev:client' >> "$ROOT/frontend.log" 2>&1 & echo $! > "$ROOT/.frontend.pid"; wait) &
sleep 6
FRONTEND_PID=$(cat "$ROOT/.frontend.pid" 2>/dev/null)

while true; do
  for pid in $BACKEND_PID $NODE_PID $FRONTEND_PID; do
    if ! kill -0 "$pid" 2>/dev/null; then
      kill $BACKEND_PID $NODE_PID $FRONTEND_PID 2>/dev/null || true
      exit 1
    fi
  done
  sleep 1
done
