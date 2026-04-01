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

    # Formats:
    #   Comment lines (# …) skipped.
    #   Aligned: serving_endpoint | display_name | … (space-padded, " | " separators).
    #   Legacy tab: endpoint\t#\tdisplay_name\t|\t…
    #   Legacy: display_name : value … or display_name=value
    display_re_colon = re.compile(r"display_name\s*:\s*(\S+)")
    display_re_eq = re.compile(r"display_name=(\S+)")

    def parse_aligned_pipe_line(line: str) -> tuple[str, str] | None:
        """Monospace-aligned row: ka-* | display_name | …"""
        if not line.startswith("ka-") or " | " not in line:
            return None
        parts = [p.strip() for p in line.split("|")]
        while parts and parts[-1] == "":
            parts.pop()
        if len(parts) < 2:
            return None
        endpoint_name, display_name = parts[0], parts[1]
        if not endpoint_name.startswith("ka-"):
            return None
        return endpoint_name, display_name

    def display_name_from_comment(comment: str) -> str | None:
        if "\t|\t" in comment:
            after_hash = comment[1:] if comment.startswith("#") else comment
            first = after_hash.split("\t|\t", 1)[0].strip().lstrip("\t")
            return first or None
        match = display_re_colon.search(comment) or display_re_eq.search(comment)
        return match.group(1).strip() if match else None

    for line in KA_LIST_PATH.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        aligned = parse_aligned_pipe_line(line)
        if aligned:
            endpoint_name, display_name = aligned
            key = display_name.lower()
            mapping[key] = endpoint_name
            continue
        parts = line.split("\t", 1)
        if len(parts) < 2:
            continue
        endpoint_name = parts[0].strip()
        comment = parts[1]
        display_name = display_name_from_comment(comment)
        if display_name:
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
