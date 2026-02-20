"""Placeholder agent tool. Replace with real same-domain tools under tools/<name>/."""

from langchain_core.tools import tool


@tool
def placeholder_tool(input: str = "") -> str:
    """Placeholder for new reports/data tools. Returns a short message."""
    return "New tools (reports/data) coming soon."
