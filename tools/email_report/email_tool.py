"""LangGraph @tool: send performance report PDF to one airline contact via Resend."""

import base64
import html
import json
import os
import re
import time
import resend  # type: ignore[import-untyped]
from langchain_core.tools import tool

from .template_loader import load_template

TRACE_LOG_PATH = "/Users/mehdi.lamrani/code/_/amadeus-airops/.cursor/debug.log"


def _trace_log(message: str, data: dict):
    try:
        with open(TRACE_LOG_PATH, "a") as f:
            f.write(json.dumps({"timestamp": time.time() * 1000, "location": "email_tool.py", "message": message, "data": data}) + "\n")
    except Exception:
        pass


def _slug(s: str) -> str:
    """Filesystem-safe slug: spaces and punctuation to single underscore."""
    s = re.sub(r"[^\w\s-]", "", s)
    s = re.sub(r"[-\s]+", "_", s).strip("_")
    return s or "report"


def _period_slug(period_label: str) -> str:
    """e.g. 'Jan 5-12, 2026' -> 'Jan5-12_2026'."""
    return _slug(period_label.replace(",", " "))


def substitute(template: str, contact_name: str, airline_name: str, period_label: str) -> str:
    """Replace placeholders. Handles [Contact Namel] as [Contact Name]."""
    out = template.replace("[Contact Name]", contact_name)
    out = out.replace("[Contact Namel]", contact_name)
    out = out.replace("[Airline Name]", airline_name)
    out = out.replace("[Period]", period_label)
    out = out.replace("[Period Long]", period_label)
    out = out.replace("[Airline]", _slug(airline_name))
    out = out.replace("[PeriodSlug]", _period_slug(period_label))
    return out


def _body_to_html(body: str) -> str:
    """Convert plain text body to simple HTML (paragraphs and line breaks)."""
    escaped = html.escape(body)
    paragraphs = [p.strip() for p in escaped.split("\n\n") if p.strip()]
    return "".join(f"<p>{p.replace(chr(10), '<br/>')}</p>" for p in paragraphs)


@tool
def send_email_report_tool(*args, **kwargs) -> str:
    """Send the check-in performance report PDF to one airline contact.

    Call with to_email, contact_name, airline_name, pdf_path, period_label. Sends the report PDF to that recipient. Required env: RESEND_API_KEY.

    To build the recipient checklist first: call get_airline_contacts_tool to get the contact list, match contacts to your airlines (from report/PDF context), build the email_recipients list, and output it for the UI. Then call this tool once per recipient to send (or let the UI call the send API on confirm).
    """
    # #region agent log
    _trace_log("tool received", {"hypothesisId": "B", "args_len": len(args), "args0_keys": list(args[0].keys()) if args and isinstance(args[0], dict) else None, "kwargs_keys": list(kwargs.keys())})
    # #endregion
    # Backend calls .invoke({"input": {...}}); runnable may pass as positional arg or as kwargs
    payload = args[0] if args and isinstance(args[0], dict) else kwargs
    data = payload.get("input", payload) if isinstance(payload, dict) else kwargs
    if isinstance(data, str):
        try:
            data = json.loads(data)
        except json.JSONDecodeError:
            return "Error: input must be valid JSON with to_email, contact_name, airline_name, pdf_path, period_label."
    if not isinstance(data, dict):
        data = kwargs
    # Unwrap when framework nests: e.g. invoke({"input": {...}}) becomes input={"input": {...}}
    if isinstance(data, dict) and "input" in data and not data.get("to_email"):
        data = data.get("input", data)

    has_send_fields = (
        isinstance(data, dict)
        and data.get("to_email")
        and data.get("contact_name")
        and data.get("airline_name")
        and data.get("pdf_path")
        and data.get("period_label")
    )
    if not has_send_fields:
        # #region agent log
        _trace_log("early return: recipient list msg (no send fields)", {"hypothesisId": "B", "has_send_fields": False})
        # #endregion
        return (
            "To get the recipient list: call get_airline_contacts_tool to fetch contacts, match them to your airlines (with pdf_path and period_label from context), build email_recipients, and output the checklist. To send an email: call this tool with to_email, contact_name, airline_name, pdf_path, period_label."
        )

    api_key = os.environ.get("RESEND_API_KEY")
    if not api_key:
        return "Error: RESEND_API_KEY is not set. Set it in the environment to send emails."

    from_email = os.environ.get(
        "EMAIL_FROM",
        "Amadeus Airport Insights <onboarding@resend.dev>",
    )

    to_email = data["to_email"]
    contact_name = data["contact_name"]
    airline_name = data["airline_name"]
    pdf_path = data["pdf_path"]
    period_label = data["period_label"]

    try:
        subject_tpl, body_tpl, attachment_tpl = load_template()
    except FileNotFoundError as e:
        return str(e)

    subject = substitute(subject_tpl, contact_name, airline_name, period_label)
    body = substitute(body_tpl, contact_name, airline_name, period_label)
    html_content = _body_to_html(body)

    attachment_filename = substitute(
        attachment_tpl, contact_name, airline_name, period_label
    )
    if not pdf_path.startswith("/Volumes/"):
        return "Error: pdf_path must be a Unity Catalog Volume path (e.g. /Volumes/catalog/schema/reports/...). Local paths are not supported."
    from databricks.sdk import WorkspaceClient

    # #region agent log
    _trace_log("downloading PDF", {"hypothesisId": "E", "pdf_path": pdf_path, "to_email": to_email})
    # #endregion
    w = WorkspaceClient()
    resp = w.files.download(pdf_path)

    if not getattr(resp, "contents", None):
        # #region agent log
        _trace_log("PDF not found (no contents)", {"hypothesisId": "E", "pdf_path": pdf_path})
        # #endregion
        return f"Error: PDF file not found at {pdf_path}."
    pdf_bytes = resp.contents.read()
    # #region agent log
    _trace_log("PDF downloaded", {"hypothesisId": "E", "pdf_path": pdf_path, "bytes": len(pdf_bytes)})
    # #endregion
    
    if len(pdf_bytes) > 40 * 1024 * 1024:
        return "Error: PDF is larger than 40MB; Resend cannot send it."
    pdf_b64 = base64.b64encode(pdf_bytes).decode("ascii")

    resend.api_key = api_key
    params = {
        "from": from_email,
        "to": [to_email],
        "subject": subject,
        "html": html_content,
        "attachments": [
            {"filename": attachment_filename, "content": pdf_b64},
        ],
    }
    # #region agent log
    _trace_log("calling Resend.Emails.send", {"hypothesisId": "C", "to_email": to_email, "from_email": from_email})
    # #endregion
    try:
        r = resend.Emails.send(params)
        # #region agent log
        _trace_log("Resend.Emails.send returned", {"hypothesisId": "D", "to_email": to_email, "resend_return": str(r) if r is not None else "None", "resend_type": type(r).__name__})
        # #endregion
    except Exception as e:
        # #region agent log
        _trace_log("Resend exception", {"hypothesisId": "C", "to_email": to_email, "error_type": type(e).__name__, "error_msg": str(e)})
        # #endregion
        return f"Resend error: {e}"

    return f"Email sent to {to_email} with report attached ({attachment_filename})."
