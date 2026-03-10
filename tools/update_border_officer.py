"""Agent tool to update border officer at_post via update_border_officer procedure."""

from langchain_core.tools import tool

from data.sql_utils import get_schema_qualified
from tools.sql_executor import execute_statement, get_warehouse


@tool
def update_border_officer(officer_id: str, at_post: str) -> str:
    """Update a border officer's at_post status. Call when operator confirms pulling an officer off break or redeploying.
    officer_id: e.g. 'O03'. at_post: ACTIVE, AWAY, or BREAK."""
    w, wh_id = get_warehouse()
    schema = get_schema_qualified()
    o = officer_id.replace("'", "''")
    ap = at_post.replace("'", "''")
    stmt = f"CALL {schema}.update_border_officer('{o}', '{ap}')"
    try:
        execute_statement(w, wh_id, stmt)
        return f"Updated officer {officer_id} to {at_post}."
    except RuntimeError as e:
        return f"Error: {e}"
