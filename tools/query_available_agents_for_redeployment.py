"""Agent tool to query available agents for redeployment."""

from pathlib import Path

from langchain_core.tools import tool

from data.sql_utils import substitute_schema
from tools.sql_executor import execute_query, format_query_result, get_warehouse, _escape_sql_string

_FUNC_DIR = Path(__file__).resolve().parents[1] / "data" / "func"


@tool
def query_available_agents_for_redeployment(zone: str | None = None) -> str:
    """Available agents for redeployment: lists check-in agents currently on break or available (not at counter). zone: optional, e.g. 'B'; omit for all zones."""
    w, wh_id = get_warehouse()
    sql = substitute_schema((_FUNC_DIR / "available_agents_for_redeployment.sql").read_text().strip())
    zone_filter = f"AND zone = '{_escape_sql_string(zone)}'" if zone else ""
    stmt = sql.replace("{zone_filter}", zone_filter)
    try:
        columns, rows = execute_query(w, wh_id, stmt)
        return format_query_result(columns, rows)
    except RuntimeError as e:
        return f"Error: {e}"
