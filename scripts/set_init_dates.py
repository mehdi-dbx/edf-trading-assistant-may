#!/usr/bin/env python3
"""Set all dates in data/init to the given date.

Replaces date patterns in SQL and Python files under data/init:
- 2026-02-25T10:00:00.000 -> {date}T{time}.000
- 2026-02-25 10:30:00 -> {date} {time}
- CAST('2026-02-25 10:00:00' AS TIMESTAMP_NTZ) -> CAST('{date} {time}' AS TIMESTAMP_NTZ)

Usage:
  uv run python scripts/set_init_dates.py 2026-03-01
  uv run python scripts/set_init_dates.py 2026-03-01 10:00:00
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INIT_DIR = ROOT / "data" / "init"

# Patterns: match date+time in SQL and Python files
# Pattern 1: ISO with T - '2026-02-25T10:00:00.000'
RE_ISO = re.compile(r"(\d{4}-\d{2}-\d{2})T(\d{2}:\d{2}:\d{2}\.\d{3})")
# Pattern 2: SQL timestamp - '2026-02-25 10:30:00' or CAST('2026-02-25 10:00:00' AS ...)
RE_SQL = re.compile(r"(\d{4}-\d{2}-\d{2})\s+(\d{2}:\d{2}:\d{2})")


def replace_dates(content: str, new_date: str, new_time: str | None = None) -> str:
    """Replace date parts with new_date. If new_time, replace times too; else preserve."""
    if new_time:
        def iso_repl(_m: re.Match) -> str:
            return f"{new_date}T{new_time}.000"

        def sql_repl(_m: re.Match) -> str:
            return f"{new_date} {new_time}"
    else:
        def iso_repl(m: re.Match) -> str:
            return f"{new_date}T{m.group(2)}"

        def sql_repl(m: re.Match) -> str:
            return f"{new_date} {m.group(2)}"

    content = RE_ISO.sub(iso_repl, content)
    content = RE_SQL.sub(sql_repl, content)
    return content


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: set_init_dates.py YYYY-MM-DD [HH:MM:SS]", file=sys.stderr)
        print("  YYYY-MM-DD       New date (required)", file=sys.stderr)
        print("  HH:MM:SS         Optional: replace all times with this", file=sys.stderr)
        return 1

    new_date = sys.argv[1].strip()
    if not re.match(r"\d{4}-\d{2}-\d{2}$", new_date):
        print(f"Invalid date format: {new_date}. Use YYYY-MM-DD", file=sys.stderr)
        return 1

    new_time = sys.argv[2].strip() if len(sys.argv) > 2 else None
    if new_time and not re.match(r"\d{2}:\d{2}:\d{2}$", new_time):
        print(f"Invalid time format: {new_time}. Use HH:MM:SS", file=sys.stderr)
        return 1

    if not INIT_DIR.exists():
        print(f"Directory not found: {INIT_DIR}", file=sys.stderr)
        return 1

    changed = 0
    for path in sorted(INIT_DIR.iterdir()):
        if path.suffix not in (".sql", ".py"):
            continue
        text = path.read_text()
        new_text = replace_dates(text, new_date, new_time)
        if new_text != text:
            path.write_text(new_text)
            print(f"Updated {path.relative_to(ROOT)}")
            changed += 1

    if changed == 0:
        print("No date changes needed.")
    else:
        print(f"Updated {changed} file(s) to date {new_date}" + (f" {new_time}" if new_time else ""))

    return 0


if __name__ == "__main__":
    sys.exit(main())
