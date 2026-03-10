"""Agent tool to query check-in agents grouped by counter status."""

from pathlib import Path

from langchain_core.tools import tool

from data.sql_utils import substitute_schema
from tools.sql_executor import execute_query, format_query_result, get_warehouse, _escape_sql_string

_FUNC_DIR = Path(__file__).resolve().parents[1] / "data" / "func"


@tool
def query_checkin_agents_by_counter_status(zone: str) -> str:
    """Check-in agents grouped by counter status: counts per status (ACTIVE, BREAK, etc.) and lists agent IDs/names in the given zone. zone: e.g. 'B'."""
    w, wh_id = get_warehouse()
    sql = substitute_schema((_FUNC_DIR / "checkin_agents_by_counter_status.sql").read_text().strip())
    stmt = sql.replace("{zone}", _escape_sql_string(zone))
    try:
        columns, rows = execute_query(w, wh_id, stmt)
        return format_query_result(columns, rows)
    except RuntimeError as e:
        return f"Error: {e}"
