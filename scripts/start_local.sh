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

# Port cleanup: SIGTERM first, wait, then SIGKILL if still hanging
PORTS=(8000 3000 3001)
for port in "${PORTS[@]}"; do
  pids=$(lsof -ti :$port 2>/dev/null) || true
  if [[ -n "$pids" ]]; then
    echo "Port $port in use, sending SIGTERM to: $pids"
    echo "$pids" | xargs kill 2>/dev/null || true
  fi
done
for port in "${PORTS[@]}"; do
  n=0
  while lsof -ti :$port >/dev/null 2>&1 && [[ $n -lt 5 ]]; do
    sleep 1; n=$((n + 1))
  done
  pids=$(lsof -ti :$port 2>/dev/null) || true
  if [[ -n "$pids" ]]; then
    echo "Port $port still in use, sending SIGKILL to: $pids"
    echo "$pids" | xargs kill -9 2>/dev/null || true
  fi
done

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
  for pid in $BACKEND_PID $NODE_PID $FRONTEND_PID; do
    [[ -z "$pid" ]] && continue
    pgid=$(ps -o pgid= -p "$pid" 2>/dev/null | tr -d ' ')
    [[ -n "$pgid" ]] && kill -- -"$pgid" 2>/dev/null || true
  done
  rm -f "$ROOT"/.{backend,node,frontend}.pid
  exit 0
}
trap cleanup SIGINT SIGTERM

echo "Starting backend (8000), Node API (3001), and frontend (3000)..."
echo "Backend:  http://localhost:8000"
echo "Node API: http://localhost:3001  (/api/session)"
echo "Frontend: http://localhost:3000"
echo "Stop with Ctrl+C"
echo ""

# Wait for a URL to return 200 (max 60s)
wait_for() {
  local url="$1" name="$2" n=0 max=60
  until curl -s -o /dev/null -w "%{http_code}" "$url" 2>/dev/null | grep -q 200; do
    n=$((n + 1)); [[ $n -ge $max ]] && { echo "Timeout waiting for $name"; return 1; }
    sleep 1
  done
  echo "$name ready"
}

# Build Node server (ensures latest routes, e.g. /api/tables)
(cd e2e-chatbot-app-next && npm run build:server) || true

# Start each process with setsid so kill -- -$PGID only hits the child tree,
# not your terminal or other apps (e.g. Firefox)
(setsid uv run start-server --reload >> "$ROOT/backend.log" 2>&1 & echo $! > "$ROOT/.backend.pid"; wait) &
wait_for "http://127.0.0.1:8000/health" "Backend" || true
BACKEND_PID=$(cat "$ROOT/.backend.pid" 2>/dev/null)

(setsid env CHAT_APP_PORT=3001 PORT=3001 API_PROXY="$API_PROXY" \
  bash -c 'cd e2e-chatbot-app-next && npm run dev:built --workspace=@databricks/chatbot-server' \
  >> "$ROOT/node.log" 2>&1 & echo $! > "$ROOT/.node.pid"; wait) &
wait_for "http://127.0.0.1:3001/ping" "Node API" || true
NODE_PID=$(cat "$ROOT/.node.pid" 2>/dev/null)

(setsid bash -c 'cd e2e-chatbot-app-next && npm run dev:client' >> "$ROOT/frontend.log" 2>&1 & echo $! > "$ROOT/.frontend.pid"; wait) &
sleep 5
FRONTEND_PID=$(cat "$ROOT/.frontend.pid" 2>/dev/null)

# Monitor: call cleanup on unexpected exit so nothing is orphaned
while true; do
  for pid in $BACKEND_PID $NODE_PID $FRONTEND_PID; do
    if ! kill -0 "$pid" 2>/dev/null; then
      echo "Process $pid exited unexpectedly. Shutting down."
      cleanup
    fi
  done
  sleep 1
done