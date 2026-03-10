"""Agent tool to query border officers grouped by post status."""

from pathlib import Path

from langchain_core.tools import tool

from data.sql_utils import substitute_schema
from tools.sql_executor import execute_query, format_query_result, get_warehouse, _escape_sql_string

_FUNC_DIR = Path(__file__).resolve().parents[1] / "data" / "func"


@tool
def query_border_officers_by_post(zone: str) -> str:
    """Border officers grouped by post status: counts officers per status and lists officer_id/name in the given zone. zone: e.g. 'B'."""
    w, wh_id = get_warehouse()
    sql = substitute_schema((_FUNC_DIR / "border_officers_by_post.sql").read_text().strip())
    stmt = sql.replace("{zone}", _escape_sql_string(zone))
    try:
        columns, rows = execute_query(w, wh_id, stmt)
        return format_query_result(columns, rows)
    except RuntimeError as e:
        return f"Error: {e}"
