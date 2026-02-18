#!/usr/bin/env bash
# Single-command dev: backend with --reload + frontend with HMR.
# Frontend changes reflect automatically. Stop with Ctrl+C; both processes exit.
set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ ! -d e2e-chatbot-app-next ]]; then
  echo "Frontend not found. Run 'uv run start-app' once to clone it, then run this script again."
  exit 1
fi

# Load .env so API_PROXY and others are set for frontend
if [[ -f .env ]]; then
  set -a
  source .env
  set +a
fi
export API_PROXY="${API_PROXY:-http://localhost:8000/invocations}"

BACKEND_PID=""
FRONTEND_PID=""
cleanup() {
  [[ -n $BACKEND_PID  ]] && kill "$BACKEND_PID"  2>/dev/null || true
  [[ -n $FRONTEND_PID ]] && kill "$FRONTEND_PID" 2>/dev/null || true
  exit 0
}
trap cleanup SIGINT SIGTERM

echo "Starting backend (reload) and frontend (HMR)..."
echo "Backend:  http://localhost:8000"
echo "Frontend: http://localhost:3000  (Vite dev server)"
echo "Stop with Ctrl+C"
echo ""

uv run start-server --reload & BACKEND_PID=$!
(cd e2e-chatbot-app-next && npm run dev:client) & FRONTEND_PID=$!

# When either exits, kill both
wait -n
EXIT_CODE=$?
kill $BACKEND_PID $FRONTEND_PID 2>/dev/null || true
exit $EXIT_CODE
