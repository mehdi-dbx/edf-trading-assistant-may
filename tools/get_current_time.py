"""Tool to return the current UTC date and time."""

from datetime import datetime, timezone

from langchain_core.tools import tool


@tool(description="Return the current UTC date and time. Use this whenever you need today's date or the current time.")
def get_current_time() -> str:
    """Return current UTC datetime as ISO 8601 string."""
    now = datetime.now(timezone.utc)
    return now.strftime("%Y-%m-%dT%H:%M:%SZ")
