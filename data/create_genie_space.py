#!/usr/bin/env python3
"""
Create a Genie space with tables from AMADEUS_UNITY_CATALOG_SCHEMA.

Modes (first arg):
  checkin     — All tables, title "Amadeus Flight Check", writes AMADEUS_GENIE_CHECKIN (default).
  turnaround  — Only flights + turnaround_events, title "Turnaround", writes AMADEUS_GENIE_TURNAROUND.

Prints space_id to stdout. Updates .env.local with the corresponding env var.

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

TURNAROUND_TABLES = {"flights", "turnaround_events"}


def main():
    mode = (sys.argv[1] if len(sys.argv) > 1 else "").strip().lower() or "checkin"
    if mode not in ("checkin", "turnaround"):
        print("Usage: python3 data/create_genie_space.py [checkin|turnaround]", file=sys.stderr)
        sys.exit(1)

    spec = os.environ.get("AMADEUS_UNITY_CATALOG_SCHEMA") or ""
    if "." not in spec:
        print("Set AMADEUS_UNITY_CATALOG_SCHEMA to catalog.schema", file=sys.stderr)
        sys.exit(1)
    catalog, schema = spec.strip().split(".", 1)

    from databricks.sdk import WorkspaceClient
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
        name = getattr(t, "name", None) or ""
        if mode == "turnaround" and name not in TURNAROUND_TABLES:
            continue
        full = getattr(t, "full_name", None) or f"{catalog}.{schema}.{t.name}"
        table_identifiers.append(full)

    if mode == "turnaround" and len(table_identifiers) < 2:
        print("Turnaround mode needs flights and turnaround_events. Run csv_to_delta.py first.", file=sys.stderr)
        sys.exit(1)

    def gen_id():
        return uuid.uuid4().hex[:24] + "0" * 8

    if mode == "turnaround":
        title = "Turnaround"
        description = "Flight prioritisation and turnaround coordination. Flights and turnaround_events in Unity Catalog."
        sample_questions = [
            {"id": gen_id(), "question": ["Rank inbound flights by buffer (tobt minus predicted_ready) ascending"]},
            {"id": gen_id(), "question": ["Which flight has the tightest buffer today?"]},
        ]
        env_var = "AMADEUS_GENIE_TURNAROUND"
    else:
        title = "Amadeus Flight Check"
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
