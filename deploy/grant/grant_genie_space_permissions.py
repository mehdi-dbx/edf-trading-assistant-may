#!/usr/bin/env python3
"""Grant Genie space permissions via the workspace Permissions API.

Use this when pre-deploy verify or Genie APIs fail with:
  ``You need "Can View" permission to perform this action``

**Default behaviour:** grant **only the current interactive user** (the identity in
`databricks auth` / `.env.local`). No Databricks App is involved.

Optional: pass ``--app-name`` to also grant the **app’s service principal** once that
app exists (deployed). Do **not** pass an app name if you only need your own user fixed.

`authorize_genie_for_app.py` only adds `genie_space` to `databricks.yml` (bundle). This
script applies workspace object ACLs.

Usage (from repo root):
  .venv/bin/python deploy/grant/grant_genie_space_permissions.py
  .venv/bin/python deploy/grant/grant_genie_space_permissions.py --space-id <id>
  .venv/bin/python deploy/grant/grant_genie_space_permissions.py --app-name <deployed-app-name>

  --space-id ID       Genie space id (default: databricks.yml or EDF_TRADING_GENIE_ROOM)
  --app-name NAME     If set, also grant this app’s service principal (app must exist)
  --skip-user         Do not grant the current user (only use with --app-name)
  --permission LEVEL  CAN_VIEW | CAN_EDIT | CAN_RUN | CAN_MANAGE (default: CAN_RUN)

Loads `.env.local` like other deploy scripts.
"""
from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

from dotenv import load_dotenv

load_dotenv(ROOT / ".env.local")

from databricks.sdk import WorkspaceClient
from databricks.sdk.core import DatabricksError
from databricks.sdk.service import iam


def _request_key(r: iam.AccessControlRequest) -> str | None:
    if r.user_name:
        return f"u:{r.user_name}"
    if r.group_name:
        return f"g:{r.group_name}"
    if r.service_principal_name:
        return f"sp:{r.service_principal_name}"
    return None


def _response_key(ac: iam.AccessControlResponse) -> str | None:
    if ac.user_name:
        return f"u:{ac.user_name}"
    if ac.group_name:
        return f"g:{ac.group_name}"
    if ac.service_principal_name:
        return f"sp:{ac.service_principal_name}"
    return None


def _response_to_request(ac: iam.AccessControlResponse) -> iam.AccessControlRequest | None:
    """Turn a GET ACL row into a PUT/PATCH request row (single permission level)."""
    if not ac.all_permissions:
        return None
    level = None
    for p in ac.all_permissions:
        if getattr(p, "inherited", None):
            continue
        level = p.permission_level
        if level is not None:
            break
    if level is None:
        level = ac.all_permissions[0].permission_level
    if level is None:
        return None
    return iam.AccessControlRequest(
        user_name=ac.user_name,
        group_name=ac.group_name,
        service_principal_name=ac.service_principal_name,
        permission_level=level,
    )


def _fallback_levels(primary: iam.PermissionLevel) -> list[iam.PermissionLevel]:
    """Try primary first, then common Genie levels (PATCH sometimes fails with InternalError)."""
    order = [
        primary,
        iam.PermissionLevel.CAN_VIEW,
        iam.PermissionLevel.CAN_EDIT,
        iam.PermissionLevel.CAN_RUN,
        iam.PermissionLevel.CAN_MANAGE,
    ]
    seen: set[iam.PermissionLevel] = set()
    out: list[iam.PermissionLevel] = []
    for p in order:
        if p not in seen:
            seen.add(p)
            out.append(p)
    return out


def _grant_via_merge_set(
    w: WorkspaceClient,
    space_id: str,
    entry: iam.AccessControlRequest,
) -> None:
    """GET existing ACL, replace/add one principal, PUT full list (works when PATCH misbehaves)."""
    cur = w.permissions.get(request_object_type="genie", request_object_id=space_id)
    merged: list[iam.AccessControlRequest] = []
    nk = _request_key(entry)
    for ac in cur.access_control_list or []:
        req = _response_to_request(ac)
        if not req:
            continue
        if nk and _request_key(req) == nk:
            continue
        merged.append(req)
    merged.append(entry)
    w.permissions.set(
        request_object_type="genie",
        request_object_id=space_id,
        access_control_list=merged,
    )


def _grant_one_principal(
    w: WorkspaceClient,
    space_id: str,
    base: iam.AccessControlRequest,
    label: str,
) -> None:
    last_patch_err: Exception | None = None
    primary = base.permission_level or iam.PermissionLevel.CAN_VIEW
    for lvl in _fallback_levels(primary):
        entry = iam.AccessControlRequest(
            user_name=base.user_name,
            group_name=base.group_name,
            service_principal_name=base.service_principal_name,
            permission_level=lvl,
        )
        try:
            w.permissions.update(
                request_object_type="genie",
                request_object_id=space_id,
                access_control_list=[entry],
            )
            if lvl != primary:
                print(f"  (used {lvl.value} — PATCH ok)")
            return
        except Exception as e:
            last_patch_err = e
            continue
    # PATCH often returns InternalError on some workspaces; try GET + PUT with merged ACL.
    last_merge_err: Exception | None = None
    for lvl in _fallback_levels(primary):
        entry = iam.AccessControlRequest(
            user_name=base.user_name,
            group_name=base.group_name,
            service_principal_name=base.service_principal_name,
            permission_level=lvl,
        )
        try:
            _grant_via_merge_set(w, space_id, entry)
            if lvl != primary:
                print(f"  (used {lvl.value} via permissions.set)")
            else:
                print(
                    f"  (permissions.set after PATCH failed: {last_patch_err!r})"
                )
            return
        except Exception as e2:
            last_merge_err = e2
            continue
    print(
        f"Error: could not grant {label}. PATCH: {last_patch_err!r}; SET: {last_merge_err!r}",
        file=sys.stderr,
    )
    raise last_merge_err or RuntimeError("grant failed")


def get_space_id_from_yml() -> str | None:
    yml = ROOT / "databricks.yml"
    if not yml.exists():
        return None
    content = yml.read_text()
    m = re.search(r"genie_space:.*?space_id: '([^']*)'", content, re.DOTALL)
    return m.group(1).strip() if m else None


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Grant Genie space permissions to the current user (default) and optionally an app SP"
    )
    parser.add_argument(
        "--space-id",
        default=None,
        help="Genie space id (default: databricks.yml or EDF_TRADING_GENIE_ROOM)",
    )
    parser.add_argument(
        "--app-name",
        default=None,
        metavar="NAME",
        help="If set, also grant this Databricks App's service principal (app must exist)",
    )
    parser.add_argument(
        "--skip-user",
        action="store_true",
        help="Do not grant the current user (only meaningful with --app-name)",
    )
    parser.add_argument(
        "--permission",
        choices=["CAN_VIEW", "CAN_EDIT", "CAN_RUN", "CAN_MANAGE"],
        default="CAN_RUN",
        help="Desired level; script may fall back (e.g. if PATCH returns InternalError)",
    )
    args = parser.parse_args()

    space_id = (args.space_id or "").strip() or get_space_id_from_yml()
    if not space_id:
        space_id = os.environ.get("EDF_TRADING_GENIE_ROOM", "").strip()
    if not space_id:
        print(
            "Error: No Genie space id. Set --space-id, or EDF_TRADING_GENIE_ROOM, "
            "or add genie_space.space_id in databricks.yml",
            file=sys.stderr,
        )
        return 1

    grant_user = not args.skip_user
    grant_app = bool(args.app_name and args.app_name.strip())
    if not grant_user and not grant_app:
        print(
            "Error: nothing to grant. Omit --skip-user, or pass --app-name for app SP.",
            file=sys.stderr,
        )
        return 1

    level = getattr(iam.PermissionLevel, args.permission)

    w = WorkspaceClient()

    if grant_user:
        try:
            me = w.current_user.me()
        except DatabricksError as e:
            print(f"Error: current user: {e}", file=sys.stderr)
            return 1
        un = me.user_name
        if not un:
            print("Error: could not resolve current user user_name", file=sys.stderr)
            return 1
        print(f"Grant {args.permission} on genie space {space_id} → user {un}")
        try:
            _grant_one_principal(
                w,
                space_id,
                iam.AccessControlRequest(user_name=un, permission_level=level),
                label=f"user {un}",
            )
        except Exception:
            return 1

    if grant_app:
        app_name = args.app_name.strip()
        try:
            app = w.apps.get(name=app_name)
        except Exception as e:
            print(
                f"Error: could not load app {app_name!r}: {e}",
                file=sys.stderr,
            )
            return 1
        sp_id = getattr(app, "service_principal_client_id", None) or getattr(
            app, "oauth2_app_client_id", None
        )
        sp_label = getattr(app, "service_principal_name", None) or sp_id
        if not sp_id:
            print(
                f"Error: app {app_name!r} has no service_principal_client_id",
                file=sys.stderr,
            )
            return 1
        print(f"Grant {args.permission} on genie space {space_id} → app SP {sp_label}")
        try:
            _grant_one_principal(
                w,
                space_id,
                iam.AccessControlRequest(
                    service_principal_name=sp_id,
                    permission_level=level,
                ),
                label=f"app SP {sp_label}",
            )
        except Exception:
            return 1

    print("Done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
