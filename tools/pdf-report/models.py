"""Pydantic models for report input schema."""

from typing import Any

from pydantic import BaseModel


class ReportSection(BaseModel):
    """A single section of the report."""

    title: str
    content: str


class ReportData(BaseModel):
    """Structured report content: summary, sections, metrics."""

    summary: str
    sections: list[ReportSection]
    metrics: dict[str, Any]


class ReportInput(BaseModel):
    """Top-level input for the PDF report tool."""

    customer_id: str
    customer_name: str
    logo_path: str
    data: ReportData


if __name__ == "__main__":
    dummy = ReportInput(
        customer_id="cust-001",
        customer_name="Acme Airlines",
        logo_path="/Volumes/main/logos/cust-001/logo.png",
        data=ReportData(
            summary="Check-in performance overview for Q1.",
            sections=[
                ReportSection(title="By airline", content="Table and analysis here."),
            ],
            metrics={"total_checkins": 15000, "avg_sla_pct": 93.5},
        ),
    )
    print(dummy)
