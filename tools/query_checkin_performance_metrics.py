"""Agent tool to query check-in performance metrics by zone (optional)."""

from pathlib import Path

from langchain_core.tools import tool

from tools.sql_executor import execute_query, format_query_result, get_warehouse, _escape_sql_string

_FUNC_DIR = Path(__file__).resolve().parents[1] / "data" / "func"


@tool
def query_checkin_performance_metrics(zone: str | None = None) -> str:
    """Check-in performance metrics: latest avg check-in time, baseline, % change vs baseline, and anomaly flag. zone: optional, e.g. 'B' for Zone B only; omit for all zones."""
    w, wh_id = get_warehouse()
    sql = (_FUNC_DIR / "checkin_performance_metrics.sql").read_text().strip()
    zone_filter = f"AND zone = '{_escape_sql_string(zone)}'" if zone else ""
    stmt = sql.replace("{zone_filter}", zone_filter)
    try:
        columns, rows = execute_query(w, wh_id, stmt)
        return format_query_result(columns, rows)
    except RuntimeError as e:
        return f"Error: {e}"
