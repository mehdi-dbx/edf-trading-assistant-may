"""Agent tool to redeploy check-in agents via mc.`amadeus-checkin`.update_checkin_agent procedure."""

from langchain_core.tools import tool

from tools.sql_executor import execute_statement, get_warehouse


@tool
def update_checkin_agent(agent_id: str, zone: str, counter: str, at_counter: str) -> str:
    """Redeploy an agent to a zone/counter. Call when operator confirms redeploying an available agent (e.g. from root cause analysis recommendations).
    agent_id: e.g. 'A14'. zone: e.g. 'B'. counter: e.g. 'B08'. at_counter: ACTIVE, AWAY, BREAK, or AVAILABLE."""
    w, wh_id = get_warehouse()
    a = agent_id.replace("'", "''")
    z = zone.replace("'", "''")
    c = counter.replace("'", "''")
    ac = at_counter.replace("'", "''")
    stmt = f"CALL mc.`amadeus-checkin`.update_checkin_agent('{a}', '{z}', '{c}', '{ac}')"
    try:
        execute_statement(w, wh_id, stmt)
        return f"Redeployed {agent_id} to Zone {zone}, counter {counter}, {at_counter}."
    except RuntimeError as e:
        return f"Error: {e}"
