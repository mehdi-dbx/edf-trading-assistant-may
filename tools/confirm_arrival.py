"""Agent tool to confirm agent arrival at counter via confirm_arrival procedure."""

from langchain_core.tools import tool

from data.sql_utils import get_schema_qualified
from tools.sql_executor import execute_statement, get_warehouse


@tool
def confirm_arrival(agent_id: str) -> str:
    """Confirm that an agent has arrived at their assigned counter. Call when the agent says "Arrived at Counter X" or similar.
    agent_id: e.g. 'A10'."""
    w, wh_id = get_warehouse()
    schema = get_schema_qualified()
    a = agent_id.replace("'", "''")
    stmt = f"CALL {schema}.confirm_arrival('{a}')"
    try:
        execute_statement(w, wh_id, stmt)
        return f"Confirmed arrival for {agent_id}."
    except RuntimeError as e:
        return f"Error: {e}"
