"""LangGraph @tool: send performance report PDF to one airline contact via Resend."""

import base64
import html
import os
import re
from pathlib import Path

import resend  # type: ignore[import-untyped]
from langchain_core.tools import tool

from template_loader import load_template


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
def send_email_report_tool(input: dict) -> str:
    """Send the check-in performance report PDF to one airline contact by email.

    Use this after generating the PDF (e.g. with pdf_report_tool) when the user
    asks to send or email the report to airline contacts.

    Required env: RESEND_API_KEY. Optional: EMAIL_FROM (default Amadeus Airport Insights <onboarding@resend.dev>).

    Input must be a JSON object with:
    - to_email (str): recipient email address.
    - contact_name (str): contact name for the greeting (e.g. "John Smith").
    - airline_name (str): airline name for subject and attachment (e.g. "Singapore Airlines").
    - pdf_path (str): absolute path to the PDF file (e.g. returned by pdf_report_tool).
    - period_label (str): report period for subject/body (e.g. "Jan 5-12, 2026").

    Returns a success message or an error description.
    """
    api_key = os.environ.get("RESEND_API_KEY")
    if not api_key:
        return "Error: RESEND_API_KEY is not set. Set it in the environment to send emails."

    from_email = os.environ.get(
        "EMAIL_FROM",
        "Amadeus Airport Insights <onboarding@resend.dev>",
    )

    try:
        to_email = input["to_email"]
        contact_name = input["contact_name"]
        airline_name = input["airline_name"]
        pdf_path = input["pdf_path"]
        period_label = input["period_label"]
    except KeyError as e:
        return f"Error: missing required input field {e}."

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
    if pdf_path.startswith("/Volumes/"):
        from databricks.sdk import WorkspaceClient

        w = WorkspaceClient()
        resp = w.files.download(pdf_path)
        if not getattr(resp, "contents", None):
            return f"Error: PDF file not found at {pdf_path}."
        pdf_bytes = resp.contents.read()
    else:
        path = Path(pdf_path)
        if not path.exists():
            return f"Error: PDF file not found at {pdf_path}."
        pdf_bytes = path.read_bytes()
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
    try:
        resend.Emails.send(params)
    except Exception as e:
        return f"Resend error: {e}"

    return f"Email sent to {to_email} with report attached ({attachment_filename})."
