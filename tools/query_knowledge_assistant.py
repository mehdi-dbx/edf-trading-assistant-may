"""Agent tool to query Knowledge Assistant (KA) endpoints for climate/energy data."""

from langchain_core.tools import tool

from databricks_openai import DatabricksOpenAI

from tools.ka_loader import get_endpoint_for_assistant, load_ka_mapping


@tool(
    description="Query a Knowledge Assistant (KA) for climate/energy docs. Args: assistant_name (from prompt), question.",
)
def query_knowledge_assistant(assistant_name: str, question: str) -> str:
    """Query a Knowledge Assistant by assistant_name (from ka.list) with a question."""
    mapping = load_ka_mapping()
    endpoint = get_endpoint_for_assistant(assistant_name, mapping)
    if not endpoint:
        available = ", ".join(sorted(mapping.keys())[:5]) + ("..." if len(mapping) > 5 else "")
        return f"Unknown assistant '{assistant_name}'. Available: {available}. Use exact display_name from the list."
    try:
        client = DatabricksOpenAI()
        response = client.responses.create(
            model=endpoint,
            input=[{"role": "user", "content": question}],
            max_output_tokens=2048,
        )
        return response.output_text or ""
    except Exception as e:
        return f"Error querying {endpoint}: {e}"
