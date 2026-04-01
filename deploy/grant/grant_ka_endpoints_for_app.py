#!/usr/bin/env python3
"""Grant CAN_QUERY on KA serving endpoints to the app's service principal.

Uses retrieve_app_sp logic to get the app SP, reads endpoint names from data/ka.list,
and grants CAN_QUERY via the Permissions API.

Usage:
  uv run python deploy/grant/grant_ka_endpoints_for_app.py [APP_NAME]

  APP_NAME: Databricks app name (default: DBX_APP_NAME from .env.local)
"""
import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
KA_LIST_PATH = ROOT / "data" / "ka.list"

from dotenv import load_dotenv

load_dotenv(ROOT / ".env.local")

from databricks.sdk import WorkspaceClient
from databricks.sdk.service import iam


def parse_ka_list() -> list[str]:
    """Return list of endpoint names from data/ka.list."""
    endpoints: list[str] = []
    if not KA_LIST_PATH.exists():
        return endpoints
    for line in KA_LIST_PATH.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split("\t", 1)
        if parts:
            ep = parts[0].strip()
            if ep and ep.startswith("ka-"):
                endpoints.append(ep)
    return endpoints


def get_app_sp_info(app_name: str) -> dict | None:
    """Get app service principal info via retrieve_app_sp.py."""
    result = subprocess.run(
        [sys.executable, str(ROOT / "deploy" / "grant" / "retrieve_app_sp.py"), app_name],
        capture_output=True,
        text=True,
        cwd=ROOT,
    )
    if result.returncode != 0:
        return None
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return None


def main() -> int:
    default_app = os.environ.get("DBX_APP_NAME", "agent-edf-trading-assistant").strip()
    parser = argparse.ArgumentParser(
        description="Grant CAN_QUERY on KA endpoints to app service principal"
    )
    parser.add_argument(
        "app_name",
        nargs="?",
        default=default_app,
        help=f"Databricks app name (default: {default_app!r})",
    )
    args = parser.parse_args()

    sp_info = get_app_sp_info(args.app_name)
    if not sp_info:
        print(
            f"Error: Could not get app SP for '{args.app_name}'. Is the app deployed?",
            file=sys.stderr,
        )
        return 1

    sp_id = sp_info.get("service_principal_client_id")
    sp_name = sp_info.get("service_principal_name", sp_id)
    if not sp_id:
        print(
            f"Error: App '{args.app_name}' has no service_principal_client_id",
            file=sys.stderr,
        )
        return 1

    endpoints = parse_ka_list()
    if not endpoints:
        print(
            f"Warning: No KA endpoints in {KA_LIST_PATH}. Run scripts/list_ka_endpoints.py first.",
            file=sys.stderr,
        )
        return 0

    print(f"Granting CAN_QUERY on {len(endpoints)} KA endpoint(s) to {sp_name or sp_id}")
    w = WorkspaceClient()

    ok = 0
    for ep in sorted(endpoints):
        try:
            w.permissions.update(
                request_object_type="serving-endpoints",
                request_object_id=ep,
                access_control_list=[
                    iam.AccessControlRequest(
                        service_principal_name=sp_id,
                        permission_level=iam.PermissionLevel.CAN_QUERY,
                    )
                ],
            )
            print(f"  OK: {ep}")
            ok += 1
        except Exception as e:
            print(f"  FAIL: {ep} - {e}", file=sys.stderr)

    print(f"Done. {ok}/{len(endpoints)} endpoint(s) granted.")
    return 0 if ok == len(endpoints) else 1


if __name__ == "__main__":
    sys.exit(main())
