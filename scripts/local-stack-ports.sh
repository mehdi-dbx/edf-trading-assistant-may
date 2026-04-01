# shellcheck shell=bash
# Shared by start_local.sh and restart_local.sh — kill LISTENers only (not browser clients).
kill_local_stack_ports() {
  for port in 8000 3000 3001; do
    # Multiple PIDs can share a port (e.g. parent + worker); kill each.
    for pid in $(lsof -ti :"$port" -sTCP:LISTEN 2>/dev/null); do
      kill "$pid" 2>/dev/null || true
    done
  done
}
