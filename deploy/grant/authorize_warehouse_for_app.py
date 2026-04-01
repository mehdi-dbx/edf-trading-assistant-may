#!/usr/bin/env python3
"""Grant CAN_USE on SQL warehouse to the app's service principal.

Usage:
  uv run python deploy/grant/authorize_warehouse_for_app.py [APP_NAME] [--warehouse-id ID]

  APP_NAME: Databricks app name (default: DBX_APP_NAME from .env.local)
  --warehouse-id: Warehouse ID (default: from databricks.yml or DATABRICKS_WAREHOUSE_ID)
"""
import argparse
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

from dotenv import load_dotenv

load_dotenv(ROOT / ".env.local")

from databricks.sdk import WorkspaceClient
from databricks.sdk.service import iam


def get_warehouse_id() -> str | None:
    """Read warehouse ID from databricks.yml or .env.local."""
    yml = ROOT / "databricks.yml"
    if yml.exists():
        content = yml.read_text()
        m = re.search(r"sql_warehouse:\s*\n\s+id:\s*'([^']*)'", content)
        if m:
            return m.group(1)
    return os.environ.get("DATABRICKS_WAREHOUSE_ID", "").strip() or None


def main() -> int:
    default_app = os.environ.get("DBX_APP_NAME", "agent-edf-trading-assistant").strip()
    parser = argparse.ArgumentParser(
        description="Grant CAN_USE on SQL warehouse to app service principal"
    )
    parser.add_argument(
        "app_name",
        nargs="?",
        default=default_app,
        help=f"Databricks app name (default: {default_app!r})",
    )
    parser.add_argument(
        "--warehouse-id",
        default=None,
        help="Warehouse ID (default: from databricks.yml or DATABRICKS_WAREHOUSE_ID)",
    )
    args = parser.parse_args()

    wh_id = args.warehouse_id or get_warehouse_id()
    if not wh_id:
        print(
            "Error: No warehouse ID. Set DATABRICKS_WAREHOUSE_ID or use --warehouse-id",
            file=sys.stderr,
        )
        return 1

    w = WorkspaceClient()
    try:
        app = w.apps.get(name=args.app_name)
    except Exception as e:
        print(f"Error: Could not get app '{args.app_name}': {e}", file=sys.stderr)
        return 1

    sp_id = getattr(app, "service_principal_client_id", None) or getattr(
        app, "oauth2_app_client_id", None
    )
    sp_name = getattr(app, "service_principal_name", None)
    if not sp_id:
        print(
            f"Error: App '{args.app_name}' has no service_principal_client_id",
            file=sys.stderr,
        )
        return 1

    print(f"Granting CAN_USE on warehouse {wh_id} to {sp_name or sp_id}")

    try:
        w.permissions.update(
            request_object_type="warehouses",
            request_object_id=wh_id,
            access_control_list=[
                iam.AccessControlRequest(
                    service_principal_name=sp_id,
                    permission_level=iam.PermissionLevel.CAN_USE,
                )
            ],
        )
        print("Done.")
        return 0
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
