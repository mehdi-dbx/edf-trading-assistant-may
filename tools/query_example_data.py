"""Agent tool to query example_data table."""

from pathlib import Path

from langchain_core.tools import tool

from data.sql_utils import substitute_schema
from tools.sql_executor import execute_query, format_query_result, get_warehouse

_FUNC_DIR = Path(__file__).resolve().parents[1] / "data" / "func"


@tool
def query_example_data() -> str:
    """Query the example_data table. Returns id, value, updated_at columns."""
    w, wh_id = get_warehouse()
    sql = substitute_schema((_FUNC_DIR / "example_query.sql").read_text().strip())
    try:
        columns, rows = execute_query(w, wh_id, sql)
        return format_query_result(columns, rows)
    except RuntimeError as e:
        return f"Error: {e}"
