"""Agent tool to query staffing duties for an agent (NEW status)."""

from pathlib import Path

from langchain_core.tools import tool

from tools.sql_executor import execute_query, format_query_result, get_warehouse, _escape_sql_string

_FUNC_DIR = Path(__file__).resolve().parents[1] / "data" / "func"


@tool
def query_staffing_duties(agent_id: str) -> str:
    """Staffing duties: lists rows from checkin_agents where agent has staffing_status NEW (zone, counter, assigned_by_id, assigned_at). agent_id: e.g. 'A10'."""
    w, wh_id = get_warehouse()
    sql = (_FUNC_DIR / "staffing_duties.sql").read_text().strip()
    stmt = sql.replace("{agent_id}", _escape_sql_string(agent_id))
    try:
        columns, rows = execute_query(w, wh_id, stmt)
        return format_query_result(columns, rows)
    except RuntimeError as e:
        return f"Error: {e}"
