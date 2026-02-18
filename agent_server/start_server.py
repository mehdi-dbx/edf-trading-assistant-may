import os
import sys

# --- BEGIN: TEMPORARY LOCAL TESTING ONLY - REMOVE FOR DATABRICKS ---
# On macOS, WeasyPrint (PDF report tool) needs Homebrew Pango/Cairo; not needed on Databricks.
if sys.platform == "darwin":
    brew_lib = "/opt/homebrew/lib"
    if os.path.isdir(brew_lib):
        existing = os.environ.get("DYLD_LIBRARY_PATH", "")
        os.environ["DYLD_LIBRARY_PATH"] = f"{brew_lib}{':' + existing if existing else ''}"
# --- END: TEMPORARY LOCAL TESTING ONLY - REMOVE FOR DATABRICKS ---

from dotenv import load_dotenv
from fastapi import Response
from mlflow.genai.agent_server import AgentServer, setup_mlflow_git_based_version_tracking

# Load env vars from .env then .env.local before importing the agent for proper auth
load_dotenv(dotenv_path=".env", override=True)
load_dotenv(dotenv_path=".env.local", override=True)

# Need to import the agent to register the functions with the server
import agent_server.agent  # noqa: E402
from agent_server.reports_zip import build_zip_bytes, get_volume_base

server = AgentServer("ResponsesAgent", enable_chat_proxy=True)

# Define the app as a module level variable to enable multiple workers
app = server.app  # noqa: F841
setup_mlflow_git_based_version_tracking()


@app.get("/api/reports.zip")
def download_reports_zip(airline_slug: str | None = None):
    """Return a ZIP of all report PDFs from the Volume. Optional airline_slug to filter."""
    volume_base = get_volume_base()
    if not volume_base or not volume_base.startswith("/Volumes/"):
        return Response(content="No Volume configured", status_code=503)
    zip_bytes, filename = build_zip_bytes(volume_base, airline_slug)
    if not zip_bytes:
        return Response(content="No report PDFs found", status_code=404)
    return Response(
        content=zip_bytes,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def main():
    server.run(app_import_string="agent_server.start_server:app")
