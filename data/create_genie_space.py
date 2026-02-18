#!/usr/bin/env python3
"""
Create Genie Space 'Amadeus Flight Check' with all tables from AMADEUS_UNITY_CATALOG_SCHEMA.

- Lists tables in the configured catalog.schema (Unity Catalog).
- Creates a Genie space with those tables as data sources and sample questions.
- Prints the new space_id to stdout.
- Writes AMADEUS_GENIE_CHECKIN=<space_id> into .env.local.

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
    # --- Resolve catalog and schema from env ---
    spec = os.environ.get("AMADEUS_UNITY_CATALOG_SCHEMA") or ""
    if "." not in spec:
        print("Set AMADEUS_UNITY_CATALOG_SCHEMA to catalog.schema", file=sys.stderr)
        sys.exit(1)
    catalog, schema = spec.strip().split(".", 1)

    from databricks.sdk import WorkspaceClient

    w = WorkspaceClient()

    # --- Resolve SQL warehouse (env or first available) ---
    wh_id = os.environ.get("DATABRICKS_WAREHOUSE_ID") or next(iter(w.warehouses.list()), None)
    if not wh_id:
        print("No warehouse. Set DATABRICKS_WAREHOUSE_ID or create one.", file=sys.stderr)
        sys.exit(1)
    wh_id = getattr(wh_id, "id", wh_id)

    # --- List all tables in the schema (used as Genie data sources) ---
    tables = list(w.tables.list(catalog_name=catalog, schema_name=schema))
    if not tables:
        print(f"No tables in {catalog}.{schema}. Run csv_to_delta.py first or add tables.", file=sys.stderr)
        sys.exit(1)

    table_identifiers = []
    for t in tables:
        full = getattr(t, "full_name", None) or f"{catalog}.{schema}.{t.name}"
        table_identifiers.append(full)

    # --- Build Genie serialized_space payload (version 2 format) ---
    def gen_id():
        return uuid.uuid4().hex[:24] + "0" * 8

    serialized = {
        "version": 2,
        "config": {
            "sample_questions": [
                {"id": gen_id(), "question": ["What are total check-ins by airline?"]},
                {"id": gen_id(), "question": ["Show load factor and SLA by airline"]},
            ]
        },
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

    # --- Create the Genie space ---
    space = w.genie.create_space(
        warehouse_id=wh_id,
        serialized_space=json.dumps(serialized),
        title="Amadeus Flight Check",
        description="Natural language exploration of check-in and flight performance data in Unity Catalog.",
    )
    print(space.space_id)

    # --- Persist space_id to .env.local as AMADEUS_GENIE_CHECKIN ---
    env_path = ROOT / ".env.local"
    line = f"AMADEUS_GENIE_CHECKIN={space.space_id}"
    lines = env_path.read_text().splitlines() if env_path.exists() else []
    lines = [ln for ln in lines if not ln.strip().startswith("AMADEUS_GENIE_CHECKIN")]
    lines.append(line)
    env_path.write_text("\n".join(lines) + "\n")
    print(f"Updated {env_path} with AMADEUS_GENIE_CHECKIN={space.space_id}", file=sys.stderr)


if __name__ == "__main__":
    main()
