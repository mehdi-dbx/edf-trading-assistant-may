#!/usr/bin/env python3
"""
Fetch Genie room (space) from Databricks workspace and inject into .env.local.

Requires DATABRICKS_HOST and DATABRICKS_TOKEN (or DATABRICKS_CONFIG_PROFILE) in .env.local.
Updates or adds EDF_TRADING_GENIE_ROOM=<space_id>.

Usage:
  uv run python scripts/sync_genie_room_to_env.py
  uv run python scripts/sync_genie_room_to_env.py --name "trading"
  uv run python scripts/sync_genie_room_to_env.py --space-id 01f125ff96d61121a20aab6e7d0b080d
  uv run python scripts/sync_genie_room_to_env.py --dry-run
"""

import argparse
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENV_LOCAL = ROOT / ".env.local"

# Load .env.local before other imports
if ENV_LOCAL.exists():
    from dotenv import load_dotenv
    load_dotenv(ENV_LOCAL, override=True)


def get_workspace_client():
    """Create WorkspaceClient from env."""
    from databricks.sdk import WorkspaceClient
    host = os.environ.get("DATABRICKS_HOST", "").strip()
    token = os.environ.get("DATABRICKS_TOKEN", "").strip()
    profile = os.environ.get("DATABRICKS_CONFIG_PROFILE", "").strip()
    if host and token:
        return WorkspaceClient(host=host, token=token)
    return WorkspaceClient(profile=profile) if profile else WorkspaceClient()


def list_genie_spaces():
    """List Genie spaces from workspace. Returns list of (space_id, title)."""
    w = get_workspace_client()
    response = w.genie.list_spaces()
    spaces = response.spaces if hasattr(response, "spaces") else []
    return [(s.space_id, s.title or "") for s in spaces]


def update_env_file(space_id: str, dry_run: bool = False) -> bool:
    """Set EDF_TRADING_GENIE_ROOM in .env.local. Returns True if file was modified."""
    if not ENV_LOCAL.exists():
        if dry_run:
            print(f"[dry-run] Would create {ENV_LOCAL} with EDF_TRADING_GENIE_ROOM={space_id}", file=sys.stderr)
        else:
            ENV_LOCAL.write_text(f"EDF_TRADING_GENIE_ROOM={space_id}\n")
        return True

    content = ENV_LOCAL.read_text()
    line = f"EDF_TRADING_GENIE_ROOM={space_id}"

    if re.search(r"^\s*EDF_TRADING_GENIE_ROOM\s*=", content, re.MULTILINE):
        new_content = re.sub(
            r"^(\s*EDF_TRADING_GENIE_ROOM\s*=\s*)[^\n]*",
            r"\g<1>" + space_id,
            content,
            count=1,
            flags=re.MULTILINE,
        )
    else:
        new_content = content.rstrip() + f"\n\n# Genie room\n{line}\n"

    if new_content == content:
        return False

    if dry_run:
        print(f"[dry-run] Would set EDF_TRADING_GENIE_ROOM={space_id} in {ENV_LOCAL}", file=sys.stderr)
        return True

    ENV_LOCAL.write_text(new_content)
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Fetch Genie room from workspace and inject into .env.local")
    parser.add_argument("--space-id", help="Use this space ID directly (skip listing)")
    parser.add_argument("--name", help="Filter spaces by title (case-insensitive substring)")
    parser.add_argument("--dry-run", action="store_true", help="Print what would be done, do not write")
    args = parser.parse_args()

    if args.space_id:
        space_id = args.space_id.strip()
        if not space_id:
            print("Error: --space-id cannot be empty", file=sys.stderr)
            return 1
        update_env_file(space_id, dry_run=args.dry_run)
        print(f"EDF_TRADING_GENIE_ROOM={space_id}" + (" (dry-run)" if args.dry_run else ""), file=sys.stderr)
        return 0

    try:
        spaces = list_genie_spaces()
    except Exception as e:
        print(f"Error listing Genie spaces: {e}", file=sys.stderr)
        return 1

    if not spaces:
        print("No Genie spaces found in workspace.", file=sys.stderr)
        return 1

    if args.name:
        name_lower = args.name.lower()
        matches = [(sid, tit) for sid, tit in spaces if name_lower in (tit or "").lower()]
        if not matches:
            print(f"No space matching '{args.name}'. Available:", file=sys.stderr)
            for sid, tit in spaces[:10]:
                print(f"  {sid}  {tit}", file=sys.stderr)
            return 1
        spaces = matches

    # Use first match
    space_id, title = spaces[0]
    if len(spaces) > 1:
        print(f"Multiple matches, using first: {title} ({space_id})", file=sys.stderr)

    updated = update_env_file(space_id, dry_run=args.dry_run)
    print(f"EDF_TRADING_GENIE_ROOM={space_id}  # {title}" + (" (dry-run)" if args.dry_run else ""), file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
