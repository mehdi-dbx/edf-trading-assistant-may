#!/usr/bin/env python3
"""
Create a Genie space named "AMADEUS CHECKIN" with all tables from AMADEUS_UNITY_CATALOG_SCHEMA.

Prints space_id to stdout. Updates .env.local with AMADEUS_GENIE_CHECKIN.

Requires: AMADEUS_UNITY_CATALOG_SCHEMA, DATABRICKS_WAREHOUSE_ID (or a warehouse in the workspace).
"""
import json
import os
import sys
import uuid
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)
load_dotenv(ROOT / ".env", override=True)
load_dotenv(ROOT / ".env.local", override=True)


def main():
    spec = os.environ.get("AMADEUS_UNITY_CATALOG_SCHEMA") or ""
    if "." not in spec:
        print("Set AMADEUS_UNITY_CATALOG_SCHEMA to catalog.schema in .env.local", file=sys.stderr)
        sys.exit(1)
    catalog, schema = spec.strip().split(".", 1)

    from databricks.sdk import WorkspaceClient
    token = os.environ.get("DATABRICKS_TOKEN")
    # Prefer token over profile to avoid databricks-cli auth when token is set
    if token:
        _profile = os.environ.pop("DATABRICKS_CONFIG_PROFILE", None)
        try:
            w = WorkspaceClient(host=os.environ.get("DATABRICKS_HOST"), token=token)
        finally:
            if _profile is not None:
                os.environ["DATABRICKS_CONFIG_PROFILE"] = _profile
    else:
        w = WorkspaceClient()

    wh_id = os.environ.get("DATABRICKS_WAREHOUSE_ID") or next(iter(w.warehouses.list()), None)
    if not wh_id:
        print("No warehouse. Set DATABRICKS_WAREHOUSE_ID or create one.", file=sys.stderr)
        sys.exit(1)
    wh_id = getattr(wh_id, "id", wh_id)

    tables = list(w.tables.list(catalog_name=catalog, schema_name=schema))
    if not tables:
        print(f"No tables in {catalog}.{schema}. Run csv_to_delta.py first.", file=sys.stderr)
        sys.exit(1)

    table_identifiers = []
    for t in tables:
        full = getattr(t, "full_name", None) or f"{catalog}.{schema}.{t.name}"
        table_identifiers.append(full)

    def gen_id():
        return uuid.uuid4().hex[:24] + "0" * 8

    title = "AMADEUS CHECKIN"
    description = "Natural language exploration of check-in and flight performance data in Unity Catalog."
    sample_questions = [
        {"id": gen_id(), "question": ["What are total check-ins by airline?"]},
        {"id": gen_id(), "question": ["Show load factor and SLA by airline"]},
    ]
    env_var = "AMADEUS_GENIE_CHECKIN"

    serialized = {
        "version": 2,
        "config": {"sample_questions": sample_questions},
        "data_sources": {
            "tables": [{"identifier": tid} for tid in table_identifiers],
            "metric_views": [],
        },
        "instructions": {
            "text_instructions": [],
            "example_question_sqls": [],
            "sql_functions": [],
            "join_specs": [],
            "sql_snippets": {"filters": [], "expressions": [], "measures": []},
        },
        "benchmarks": {"questions": []},
    }

    space = w.genie.create_space(
        warehouse_id=wh_id,
        serialized_space=json.dumps(serialized),
        title=title,
        description=description,
    )
    print(space.space_id)

    env_path = ROOT / ".env.local"
    line = f"{env_var}={space.space_id}"
    lines = env_path.read_text().splitlines() if env_path.exists() else []
    lines = [ln for ln in lines if not ln.strip().startswith(env_var)]
    lines.append(line)
    env_path.write_text("\n".join(lines) + "\n")
    print(f"Updated {env_path} with {env_var}={space.space_id}", file=sys.stderr)


if __name__ == "__main__":
    main()
