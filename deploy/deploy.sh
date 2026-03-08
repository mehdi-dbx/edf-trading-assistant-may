#!/usr/bin/env bash
# Deploy trial app to Databricks Apps.
# Run from the trial directory: ./scripts/deploy.sh
# Usage: ./scripts/deploy.sh [app-name]
#   app-name defaults to agent-airops-hello
set -e

APP_NAME="${1:-agent-airops-hello}"
DATABRICKS_USERNAME=$(databricks current-user me | jq -r .userName)
REMOTE_PATH="/Users/$DATABRICKS_USERNAME/agent-langgraph"

echo "Removing remote .venv (if present)..."
databricks workspace delete "$REMOTE_PATH/.venv" --recursive 2>/dev/null || true

echo "Syncing to workspace (excluding .venv, node_modules via .gitignore)..."
databricks sync . "$REMOTE_PATH" --exclude-from .gitignore

echo "Deploying app $APP_NAME..."
databricks apps deploy "$APP_NAME" --source-code-path "/Workspace$REMOTE_PATH"

echo "Done."
