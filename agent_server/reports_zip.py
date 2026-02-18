"""Build a ZIP of report PDFs from the Unity Catalog Volume for download."""

import io
import os
import zipfile
from pathlib import Path


def get_volume_base() -> str:
    """Same volume base as pdf_report_tool."""
    volume_base = os.environ.get("VOLUME_BASE_PATH", "").strip()
    if volume_base and volume_base.startswith("/Volumes/"):
        return volume_base.rstrip("/")
    spec = os.environ.get("AMADEUS_UNITY_CATALOG_SCHEMA", "").strip()
    if "." in spec:
        catalog, schema = spec.split(".", 1)
        return f"/Volumes/{catalog}/{schema}/reports"
    return ""


def list_pdf_paths(volume_base: str, airline_slug: str | None) -> list[str]:
    """List full Volume paths to all PDFs under volume_base, optionally under one airline subdir."""
    from databricks.sdk import WorkspaceClient

    w = WorkspaceClient()
    paths: list[str] = []

    def list_pdfs(dir_path: str) -> None:
        try:
            for entry in w.files.list_directory_contents(dir_path):
                name = getattr(entry, "name", None) or ""
                full = f"{dir_path.rstrip('/')}/{name}"
                if getattr(entry, "is_directory", False):
                    list_pdfs(full)
                elif name.lower().endswith(".pdf"):
                    paths.append(full)
        except Exception:
            pass

    if airline_slug:
        list_pdfs(f"{volume_base}/{airline_slug}")
    else:
        try:
            for entry in w.files.list_directory_contents(volume_base):
                name = getattr(entry, "name", None) or ""
                if getattr(entry, "is_directory", False):
                    list_pdfs(f"{volume_base}/{name}")
        except Exception:
            pass
    paths.sort()
    return paths


def build_zip_bytes(volume_base: str, airline_slug: str | None) -> tuple[bytes, str]:
    """Download all report PDFs from the Volume and zip them. Returns (zip_bytes, filename)."""
    paths = list_pdf_paths(volume_base, airline_slug)
    if not paths:
        return b"", "reports.zip"

    from databricks.sdk import WorkspaceClient

    w = WorkspaceClient()
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for full_path in paths:
            try:
                resp = w.files.download(full_path)
                contents = getattr(resp, "contents", None)
                if contents is not None:
                    data = contents.read()
                    name = Path(full_path).name
                    zf.writestr(name, data)
            except Exception:
                continue
    buf.seek(0)
    filename = f"reports_{airline_slug}.zip" if airline_slug else "reports.zip"
    return buf.getvalue(), filename
