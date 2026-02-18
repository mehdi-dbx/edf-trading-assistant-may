"""Helpers: logo loading, path utilities."""

import base64
import os
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


def get_output_path(customer_id: str, volume_base: str) -> Path:
    """Return path for report PDF: <volume_base>/reports/<customer_id>/report.pdf.

    Creates parent directories if they do not exist.
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
