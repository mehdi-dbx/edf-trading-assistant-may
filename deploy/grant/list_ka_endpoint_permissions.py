#!/usr/bin/env python3
"""Check and list permissions on each KA serving endpoint from data/ka.list.

Resolves endpoint name to ID (API requires ID), then fetches permissions.

Usage:
  uv run python deploy/grant/list_ka_endpoint_permissions.py [--json]
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
KA_LIST_PATH = ROOT / "data" / "ka.list"

from dotenv import load_dotenv

load_dotenv(ROOT / ".env.local")

from databricks.sdk import WorkspaceClient


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


def _resolve_name_to_id(w: WorkspaceClient, name: str) -> str | None:
    """Resolve endpoint name to ID. Permissions API requires ID."""
    for ep in w.serving_endpoints.list():
        if getattr(ep, "name", None) == name:
            return getattr(ep, "id", None)
    return None


def main() -> int:
    parser = argparse.ArgumentParser(
        description="List permissions on KA endpoints from data/ka.list"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON",
    )
    args = parser.parse_args()

    endpoints = parse_ka_list()
    if not endpoints:
        print(
            f"Warning: No KA endpoints in {KA_LIST_PATH}",
            file=sys.stderr,
        )
        return 0

    w = WorkspaceClient()
    results: list[dict] = []

    for ep_name in sorted(endpoints):
        entry: dict = {
            "endpoint": ep_name,
            "endpoint_id": None,
            "ok": False,
            "permissions": None,
            "error": None,
        }
        try:
            ep_id = _resolve_name_to_id(w, ep_name)
            if not ep_id:
                entry["error"] = "endpoint not found"
                results.append(entry)
                continue
            entry["endpoint_id"] = ep_id

            perm = w.permissions.get(
                request_object_type="serving-endpoints",
                request_object_id=ep_id,
            )
            entry["ok"] = True
            acl = perm.access_control_list if perm else []
            perms: list[dict] = []
            for p in acl:
                principal = (
                    p.service_principal_name or p.user_name or p.group_name or "?"
                )
                level = None
                if getattr(p, "all_permissions", None):
                    levels = [x.permission_level for x in p.all_permissions]
                    level = str(levels[0]).replace("PermissionLevel.", "") if levels else None
                display = getattr(p, "display_name", None) or principal
                perms.append({"principal": principal, "display_name": display, "permission_level": level})
            entry["permissions"] = perms
        except Exception as e:
            entry["error"] = str(e)

        results.append(entry)

    if args.json:
        print(json.dumps(results, indent=2, default=str))
        return 0

    for r in results:
        print(f"\n{r['endpoint']}" + (f" (id={r['endpoint_id']})" if r.get("endpoint_id") else ""))
        if r["error"]:
            print(f"  ERROR: {r['error']}")
        elif r["permissions"]:
            for p in r["permissions"]:
                level = p.get("permission_level") or "?"
                name = p.get("display_name") or p["principal"]
                print(f"  {name}: {level}")
        else:
            print("  (no permissions)")

    print()
    ok = sum(1 for r in results if r["ok"])
    print(f"Checked {len(results)} endpoint(s), {ok} OK")

    return 0


if __name__ == "__main__":
    sys.exit(main())
