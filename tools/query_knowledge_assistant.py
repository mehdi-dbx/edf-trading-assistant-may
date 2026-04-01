"""Agent tool to query Knowledge Assistant (KA) endpoints for climate/energy data."""

import json
from typing import Any

from langchain_core.tools import tool

from databricks_openai import DatabricksOpenAI

from tools.ka_loader import get_endpoint_for_assistant, load_ka_mapping

# Tool return shape (JSON string): see _ka_tool_result_json.
# Citations come from the OpenAI Responses API `output[].content[]` items of type
# `output_text` and their `annotations` (file_citation, url_citation, etc.); see
# openai.types.responses.response_output_text.ResponseOutputText.


def _annotation_to_source(ann: Any) -> tuple[str, str] | None:
    """Map a single annotation to (title, excerpt) or None if unusable."""
    if ann is None:
        return None
    if isinstance(ann, dict):
        ann_type = ann.get("type")
        if ann_type == "file_citation":
            return (str(ann.get("filename") or "Document"), "")
        if ann_type == "url_citation":
            return (
                str(ann.get("title") or ann.get("url") or "Web source"),
                str(ann.get("url") or ""),
            )
        if ann_type == "container_file_citation":
            fn = ann.get("filename") or ann.get("file_id") or ""
            return (str(fn or "Document"), "")
        if ann_type == "file_path":
            return (str(ann.get("file_id") or "File"), "")
        return None
    ann_type = getattr(ann, "type", None)
    if ann_type == "file_citation":
        fn = getattr(ann, "filename", None)
        return (str(fn or "Document"), "")
    if ann_type == "url_citation":
        title = getattr(ann, "title", None) or getattr(ann, "url", None)
        url = getattr(ann, "url", None)
        return (str(title or "Web source"), str(url or ""))
    if ann_type == "container_file_citation":
        fn = getattr(ann, "filename", None) or getattr(ann, "file_id", None)
        return (str(fn or "Document"), "")
    if ann_type == "file_path":
        fid = getattr(ann, "file_id", None)
        return (str(fid or "File"), "")
    return None


def _sources_from_responses_output(response: Any, max_items: int = 20) -> list[dict[str, str]]:
    """Collect citation-like annotations from a Responses API `response.output` list."""
    sources: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    output = getattr(response, "output", None) or []
    for item in output:
        if getattr(item, "type", None) != "message":
            continue
        for content in getattr(item, "content", None) or []:
            if getattr(content, "type", None) != "output_text":
                continue
            for ann in getattr(content, "annotations", None) or []:
                pair = _annotation_to_source(ann)
                if not pair:
                    continue
                title, excerpt = pair
                key = (title, excerpt)
                if key in seen:
                    continue
                seen.add(key)
                sources.append({"title": title, "excerpt": excerpt})
                if len(sources) >= max_items:
                    return sources
    return sources


def _add_source(
    sources: list[dict[str, str]],
    seen: set[tuple[str, str]],
    title: str,
    excerpt: str,
    max_items: int,
) -> bool:
    if len(sources) >= max_items:
        return False
    key = (title, excerpt)
    if key in seen:
        return True
    seen.add(key)
    sources.append({"title": title, "excerpt": excerpt})
    return True


def _sources_from_dict_lists(data: Any, max_items: int = 20) -> list[dict[str, str]]:
    """Parse Amadeus-style `source_documents` / `sources` from a JSON object."""
    sources: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    if not isinstance(data, dict):
        return sources
    for key in ("source_documents", "sources", "documents"):
        arr = data.get(key)
        if not isinstance(arr, list):
            continue
        for item in arr:
            if not isinstance(item, dict):
                continue
            title = str(
                item.get("title")
                or item.get("document_name")
                or item.get("name")
                or "Source",
            )
            excerpt = str(item.get("excerpt") or item.get("text") or "")
            _add_source(sources, seen, title, excerpt, max_items)
            if len(sources) >= max_items:
                return sources
    return sources


def _sources_from_answer_text(answer: str, max_items: int = 20) -> list[dict[str, str]]:
    """If the model returns JSON (e.g. mitigation-style KA), merge embedded document lists."""
    a = answer.strip()
    if not a.startswith("{"):
        return []
    try:
        data = json.loads(a)
    except json.JSONDecodeError:
        return []
    return _sources_from_dict_lists(data, max_items=max_items)


def _walk_obj_for_citations(obj: Any, sources: list[dict[str, str]], seen: set[tuple[str, str]], max_items: int) -> None:
    """Find file_citation / url_citation objects anywhere in a model_dump tree."""
    if len(sources) >= max_items:
        return
    if isinstance(obj, dict):
        t = obj.get("type")
        if t in (
            "file_citation",
            "url_citation",
            "container_file_citation",
            "file_path",
        ):
            pair = _annotation_to_source(obj)
            if pair:
                title, excerpt = pair
                _add_source(sources, seen, title, excerpt, max_items)
        else:
            for v in obj.values():
                _walk_obj_for_citations(v, sources, seen, max_items)
    elif isinstance(obj, list):
        for item in obj:
            _walk_obj_for_citations(item, sources, seen, max_items)


def _sources_from_response_dump(response: Any, max_items: int = 20) -> list[dict[str, str]]:
    """Fallback: walk model_dump() for citation dicts (some gateways nest annotations differently)."""
    sources: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    try:
        if hasattr(response, "model_dump"):
            d = response.model_dump(mode="json")
        else:
            return sources
    except Exception:
        return sources
    _walk_obj_for_citations(d, sources, seen, max_items)
    return sources


def _merge_sources(
    answer: str,
    response: Any,
    max_items: int = 20,
) -> list[dict[str, str]]:
    seen: set[tuple[str, str]] = set()
    merged: list[dict[str, str]] = []
    for bucket in (
        _sources_from_responses_output(response, max_items=max_items),
        _sources_from_response_dump(response, max_items=max_items),
        _sources_from_answer_text(answer, max_items=max_items),
    ):
        for row in bucket:
            t, e = row["title"], row["excerpt"]
            _add_source(merged, seen, t, e, max_items)
            if len(merged) >= max_items:
                return merged
    return merged


def _ka_tool_result_json(answer: str, assistant_name: str, sources: list[dict[str, str]]) -> str:
    return json.dumps(
        {
            "answer": answer,
            "assistant_name": assistant_name,
            "sources": sources,
        },
        ensure_ascii=False,
    )


@tool(
    description=(
        "Query a Knowledge Assistant (KA) for climate/energy docs. "
        "assistant_name must be an exact display_name from data/ka.list (refresh via scripts/list_ka_endpoints.py). "
        "Args: assistant_name, question."
    ),
)
def query_knowledge_assistant(assistant_name: str, question: str) -> str:
    """Query a KA by display_name as listed in data/ka.list."""
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
        answer = response.output_text or ""
        sources = _merge_sources(answer, response)
        return _ka_tool_result_json(answer, assistant_name, sources)
    except Exception as e:
        return f"Error querying {endpoint}: {e}"
