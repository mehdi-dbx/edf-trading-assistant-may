from dotenv import load_dotenv
from mlflow.genai.agent_server import AgentServer, setup_mlflow_git_based_version_tracking

# Load env vars from .env then .env.local before importing the agent for proper auth
load_dotenv(dotenv_path=".env.local", override=True)

# Need to import the agent to register the functions with the server
import agent_server.agent  # noqa: E402

server = AgentServer("ResponsesAgent", enable_chat_proxy=True)

# Define the app as a module level variable to enable multiple workers
app = server.app  # noqa: F841

import os

from fastapi import HTTPException

from tools.sql_executor import execute_query, get_warehouse  # noqa: E402

ALLOWED_TABLES = frozenset(["example_data"])


@app.get("/tables/{table_name}")
def get_table(table_name: str):
    """Return table data from UC. Used by Node /api/tables proxy (avoids DATABRICKS_* env in Node)."""
    if table_name not in ALLOWED_TABLES:
        raise HTTPException(
            status_code=400,
            detail={"error": "Table not allowed", "allowed": list(ALLOWED_TABLES)},
        )
    schema_spec = os.environ.get("UNITY_CATALOG_SCHEMA", "").strip()
    if not schema_spec or "." not in schema_spec:
        raise HTTPException(
            status_code=502,
            detail="UNITY_CATALOG_SCHEMA not set (catalog.schema)",
        )
    catalog, schema = schema_spec.split(".", 1)
    full_table = (
        f"{catalog}.`{schema}`.{table_name}"
        if "-" in schema or " " in schema
        else f"{catalog}.{schema}.{table_name}"
    )
    statement = f"SELECT * FROM {full_table}"
    try:
        w_client, wh_id = get_warehouse()
        columns, rows = execute_query(w_client, wh_id, statement)
        return {"columns": columns, "rows": rows}
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))


if os.environ.get("MLFLOW_EXPERIMENT_ID", "").strip():
    try:
        setup_mlflow_git_based_version_tracking()
    except Exception:
        # Stale experiment ID (e.g. after switching workspace) — deploy/import still works
        pass


def main():
    server.run(app_import_string="agent_server.start_server:app")
