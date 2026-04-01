#!/usr/bin/env python3
"""Fail if prompt files cite backtick tokens that are not valid Knowledge Assistant display_names.

Treats backtick content as a KA name candidate when it has no '*' and no '.' (skips schema refs
like `edf.chatbot` and wildcards like `daily_outlook_*`). Resolution uses the same logic as
get_endpoint_for_assistant (exact key, then substring match).

Usage:
  uv run python scripts/check_prompt_ka_names.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools.ka_loader import get_endpoint_for_assistant, load_ka_mapping

PROMPT_FILES = [
    ROOT / "prompt" / "main.prompt",
    ROOT / "prompt" / "knowledge.base",
]

BACKTICK_RE = re.compile(r"`([^`]+)`")


def _ka_candidate(token: str) -> bool:
    t = token.strip()
    if not t or "*" in t:
        return False
    if "." in t:
        return False
    return True


def main() -> int:
    mapping = load_ka_mapping()
    bad: list[tuple[str, str]] = []
    for path in PROMPT_FILES:
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        for tok in BACKTICK_RE.findall(text):
            if not _ka_candidate(tok):
                continue
            if get_endpoint_for_assistant(tok, mapping) is None:
                bad.append((str(path.relative_to(ROOT)), tok))

    if not bad:
        print("OK: KA-style backticks in prompt/ resolve via data/ka.list")
        return 0

    print(
        "Mismatch: these backtick tokens do not match any Knowledge Assistant in data/ka.list:",
        file=sys.stderr,
    )
    for rel, tok in sorted(bad):
        print(f"  {rel}: `{tok}`", file=sys.stderr)
    print(
        "\nRefresh data/ka.list: uv run python scripts/list_ka_endpoints.py",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
