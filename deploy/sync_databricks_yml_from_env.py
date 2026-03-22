#!/usr/bin/env python3
"""Sync databricks.yml and app.yaml from .env.local.

Updates:
  - databricks.yml: sql_warehouse.id, serving_endpoint.name, target app name
  - app.yaml: AGENT_MODEL_ENDPOINT, UNITY_CATALOG_SCHEMA, DATABRICKS_WAREHOUSE_ID

Usage:
  uv run python deploy/sync_databricks_yml_from_env.py [--dry-run]

  --dry-run: Print changes without writing.
"""
import argparse
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env.local")


def get_endpoint_from_app_yaml() -> str:
    app_yml = ROOT / "app.yaml"
    if app_yml.exists():
        lines = app_yml.read_text().splitlines()
        for i, line in enumerate(lines):
            if "AGENT_MODEL_ENDPOINT" in line and "name:" in line:
                for j in range(i + 1, min(i + 3, len(lines))):
                    if "value:" in lines[j]:
                        val = lines[j].split("value:")[-1].strip().strip('"').strip("'")
                        if val and not val.startswith("#"):
                            return val
    return ""


def main() -> int:
    parser = argparse.ArgumentParser(description="Sync databricks.yml from .env.local")
    parser.add_argument("--dry-run", action="store_true", help="Print changes without writing")
    args = parser.parse_args()

    env_path = ROOT / ".env.local"
    yml_path = ROOT / "databricks.yml"

    if not env_path.exists():
        print(f"Error: {env_path} not found", file=sys.stderr)
        return 1
    if not yml_path.exists():
        print(f"Error: {yml_path} not found", file=sys.stderr)
        return 1

    content = yml_path.read_text()
    changes = []

    # sql_warehouse.id <- DATABRICKS_WAREHOUSE_ID
    wh_id = os.environ.get("DATABRICKS_WAREHOUSE_ID", "").strip()
    if wh_id:
        m = re.search(r"sql_warehouse:\s*\n\s+id: '([^']*)'", content)
        if m and m.group(1) != wh_id:
            content = re.sub(r"(sql_warehouse:\s*\n\s+)id: '[^']*'", r"\g<1>id: '" + wh_id + "'", content, count=1)
            changes.append(f"  sql_warehouse.id <- DATABRICKS_WAREHOUSE_ID={wh_id}")

    # serving_endpoint.name <- AGENT_MODEL_ENDPOINT
    endpoint = os.environ.get("AGENT_MODEL_ENDPOINT", "").strip() or get_endpoint_from_app_yaml()
    if endpoint:
        m = re.search(r"serving_endpoint:\s*\n\s+name: '([^']*)'", content)
        if m and m.group(1) != endpoint:
            content = re.sub(
                r"(serving_endpoint:\s*\n\s+)name: '[^']*'",
                r"\g<1>name: '" + endpoint + "'",
                content,
                count=1,
            )
            changes.append(f"  serving_endpoint.name <- AGENT_MODEL_ENDPOINT={endpoint}")

    # targets.template app name <- DBX_APP_NAME
    app_name = os.environ.get("DBX_APP_NAME", "").strip()
    if app_name:
        m = re.search(
            r"template:\s*\n\s+mode: production\s*\n\s+workspace:.*?agent_langgraph:\s*\n\s+name: ([^\n]+)",
            content,
            re.DOTALL,
        )
        current = m.group(1).strip().strip('"').strip("'") if m else ""
        if current != app_name:
            content = re.sub(
                r"(template:\s*\n\s+mode: production\s*\n\s+workspace:.*?agent_langgraph:\s*\n\s+name: )[^\n]+",
                r"\g<1>" + app_name,
                content,
                count=1,
                flags=re.DOTALL,
            )
            changes.append(f"  targets.template app name <- DBX_APP_NAME={app_name}")

    # app.yaml: AGENT_MODEL_ENDPOINT, UNITY_CATALOG_SCHEMA, DATABRICKS_WAREHOUSE_ID
    app_yml = ROOT / "app.yaml"
    if app_yml.exists():
        schema_spec = os.environ.get("UNITY_CATALOG_SCHEMA", "").strip()
        wh_id = os.environ.get("DATABRICKS_WAREHOUSE_ID", "").strip()
        app_content = app_yml.read_text()
        app_changed = False
        if endpoint:
            m = re.search(r"AGENT_MODEL_ENDPOINT\s*\n\s+value:\s*[\"']([^\"']*)[\"']", app_content)
            if m and m.group(1) != endpoint:
                app_content = re.sub(
                    r"(AGENT_MODEL_ENDPOINT\s*\n\s+value:\s*)[\"'][^\"']*[\"']",
                    r'\g<1>"' + endpoint + '"',
                    app_content,
                    count=1,
                )
                app_changed = True
                changes.append(f"  app.yaml AGENT_MODEL_ENDPOINT <- {endpoint}")
        if schema_spec:
            m = re.search(r"UNITY_CATALOG_SCHEMA\s*\n\s+value:\s*[\"']([^\"']*)[\"']", app_content)
            if m and m.group(1) != schema_spec:
                app_content = re.sub(
                    r"(UNITY_CATALOG_SCHEMA\s*\n\s+value:\s*)[\"'][^\"']*[\"']",
                    r'\g<1>"' + schema_spec + '"',
                    app_content,
                    count=1,
                )
                app_changed = True
                changes.append(f"  app.yaml UNITY_CATALOG_SCHEMA <- {schema_spec}")
        if wh_id:
            m = re.search(r"DATABRICKS_WAREHOUSE_ID\s*\n\s+value:\s*[\"']([^\"']*)[\"']", app_content)
            if m and m.group(1) != wh_id:
                app_content = re.sub(
                    r"(DATABRICKS_WAREHOUSE_ID\s*\n\s+value:\s*)[\"'][^\"']*[\"']",
                    r'\g<1>"' + wh_id + '"',
                    app_content,
                    count=1,
                )
                app_changed = True
                changes.append(f"  app.yaml DATABRICKS_WAREHOUSE_ID <- {wh_id}")
        if app_changed:
            app_yml.write_text(app_content)

    if not changes:
        print("databricks.yml already in sync with .env.local")
        return 0

    print("Syncing databricks.yml from .env.local:")
    for c in changes:
        print(c)

    if args.dry_run:
        print("\n[--dry-run] Not writing databricks.yml")
        return 0

    yml_path.write_text(content)
    print(f"\nUpdated {yml_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
