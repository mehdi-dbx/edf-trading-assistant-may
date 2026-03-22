"""Parse data/ka.list and return endpoint mapping for Knowledge Assistants."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
KA_LIST_PATH = ROOT / "data" / "ka.list"


def load_ka_mapping() -> dict[str, str]:
    """
    Parse ka.list and return display_name -> endpoint_name mapping.
    Uses display_name as key (normalized to lowercase for matching).
    Skips comment lines and lines without display_name.
    """
    mapping: dict[str, str] = {}
    if not KA_LIST_PATH.exists():
        return mapping

    # Format: endpoint_name\t# id=... display_name=value
    display_re = re.compile(r"display_name=(\S+)")

    for line in KA_LIST_PATH.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split("\t", 1)
        if len(parts) < 2:
            continue
        endpoint_name = parts[0].strip()
        comment = parts[1]
        match = display_re.search(comment)
        if match:
            display_name = match.group(1).strip()
            # Normalize to lowercase for case-insensitive lookup
            key = display_name.lower()
            mapping[key] = endpoint_name
    return mapping


def get_endpoint_for_assistant(assistant_name: str, mapping: dict[str, str] | None = None) -> str | None:
    """
    Look up endpoint by assistant name. Supports exact match (lowercase) or
    substring match if exact fails.
    """
    if mapping is None:
        mapping = load_ka_mapping()
    normalized = assistant_name.strip().lower()
    if not normalized:
        return None
    # Exact match
    if normalized in mapping:
        return mapping[normalized]
    # Substring match: find first key that contains normalized or that normalized contains
    for key, endpoint in mapping.items():
        if normalized in key or key in normalized:
            return endpoint
    return None
