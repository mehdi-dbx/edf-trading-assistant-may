#!/usr/bin/env bash
# Create Databricks secret scope and store OPENAI_API_KEY for voice transcription.
# Run from project root: ./deploy/setup_openai_secret.sh
#
# Reads OPENAI_API_KEY from .env.local. Skips if secret already exists.
set -e

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

SCOPE="template"
KEY="openai-api-key"

# Check if secret already exists (scope may not exist yet)
if databricks secrets list-secrets "$SCOPE" 2>/dev/null | grep -qw "$KEY"; then
  echo "Secret $SCOPE/$KEY already exists. Skipping."
  exit 0
fi

# Load .env.local
if [ ! -f "$ROOT/.env.local" ]; then
  echo "Error: .env.local not found"
  exit 1
fi
set -a
source "$ROOT/.env.local"
set +a

if [ -z "${OPENAI_API_KEY:-}" ]; then
  echo "Error: OPENAI_API_KEY not set in .env.local"
  exit 1
fi

echo "Creating secret scope $SCOPE (if not exists)..."
databricks secrets create-scope "$SCOPE" 2>/dev/null || true

echo "Storing OPENAI_API_KEY in $SCOPE/$KEY..."
databricks secrets put-secret "$SCOPE" "$KEY" --string-value "$OPENAI_API_KEY"

echo "Done. Secret $SCOPE/$KEY is ready for deploy."
