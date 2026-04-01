#!/usr/bin/env bash
# Kill anything listening on 8000 / 3000 / 3001, then start the full dev stack (same as start_local.sh).
set -e
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=local-stack-ports.sh
source "$ROOT/scripts/local-stack-ports.sh"
kill_local_stack_ports
sleep 2
exec "$ROOT/scripts/start_local.sh"
