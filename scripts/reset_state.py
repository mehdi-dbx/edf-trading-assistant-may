#!/usr/bin/env python3
"""Reset demo state by re-running create SQL scripts in sequence."""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)

from dotenv import load_dotenv

load_dotenv(ROOT / ".env.local", override=True)

# Order: example_data (no cross-deps)
SQL_SCRIPTS = [
    "data/init/create_example_data.sql",
]
PROCEDURE_SCRIPTS = []


def main() -> None:
    from databricks.sdk import WorkspaceClient
    from databricks.sdk.service.sql import ExecuteStatementRequestOnWaitTimeout

    from data.csv_to_delta import _wait_for_statement
    from data.sql_utils import substitute_schema

    w = WorkspaceClient()
    wh = os.environ.get("DATABRICKS_WAREHOUSE_ID") or next(iter(w.warehouses.list())).id
    wh_id = str(getattr(wh, "id", wh) or wh)

    for rel_path in SQL_SCRIPTS:
        path = ROOT / rel_path
        if not path.exists():
            print(f"Skip (not found): {path}", file=sys.stderr)
            continue
        content = substitute_schema(path.read_text().strip())
        if "CALL " in content:
            create, call = content.split("CALL ", 1)
            stmts = [create.strip(), "CALL " + call.strip()]
        else:
            stmts = [s.strip() for s in content.split(";\n\n") if s.strip()]
        for stmt in stmts:
            sql = stmt if stmt.endswith(";") else stmt + ";"
            _wait_for_statement(w, wh_id, sql)
        print(f"Ran {rel_path}", file=sys.stderr)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        import traceback
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)
