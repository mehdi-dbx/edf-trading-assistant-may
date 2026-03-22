#!/usr/bin/env python3
"""Retrieve app service principal info (name + application ID) from Databricks.

Usage:
  uv run python deploy/grant/retrieve_app_sp.py [APP_NAME]

  APP_NAME: Databricks app name (default: DBX_APP_NAME from .env.local)
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

from dotenv import load_dotenv

load_dotenv(ROOT / ".env.local")
import os

from databricks.sdk import WorkspaceClient


def main() -> int:
    default_app = os.environ.get("DBX_APP_NAME", "agent-langgraph").strip()
    parser = argparse.ArgumentParser(description="Retrieve app service principal info")
    parser.add_argument(
        "app_name",
        nargs="?",
        default=default_app,
        help=f"Databricks app name (default: {default_app!r} from DBX_APP_NAME)",
    )
    args = parser.parse_args()

    w = WorkspaceClient()
    try:
        app = w.apps.get(name=args.app_name)
    except Exception as e:
        print(f"Error: Could not get app '{args.app_name}': {e}", file=sys.stderr)
        return 1

    # Service principal display name (e.g. "app-iqj9it agent-airops-checkin")
    sp_name = getattr(app, "service_principal_name", None)
    # Application ID / client ID - use for Unity Catalog GRANT (UUID)
    sp_id = getattr(app, "service_principal_client_id", None) or getattr(
        app, "oauth2_app_client_id", None
    )

    out = {
        "service_principal_name": sp_name,
        "service_principal_client_id": sp_id,
        "app_name": app.name,
    }
    print(json.dumps(out, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
