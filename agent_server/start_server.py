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
from pydantic import BaseModel
from mlflow.genai.agent_server import AgentServer, setup_mlflow_git_based_version_tracking

# Load env vars from .env then .env.local before importing the agent for proper auth
load_dotenv(dotenv_path=".env", override=True)
load_dotenv(dotenv_path=".env.local", override=True)

# Need to import the agent to register the functions with the server
import agent_server.agent  # noqa: E402
from agent_server.reports_zip import build_zip_bytes, get_volume_base
from tools.email_report.email_tool import send_email_report_tool

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


class SendReportRecipient(BaseModel):
    airline_name: str
    contact_name: str
    to_email: str
    pdf_path: str
    period_label: str


class SendReportEmailsRequest(BaseModel):
    recipients: list[SendReportRecipient]


@app.post("/api/send-report-emails")
def send_report_emails(body: SendReportEmailsRequest):
    """Send report PDFs to the given recipients. Each recipient must have airline_name, contact_name, to_email, pdf_path, period_label."""
    try:
        results = []
        for r in body.recipients:
            try:
                out = send_email_report_tool.invoke({
                    "input": {
                        "to_email": r.to_email,
                        "contact_name": r.contact_name,
                        "airline_name": r.airline_name,
                        "pdf_path": r.pdf_path,
                        "period_label": r.period_label,
                    }
                })
            except Exception as e:
                results.append({"airline_name": r.airline_name, "to_email": r.to_email, "result": f"Error: {e}"})
                continue
            results.append({"airline_name": r.airline_name, "to_email": r.to_email, "result": out})
        return {"sent": len(body.recipients), "results": results}
    except Exception as e:
        import traceback
        traceback.print_exc()
        return Response(
            content='{"error":"Internal Server Error","detail":"' + str(e).replace('"', '\\"') + '"}',
            status_code=500,
            media_type="application/json",
        )


def main():
    server.run(app_import_string="agent_server.start_server:app")
