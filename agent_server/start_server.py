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

import requests as _requests
from fastapi import HTTPException
from fastapi.responses import StreamingResponse

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


@app.get("/files")
def serve_volume_file(path: str):
    """Proxy a UC Volume file from the Databricks Files API.

    `path` must be an absolute Volume path starting with /Volumes/...
    Auth lives here (Python backend) — Node server has no Databricks credentials.
    """
    if not path.startswith("/Volumes/"):
        raise HTTPException(status_code=400, detail="path must start with /Volumes/")
    from databricks.sdk import WorkspaceClient
    try:
        w = WorkspaceClient()
        host = (w.config.host or "").rstrip("/")
        auth_headers = w.config.authenticate()
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Databricks auth error: {e}")
    url = f"{host}/api/2.0/fs/files{path}"
    resp = _requests.get(url, headers=auth_headers, stream=True, timeout=30)
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail=resp.text[:200])
    media_type = resp.headers.get("content-type", "application/octet-stream")

    def _iter():
        for chunk in resp.iter_content(chunk_size=65536):
            if chunk:
                yield chunk

    return StreamingResponse(_iter(), media_type=media_type,
                             headers={"Content-Disposition": "inline"})


if os.environ.get("MLFLOW_EXPERIMENT_ID", "").strip():
    try:
        setup_mlflow_git_based_version_tracking()
    except Exception:
        # Stale experiment ID (e.g. after switching workspace) — deploy/import still works
        pass


def main():
    server.run(app_import_string="agent_server.start_server:app")
