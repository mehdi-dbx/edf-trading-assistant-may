"""LangGraph @tool: return a direct download link to a ZIP of all report PDFs from the Volume."""

import json
import os
from urllib.parse import urlencode

from langchain_core.tools import tool


def _get_download_base_url() -> str:
    """Base URL for the reports ZIP endpoint (e.g. http://localhost:8000 or app URL)."""
    base = os.environ.get("REPORTS_DOWNLOAD_BASE_URL", "").strip()
    if base:
        return base.rstrip("/")
    proxy = os.environ.get("API_PROXY", "").strip()
    if proxy:
        # e.g. http://localhost:8000/invocations -> http://localhost:8000
        return proxy.rsplit("/", 1)[0] if "/" in proxy else proxy
    return "http://localhost:8000"


@tool
def download_reports_tool(input: str = "") -> str:
    """Return a direct download link to a ZIP of all report PDFs from the Volume.

    Use this when the user asks to download reports, list reports, get reports, or see available reports.

    Input (optional): JSON string with optional "airline_slug" (str) to filter by airline
    (e.g. "air_france", "delta_air_lines"). If omitted, the ZIP includes all reports.

    Returns a single direct download URL. The user can open the URL in a browser to download the ZIP.
    """
    try:
        payload = json.loads(input) if input.strip() else {}
    except json.JSONDecodeError:
        payload = {}
    airline_slug = (payload.get("airline_slug") or "").strip().lower().replace(" ", "_") or None

    base_url = _get_download_base_url()
    path = "/api/reports.zip"
    if airline_slug:
        path += "?" + urlencode({"airline_slug": airline_slug})
    url = base_url + path
    return f"[Download All Reports]({url})"
