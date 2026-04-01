#!/usr/bin/env python3
"""Sync KA endpoints from data/ka.list into databricks.yml.

Reads data/ka.list, parses endpoint names, and adds/updates serving_endpoint
resources under apps.agent_edf_trading_assistant.resources so the app can query KA endpoints.

Usage:
  uv run python deploy/sync_ka_endpoints_to_yml.py [--dry-run]

  --dry-run: Print changes without writing.
"""
import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
KA_LIST_PATH = ROOT / "data" / "ka.list"
DATABRICKS_YML = ROOT / "databricks.yml"

KA_SECTION_START = "        # --- KA endpoints (from data/ka.list) ---"
KA_SECTION_END = "        # --- end KA endpoints ---"


def parse_ka_list() -> list[str]:
    """Return list of endpoint names from ka.list."""
    endpoints = []
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


def resource_name_for_endpoint(endpoint: str) -> str:
    """Generate unique resource name for databricks.yml (e.g. ka_69061eaf)."""
    # ka-69061eaf-endpoint -> 69061eaf
    stem = endpoint.replace("ka-", "").replace("-endpoint", "")
    return stem


def build_ka_section(endpoints: list[str]) -> str:
    """Build YAML block for KA serving_endpoint resources."""
    if not endpoints:
        return ""
    lines = [KA_SECTION_START]
    for ep in sorted(endpoints):
        rid = resource_name_for_endpoint(ep)
        lines.append(f"        - name: 'ka_{rid}'")
        lines.append("          serving_endpoint:")
        lines.append(f"            name: '{ep}'")
        lines.append("            permission: 'CAN_QUERY'")
    lines.append(KA_SECTION_END)
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Sync KA endpoints from ka.list to databricks.yml")
    parser.add_argument("--dry-run", action="store_true", help="Print changes without writing")
    args = parser.parse_args()

    if not DATABRICKS_YML.exists():
        print(f"Error: {DATABRICKS_YML} not found", file=sys.stderr)
        return 1

    endpoints = parse_ka_list()
    if not endpoints:
        print(f"No KA endpoints in {KA_LIST_PATH}. Run scripts/list_ka_endpoints.py first.", file=sys.stderr)
        return 0

    content = DATABRICKS_YML.read_text()
    new_section = build_ka_section(endpoints)

    # Replace or insert KA section
    if KA_SECTION_START in content and KA_SECTION_END in content:
        content = re.sub(
            re.escape(KA_SECTION_START) + r".*?" + re.escape(KA_SECTION_END) + r"\n?",
            new_section.rstrip() + "\n",
            content,
            flags=re.DOTALL,
        )
        action = "Updated"
    else:
        # Insert before targets (after openai_api_key block)
        insert_pattern = r"(\s+permission: 'READ'\n)(\n)(targets:)"
        if re.search(insert_pattern, content):
            content = re.sub(
                insert_pattern,
                r"\1\n" + new_section + r"\n\3",
                content,
                count=1,
            )
            action = "Added"
        else:
            print("Error: Could not find insertion point in databricks.yml", file=sys.stderr)
            return 1

    if args.dry_run:
        print("Would update databricks.yml:")
        print(f"  {action} {len(endpoints)} KA endpoint(s)")
        for ep in sorted(endpoints):
            print(f"    - {ep}")
        return 0

    DATABRICKS_YML.write_text(content)
    print(f"{action} {len(endpoints)} KA endpoint(s) in databricks.yml", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
