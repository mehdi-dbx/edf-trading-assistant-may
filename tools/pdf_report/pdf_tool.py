"""LangGraph @tool entry point: generate branded PDF report from structured input."""

import json
import os
import tempfile
from pathlib import Path

from langchain_core.tools import tool

from .models import ReportInput
from .renderer import render_html, render_pdf
from .utils import get_volume_report_path, _slug


@tool
def pdf_report_tool(report_payload: str) -> str:
    """Generate a branded PDF report and save it to the configured Unity Catalog Volume.

    Use this when the user asks to export, save, or download the report as PDF.
    Call once per airline; each payload describes a single airline.

    report_payload must be a JSON string of an object with:
    - customer_id (str): Unique customer identifier (e.g. airline slug).
    - customer_name (str): Display name for the report header (e.g. airline name).
    - logo_path (str): Absolute Volume path to logo (e.g. /Volumes/.../reports/logos/air_france_logo.png).
    - data (object): summary (str), sections (list of title/content), metrics (object).
    - period_label (str, optional): e.g. "Jan 5-12, 2026" (for filename).
    - report_date (str, optional): e.g. "2026-02-01" or "2026-02-01 to 2026-02-07".

    Returns the Volume path where the PDF was written (no local download).
    """
    payload = json.loads(report_payload) if isinstance(report_payload, str) else report_payload
    report_input = ReportInput(**payload)
    volume_base = os.environ.get("VOLUME_BASE_PATH", "").strip()
    if not volume_base or not volume_base.startswith("/Volumes/"):
        volume_base = os.environ.get("AMADEUS_UNITY_CATALOG_SCHEMA", "").strip()
        if "." in volume_base:
            catalog, schema = volume_base.split(".", 1)
            volume_base = f"/Volumes/{catalog}/{schema}/reports"
        else:
            volume_base = "/tmp/pdf_reports"
    volume_path = get_volume_report_path(
        report_input.customer_name,
        volume_base,
        period_label=report_input.period_label,
        report_date=report_input.report_date,
    )
    # Always use per-airline logo (never default): .../reports/logos/{airline_slug}_logo.png
    base = volume_base.rstrip("/")
    per_airline_logo = f"{base}/logos/{_slug(report_input.customer_name)}_logo.png"
    report_input = report_input.model_copy(update={"logo_path": per_airline_logo})
    html = render_html(report_input)
    if volume_path.startswith("/Volumes/"):
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            temp_path = f.name
        try:
            render_pdf(html, Path(temp_path))
            from databricks.sdk import WorkspaceClient

            w = WorkspaceClient()
            parent = str(Path(volume_path).parent)
            try:
                w.files.create_directory(parent)
            except Exception:
                pass
            w.files.upload_from(file_path=volume_path, source_path=temp_path, overwrite=True)
            return volume_path
        finally:
            Path(temp_path).unlink(missing_ok=True)
    else:
        out_path = Path(volume_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        render_pdf(html, out_path)
        return volume_path


if __name__ == "__main__":
    base = Path(__file__).resolve().parent
    payload = {
        "customer_id": "cust-001",
        "customer_name": "Acme Airlines",
        "logo_path": str(base / "test_logo.png"),
        "period_label": "Jan 5-12, 2026",
        "report_date": "2026-02-01",
        "data": {
            "summary": "Check-in performance overview for Q1.",
            "sections": [{"title": "Performance", "content": "• Check-ins: 15000\n• Avg SLA: 93.5%"}],
            "metrics": {"total_checkins": 15000, "avg_sla_pct": 93.5},
        },
    }
    result = pdf_report_tool.invoke({"report_payload": json.dumps(payload)})
    if result.startswith("/Volumes/"):
        print(f"Step 7 OK: PDF uploaded to {result}")
    else:
        assert Path(result).exists(), f"PDF not created at {result}"
        print(f"Step 7 OK: PDF at {result}")
