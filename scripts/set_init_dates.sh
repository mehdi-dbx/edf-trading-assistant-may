#!/usr/bin/env bash
# Set all dates in data/init to the given date.
# Usage:
#   ./scripts/set_init_dates.sh 2026-03-01
#   ./scripts/set_init_dates.sh 2026-03-01 10:00:00
set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
uv run python scripts/set_init_dates.py "$@"
