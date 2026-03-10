"""Agent tool to query e-gate availability by zone."""

from pathlib import Path

from langchain_core.tools import tool

from data.sql_utils import substitute_schema
from tools.sql_executor import execute_query, format_query_result, get_warehouse, _escape_sql_string

_FUNC_DIR = Path(__file__).resolve().parents[1] / "data" / "func"


@tool
def query_egate_availability(zone: str) -> str:
    """E-gate availability: counts how many terminals are operational vs out of service in the given zone. zone: e.g. 'B'."""
    w, wh_id = get_warehouse()
    sql = substitute_schema((_FUNC_DIR / "egate_availability.sql").read_text().strip())
    zone_literal = "'" + _escape_sql_string(zone) + "'"
    stmt = sql.replace("{zone}", zone_literal)
    try:
        columns, rows = execute_query(w, wh_id, stmt)
        return format_query_result(columns, rows)
    except RuntimeError as e:
        return f"Error: {e}"
