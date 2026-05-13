#!/usr/bin/env python3
"""Run a SQL file. Substitutes __SCHEMA_QUALIFIED__ and __VOLUME_PATH__ from UNITY_CATALOG_SCHEMA.
Usage: python data/run_sql.py <path/to/file.sql>"""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)

from dotenv import load_dotenv
load_dotenv(ROOT / ".env.local", override=True)

from databricks.sdk import WorkspaceClient
from data.csv_to_delta import _wait_for_statement
from data.sql_utils import substitute_schema

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python data/run_sql.py <path/to/file.sql>", file=sys.stderr)
        sys.exit(1)
    sql_path = sys.argv[1]
    path = Path(sql_path) if Path(sql_path).is_absolute() else ROOT / sql_path
    if not path.exists():
        print(f"File not found: {path}", file=sys.stderr)
        sys.exit(1)

    w = WorkspaceClient()
    wh = os.environ.get("DATABRICKS_WAREHOUSE_ID") or next(iter(w.warehouses.list())).id
    wh_id = str(getattr(wh, "id", wh) or wh)
    content = substitute_schema(path.read_text().strip())

    if "CALL " in content:
        create, call = content.split("CALL ", 1)
        stmts = [create.strip(), "CALL " + call.strip()]
    else:
        stmts = [s.strip() for s in content.split(";\n\n") if s.strip()]

    for stmt in stmts:
        sql = stmt if stmt.endswith(";") else stmt + ";"
        _wait_for_statement(w, wh_id, sql)
