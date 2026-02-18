"""LangGraph @tool entry point: generate branded PDF report from structured input."""

import json
import os
from pathlib import Path

from langchain_core.tools import tool

from models import ReportInput
from renderer import render_html, render_pdf
from utils import get_output_path


@tool
def pdf_report_tool(report_payload: str) -> str:
    """Generate a branded PDF report and save it to the configured output path.

    Use this when the user asks to export, save, or download the report as PDF.

    report_payload must be a JSON string of an object with:
    - customer_id (str): Unique customer identifier.
    - customer_name (str): Display name for the report header.
    - logo_path (str): Absolute path to logo image (PNG, JPG, or SVG).
    - data (object):
      - summary (str): Short report summary.
      - sections (list): Each item has "title" (str) and "content" (str).
      - metrics (object): Key-value pairs for the metrics table.

    Returns the absolute path where the PDF was written.
    """
    payload = json.loads(report_payload) if isinstance(report_payload, str) else report_payload
    report_input = ReportInput(**payload)
    volume_base = os.environ.get("VOLUME_BASE_PATH", "/tmp/pdf_reports")
    output_path = get_output_path(report_input.customer_id, volume_base)
    html = render_html(report_input)
    render_pdf(html, output_path)
    return str(output_path)


if __name__ == "__main__":
    base = Path(__file__).resolve().parent
    payload = {
        "customer_id": "cust-001",
        "customer_name": "Acme Airlines",
        "logo_path": str(base / "test_logo.png"),
        "data": {
            "summary": "Check-in performance overview for Q1.",
            "sections": [{"title": "By airline", "content": "Table and analysis here."}],
            "metrics": {"total_checkins": 15000, "avg_sla_pct": 93.5},
        },
    }
    result = pdf_report_tool.invoke({"report_payload": json.dumps(payload)})
    assert Path(result).exists(), f"PDF not created at {result}"
    print(f"Step 7 OK: PDF at {result}")
