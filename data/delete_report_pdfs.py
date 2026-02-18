#!/usr/bin/env python3
"""Delete existing PDF report files in the Unity Catalog Volume (reports Volume).

Usage:
  uv run python data/delete_report_pdfs.py
      Delete all PDFs under /Volumes/{catalog}/{schema}/reports (all airlines).

  uv run python data/delete_report_pdfs.py [airline_slug]
      Delete only PDFs under .../reports/{airline_slug}/ (e.g. air_france).

Uses AMADEUS_UNITY_CATALOG_SCHEMA or VOLUME_BASE_PATH for the Volume path.
"""
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)
load_dotenv(ROOT / ".env", override=True)
load_dotenv(ROOT / ".env.local", override=True)


def get_volume_base() -> str:
    volume_base = os.environ.get("VOLUME_BASE_PATH", "").strip()
    if volume_base and volume_base.startswith("/Volumes/"):
        return volume_base.rstrip("/")
    spec = os.environ.get("AMADEUS_UNITY_CATALOG_SCHEMA", "").strip()
    if "." in spec:
        catalog, schema = spec.split(".", 1)
        return f"/Volumes/{catalog}/{schema}/reports"
    return ""


def list_pdf_paths(w, volume_base: str, airline_slug: str | None) -> list[str]:
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
        except Exception as e:
            print(f"Error listing: {e}", file=sys.stderr)
            sys.exit(1)
    paths.sort()
    return paths


def main() -> None:
    from databricks.sdk import WorkspaceClient

    volume_base = get_volume_base()
    if not volume_base or not volume_base.startswith("/Volumes/"):
        print("Set VOLUME_BASE_PATH or AMADEUS_UNITY_CATALOG_SCHEMA (catalog.schema).", file=sys.stderr)
        sys.exit(1)

    airline_slug = (sys.argv[1].strip().lower().replace(" ", "_") if len(sys.argv) > 1 else None) or None

    w = WorkspaceClient()
    paths = list_pdf_paths(w, volume_base, airline_slug)
    if not paths:
        print("No PDF report files found." + (f" (filter: {airline_slug})" if airline_slug else ""))
        return
    for p in paths:
        try:
            w.files.delete(p)
            print(f"Deleted: {p}")
        except Exception as e:
            print(f"Failed to delete {p}: {e}", file=sys.stderr)
    print(f"Done. Deleted {len(paths)} file(s).")


if __name__ == "__main__":
    main()
