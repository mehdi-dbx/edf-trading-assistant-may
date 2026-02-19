"""Helpers: logo loading, path utilities."""

import base64
import os
import re
from datetime import datetime, timezone
from pathlib import Path


def get_default_logo_path() -> str:
    """Default logo path on the Volume (align with data/upload_img_to_volume.py)."""
    explicit = os.environ.get("DEFAULT_LOGO_PATH", "").strip()
    if explicit:
        return explicit
    spec = os.environ.get("AMADEUS_UNITY_CATALOG_SCHEMA", "").strip()
    if "." in spec:
        catalog, schema = spec.split(".", 1)
        return f"/Volumes/{catalog}/{schema}/reports/logos/default/logo.png"
    return "/Volumes/main/default/reports/logos/default/logo.png"


def _read_logo_bytes(path: str) -> tuple[bytes, str]:
    """Read logo from Databricks Volume via Files API. No local filesystem. Fallback to default Volume path if needed."""
    if not path.strip().startswith("/Volumes/"):
        path = get_default_logo_path()
    suffix = Path(path).suffix.lower()
    # Databricks Files API; may require DATABRICKS_ENABLE_EXPERIMENTAL_FILES_API_CLIENT=true
    from databricks.sdk import WorkspaceClient

    w = WorkspaceClient()
    resp = w.files.download(path)
    if not getattr(resp, "contents", None):
        fallback = get_default_logo_path()
        if fallback != path:
            return _read_logo_bytes(fallback)
        raise FileNotFoundError(f"Logo file not found: {path}")
    raw = resp.contents.read()
    return raw, suffix


def load_logo_b64(path: str) -> str:
    """Read logo from Databricks Volume (Files API), base64-encode, return as data URI.

    Always uses Databricks; no local path. If path is not a Volume path or download fails, uses get_default_logo_path().
    Supports png, jpg, jpeg, svg. Raises FileNotFoundError if file is missing on the Volume.
    """
    raw, suffix = _read_logo_bytes(path)
    mime = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".svg": "image/svg+xml",
    }.get(suffix)
    if not mime:
        raise ValueError(f"Unsupported logo format: {suffix}. Use png, jpg, or svg.")
    b64 = base64.b64encode(raw).decode("ascii")
    return f"data:{mime};base64,{b64}"


def _slug(name: str) -> str:
    """Filesystem-safe slug: spaces and punctuation to single underscore, lowercase."""
    s = re.sub(r"[^\w\s-]", "", name)
    s = re.sub(r"[-\s]+", "_", s).strip("_").lower()
    return s or "report"


def _period_suffix(period_label: str | None) -> str:
    """Short period hint for filename (no duplicate text). e.g. 'last 7 days' -> '7days'."""
    if not period_label or not period_label.strip():
        return "report"
    pl = period_label.strip().lower()
    if "7 days" in pl or "7day" in pl or "last 7" in pl:
        return "7days"
    if "14 days" in pl or "14day" in pl or "last 14" in pl:
        return "14days"
    if "30 days" in pl or "30day" in pl or "last 30" in pl or "1 month" in pl:
        return "30days"
    # Date range like "Jan 5-12, 2026" -> Jan_5_12_2026 (short slug, no spaces)
    s = _slug(period_label.replace(",", " ").replace("-", "_"))
    return s[:24] if len(s) > 24 else s or "report"


def get_volume_report_path(
    airline_name: str,
    volume_base: str,
    period_label: str | None = None,
    report_date: str | None = None,
) -> str:
    """Return Volume path string for one report: {volume_base}/{airline_slug}/{filename}.pdf.

    Filename: {airline_slug}_perf_{YYYY_MM_DD}_{period_suffix}.pdf
    (e.g. qatar_airways_perf_2026_02_18_7days.pdf). Uses generation date to avoid duplicates.
    """
    slug = _slug(airline_name)
    gen_date = datetime.now(timezone.utc).strftime("%Y_%m_%d")
    period_hint = _period_suffix(period_label)
    filename = f"{slug}_perf_{gen_date}_{period_hint}.pdf"
    base = volume_base.rstrip("/")
    return f"{base}/{slug}/{filename}"


def get_output_path(customer_id: str, volume_base: str) -> Path:
    """Return path for report PDF: <volume_base>/reports/<customer_id>/report.pdf.

    Creates parent directories if they do not exist. Kept for backward compatibility in tests.
    """
    out_dir = Path(volume_base) / "reports" / customer_id
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir / "report.pdf"


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "path":
        # Test get_output_path
        p = get_output_path("cust-001", "/tmp/volume_test")
        assert "reports" in str(p) and "cust-001" in str(p) and p.name == "report.pdf"
        assert p.parent.exists()
        print(f"Path: {p}")
        print("Step 6 OK: path pattern correct, parent dir created.")
    else:
        path = sys.argv[1] if len(sys.argv) > 1 else get_default_logo_path()
        result = load_logo_b64(path)
        print(result[:80])
