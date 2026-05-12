# Agent script output style (internal)

**Audience:** Cursor agent only. Apply when writing or editing CLI scripts in this repo so output matches `deploy/pre_deploy_verify_assets.py`, `scripts/init_check_dbx_env.py`, and similar.

---

## Non-negotiables

1. **TTY + `NO_COLOR`:** If script prints ANSI, implement all of:
   - `NO_COLOR` env → no ANSI
   - `sys.stdout.isatty()` false → no ANSI (unless forced; rarely needed)
   - argparse flag `--no-color` (alias `--plain`) when useful for logs/CI

2. **Stderr for errors:** User-facing failures, final “exit 1” messages → `print(..., file=sys.stderr)` when mixed with normal progress on stdout.

3. **Exit codes:** `0` = success; non-zero = failure (document in docstring).

4. **Shebang / path:** `#!/usr/bin/env python3`; resolve `ROOT = Path(__file__).resolve().parents[N]`; `chdir(ROOT)` only when the script must match other tools.

---

## ANSI palette (match existing scripts)

Use the same semantic mapping:

| Code   | Role                          |
|--------|-------------------------------|
| `\033[31m` R | failure text                 |
| `\033[32m` G | success counts / strong OK   |
| `\033[33m` Y | warnings                     |
| `\033[34m` B | section accents / resource labels |
| `\033[35m` M | highest privilege tokens     |
| `\033[36m` C | main banner / summary titles |
| `\033[0m`  W | reset                         |
| `\033[1m`  BOLD | titles                     |
| `\033[2m`  DIM  | metadata, labels           |

**Status glyphs (color + char):**

- OK: green `✓`
- FAIL: red `✗`
- WARN: yellow `⚠`
- SKIP / info pass: blue `→` (not “failure”)

**No-color fallback:** `[OK]`, `[FAIL]`, `[WARN]`, `[SKIP]` strings instead of glyphs.

**Implementation pattern:** `_theme(use_color: bool)` returning a small namespace with `R,G,Y,B,M,C,W,BOLD,DIM,OK,FAIL,WARN,SKIP` (see `pre_deploy_verify_assets.py`).

---

## Layout

1. **Lead blank line** before the main banner.
2. **Banner:** `{BOLD}{C}═══ {Script human title} ═══{W}`
3. **Context lines (DIM):** indented paths, `target=`, `bundle=`, etc.
4. **Blank line** after banner block.
5. **Major sections:** `{BOLD}{B}── {Section name} ──{W}` or `{BOLD}Identity{W}` then indented DIM labels + values.
6. **Per-item lines:** two spaces + status glyph + two spaces + body; indent continuation if needed.
7. **Closing:** blank line → `{BOLD}{C}── Summary ──{W}` → DIM stats → `{BOLD}{G}All checks passed.{W}` or FAIL line on stderr.

Use em-dash `—` in titles where existing scripts use it; use `→` only inside SKIP glyph or prose “x → y”.

---

## Semantic coloring (optional but preferred for ACL/verify scripts)

- Regex `\b(CAN_[A-Z_]+|IS_OWNER)\b` in messages.
- **Magenta:** `IS_OWNER`, `CAN_*MANAGE*`
- **Yellow:** `CAN_*VIEW*`, `CAN_*READ*`
- **Cyan:** other `CAN_*` (use/query/run/edit)
- **Bold blue** for substring before first `:` on a line (resource label).

Reuse `_colorize_permission_tokens` / `_colorize_verify_line` pattern from `pre_deploy_verify_assets.py` when applicable.

---

## Progress / long runs

- **Determinate:** print `[i/n]` in DIM at start of line or in section title, e.g. `── Batch 3/10 ──`.
- **Indeterminate:** one line per step with `✓`/`✗`; avoid spinner unless already used in repo.
- **Verbose:** gate with `--verbose` / `-v`; default stays quiet and summary-first.

---

## Argparse / UX

- Description: what it does, inputs, env, exit codes.
- Defaults shown in help; `metavar` where clarity helps.
- `--dry-run` for destructive or write operations when applicable.

---

## Bash scripts

- `set -euo pipefail` where appropriate.
- Echo banner with `═══` / `──` in same spirit; if `tput`/`NO_COLOR` available, prefer simple echo without color unless script already uses ANSI.
- Delegate Python-heavy formatting to Python helpers when consistency matters.

---

## Examples to copy

- Full theme + sections + summary: `deploy/pre_deploy_verify_assets.py` (`_theme`, `_print_header`, `_section_app`, `_line_result`, summary block).
- Interactive sections: `scripts/init_check_dbx_env.py` (`section()`, `OK`/`FAIL`/`WARN`).

---

## Anti-patterns

- Raw print of secrets or PATs.
- Hard-coded `uv run` in shebang-style docs when user asked for venv-only; prefer `"$ROOT/.venv/bin/python"` or `python3` + venv note.
- Inconsistent glyphs (mixing `*`/`x`/`[OK]` in color mode).
- Colors without `NO_COLOR` / non-TTY handling.
