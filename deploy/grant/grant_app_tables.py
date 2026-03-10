#!/usr/bin/env python3
"""Grant SELECT on all UC tables in schema to the app's service principal.

Usage:
  uv run python deploy/grant/grant_app_tables.py [APP_NAME] [--schema SCHEMA]

  APP_NAME: Databricks app name (default: agent-airops-checkin)
  --schema: Catalog.schema (default: from AMADEUS_UNITY_CATALOG_SCHEMA or mc.amadeus-checkin)
"""
import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv
load_dotenv(ROOT / ".env.local")

from databricks.sdk import WorkspaceClient
from tools.sql_executor import execute_statement, get_warehouse

DEFAULT_SCHEMA = os.environ.get("AMADEUS_UNITY_CATALOG_SCHEMA", "mc.amadeus-checkin")


def main() -> int:
    parser = argparse.ArgumentParser(description="Grant SELECT on UC tables to app service principal")
    parser.add_argument("app_name", nargs="?", default="agent-airops-checkin", help="Databricks app name")
    parser.add_argument(
        "--schema",
        default=DEFAULT_SCHEMA,
        help=f"Catalog.schema (default: {DEFAULT_SCHEMA} or AMADEUS_UNITY_CATALOG_SCHEMA)",
    )
    args = parser.parse_args()

    w = WorkspaceClient()
    try:
        app = w.apps.get(name=args.app_name)
    except Exception as e:
        print(f"Error: Could not get app '{args.app_name}': {e}", file=sys.stderr)
        return 1

    # Unity Catalog uses the service principal's application ID (UUID), not the display name
    sp_id = getattr(app, "service_principal_client_id", None) or getattr(
        app, "oauth2_app_client_id", None
    )
    if not sp_id:
        print(f"Error: App '{args.app_name}' has no service_principal_client_id", file=sys.stderr)
        return 1

    print(f"Granting SELECT to app service principal: {app.service_principal_name} ({sp_id})")

    w_client, wh_id = get_warehouse()
    catalog, schema = args.schema.split(".", 1) if "." in args.schema else (args.schema, "amadeus-checkin")

    tables = list(w.tables.list(catalog_name=catalog, schema_name=schema))
    if not tables:
        print(f"No tables in {catalog}.{schema}", file=sys.stderr)
        return 1

    for stmt in [
        f"GRANT USE CATALOG ON CATALOG `{catalog}` TO `{sp_id}`",
        f"GRANT USE SCHEMA ON SCHEMA `{catalog}`.`{schema}` TO `{sp_id}`",
    ]:
        try:
            execute_statement(w_client, wh_id, stmt)
            print(f"  OK: {stmt}")
        except Exception as e:
            print(f"  FAIL: {stmt} - {e}", file=sys.stderr)
            return 1

    for t in tables:
        table = t.name
        full_name = f"`{catalog}`.`{schema}`.`{table}`"
        stmt = f"GRANT ALL PRIVILEGES ON TABLE {full_name} TO `{sp_id}`"
        try:
            execute_statement(w_client, wh_id, stmt)
            print(f"  OK: {stmt}")
        except Exception as e:
            print(f"  FAIL: {stmt} - {e}", file=sys.stderr)
            return 1

    print("Done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
