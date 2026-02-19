"""Jinja2 HTML rendering and WeasyPrint PDF export for reports."""

from datetime import datetime, timezone
from pathlib import Path

from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML

from .models import ReportInput
from .utils import load_logo_b64


def _templates_dir() -> Path:
    return Path(__file__).resolve().parent / "templates"


def render_html(report_input: ReportInput) -> str:
    """Render report_input to HTML using the Jinja2 template."""
    templates_dir = _templates_dir()
    env = Environment(loader=FileSystemLoader(str(templates_dir)))
    template = env.get_template("report.html.j2")

    logo_b64 = load_logo_b64(report_input.logo_path)
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    return template.render(
        logo_b64=logo_b64,
        customer_name=report_input.customer_name,
        data=report_input.data,
        generated_at=generated_at,
    )


def render_pdf(html: str, output_path: Path) -> None:
    """Render HTML string to PDF at output_path."""
    try:
        HTML(string=html).write_pdf(str(output_path))
    except Exception as e:
        raise RuntimeError(f"Failed to write PDF to {output_path}: {e}") from e


if __name__ == "__main__":
    from models import ReportData, ReportInput, ReportSection

    dummy = ReportInput(
        customer_id="cust-001",
        customer_name="Acme Airlines",
        logo_path=str(Path(__file__).resolve().parent / "test_logo.png"),
        data=ReportData(
            summary="Check-in performance overview for Q1.",
            sections=[
                ReportSection(title="By airline", content="Table and analysis here."),
            ],
            metrics={"total_checkins": 15000, "avg_sla_pct": 93.5},
        ),
    )
    base = Path(__file__).resolve().parent
    html = render_html(dummy)
    html_path = base / "test_output.html"
    html_path.write_text(html, encoding="utf-8")
    print(f"Wrote {html_path} ({len(html)} chars).")

    pdf_path = base / "test_output.pdf"
    render_pdf(html, pdf_path)
    print(f"Wrote {pdf_path}. Open to verify layout, logo, margins.")
