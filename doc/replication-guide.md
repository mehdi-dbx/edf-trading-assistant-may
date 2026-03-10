# Replication Guide: Genie SQL Capture, Functions, Tools, and Prompt

This document instructs another Cursor instance how to replicate the changes made in this project. The target project has the same codebase **before** these patches.

**Reference root:** You have access to the root folder of this (amadeus-checkin) project. Replace `{REF}` below with that path. Example: if your workspace is `/path/to/amadeus-checkin`, use that as `{REF}`.

---

## Purpose and Rationale

**Problem:** Genie's NLP-to-SQL is slow. Each natural language query triggers an async Genie call, then a poll, and the translation adds latency.

**Solution:** Capture the SQL that Genie generates, then turn it into dedicated SQL tools. The agent uses these tools directly instead of Genie for known flows—same queries, faster execution. Genie remains available for ad-hoc questions that have no dedicated tool.

**What we did:**
1. **Genie SQL capture** – Intercept Genie tool calls, extract SQL from responses, write to disk.
2. **Comment and rename** – Add business summaries to captured SQL; give files descriptive names.
3. **Parameterized templates** – Create `data/func/*.sql` with placeholders (`{zone}`, `{time_start}`, etc.).
4. **Query tools** – Python tools that load templates, substitute params, execute via Databricks, return results.
5. **Prompt update** – Replace Genie instructions with explicit tool calls for each flow.

---

## Part 1: Genie SQL Capture (Replicate First)

### Destination Folders

| Path | Purpose |
|------|---------|
| `data/genie-capture-sql/` | Captured SQL files. Create directory; add `.gitkeep` if empty. |
| `agent_server/genie_capture.py` | New module. |

### Steps

1. **Create `data/genie-capture-sql/`**
   - Add `.gitkeep` so the folder is tracked when empty.

2. **Create `agent_server/genie_capture.py`**
   - Copy from `{REF}/agent_server/genie_capture.py` or implement from the spec below.

3. **Integrate in `agent_server/agent.py`**
   - Add: `from agent_server.genie_capture import wrap_for_genie_capture`
   - After `mcp_tools = await mcp_client.get_tools()`, add:
     ```python
     wrapped_tools = [wrap_for_genie_capture(t) for t in mcp_tools]
     ```
   - Use `wrapped_tools` (not `mcp_tools`) when building the `tools` list passed to `create_agent`.

### Implementation Spec (genie_capture.py)

- **CAPTURE_DIR:** `Path(__file__).resolve().parents[1] / "data" / "genie-capture-sql"`
- **Genie tool detection:** Tool name (lowercase) contains `genie`, `query_space`, or `poll_response`.
- **Query from args:** Extract from tool input dict: `query` or `message` (the NL question sent to Genie).
- **SQL extraction (order):**
  - JSON: `content["query"]`, `content["queryAttachments"][i]["query"]`, `content["structured_content"]`, `attachments`
  - MCP tuple: `(content, artifact)` — check `artifact["structured_content"]` and `artifact["queryAttachments"]`
  - Markdown: ` ```sql ... ``` ` blocks
  - Fallback: raw output starting with `SELECT`, `WITH`, `INSERT`, `UPDATE`, `DELETE`
- **Filename:** From `query` arg. Sanitize: spaces→underscores, invalid chars→`_`, collapse repeated `_`, trim trailing `_`, truncate to 60 chars. If no query, use first 50 chars of SQL.
- **Wrapper:** Use `StructuredTool.from_function` with `func=_run`, `coroutine=_arun`, `**kwargs` passed to underlying tool. Best-effort: log failures, never raise.

**Reference:** `{REF}/agent_server/genie_capture.py`

---

## Part 2: Full Pipeline (SQL Functions, Tools, Prompt)

### Data Layout

| Path | Purpose | Deployed to Databricks? |
|------|---------|------------------------|
| `data/init/` | CREATE TABLE scripts | Yes, via `scripts/reset_state.py` |
| `data/proc/` | Stored procedures | Yes, via `scripts/reset_state.py` |
| `data/func/` | Parameterized SQL templates | **No** — used by tools at runtime |
| `data/genie-capture-sql/` | Captured SQL from Genie | No |

**Important:** The files in `data/func/` are NOT Unity Catalog UDFs. They are SQL templates stored as files. The tools load them, substitute placeholders, and execute via the Databricks `statement_execution` API. No `CREATE FUNCTION` in the workspace is needed.

### Step 1: Comment and Rename genie-capture-sql Files

For each SQL file in `data/genie-capture-sql/`:

- Add a top-line comment: `-- Business summary: what the query retrieves.`
- Rename files from `SELECT_...` or generic names to descriptive names, e.g.:
  - `egate_availability_zone_b.sql`
  - `flights_at_risk_zone_b.sql`
  - `checkin_performance_metrics.sql`
  - `available_agents_for_redeployment.sql`
  - `border_officer_staffing_zone_b.sql`
  - `checkin_agent_staffing_zone_b.sql`
  - `border_terminal_details_zone_b.sql`
  - `border_officers_by_post_zone_b.sql`
  - `checkin_agents_by_counter_status_zone_b.sql`

**Reference:** `{REF}/data/genie-capture-sql/`

### Step 2: Create data/func/ Parameterized Templates

For each genie-capture SQL, create a corresponding file in `data/func/`:

- Replace hardcoded values with placeholders: `{zone}`, `{time_start}`, `{time_end}`, `{zone_filter}`, `{zone_pattern}`, `{agent_id}`.
- Use `{zone_filter}` for optional zone: tool substitutes `AND zone = 'B'` or empty string.
- Use `{zone_pattern}` for ILIKE: tool substitutes `'%B%'` (quoted).
- Escape all user values in tools via `_escape_sql_string` (replace `'` with `''`).

**Example (flights_at_risk):**
```sql
-- Params: {zone}, {time_start}, {time_end}
SELECT ... WHERE zone = '{zone}' AND departure_time >= TIMESTAMP('{time_start}') AND departure_time < TIMESTAMP('{time_end}') ...
```

**Reference:** `{REF}/data/func/*.sql`

### Step 3: Extend tools/sql_executor.py

Add:

- `_escape_sql_string(s: str) -> str` — replace `'` with `''`
- `execute_query(w, wh_id, stmt) -> tuple[list[str], list[list]]` — execute SELECT, return (columns, rows). Use `Format.JSON_ARRAY`, `Disposition.INLINE`. Poll if PENDING/RUNNING; fetch chunks via `get_statement_result_chunk_n` if needed.
- `format_query_result(columns, rows) -> str` — format as pipe-separated table for agent.

**Reference:** `{REF}/tools/sql_executor.py`

### Step 4: Create tools/query_*.py

One tool per func file. Pattern:

```python
from pathlib import Path
from langchain_core.tools import tool
from tools.sql_executor import execute_query, format_query_result, get_warehouse, _escape_sql_string

_FUNC_DIR = Path(__file__).resolve().parents[1] / "data" / "func"

@tool
def query_<name>(...params...) -> str:
    """Docstring describing what the query returns."""
    w, wh_id = get_warehouse()
    sql = (_FUNC_DIR / "<name>.sql").read_text().strip()
    stmt = sql.replace("{zone}", _escape_sql_string(zone)).replace(...)  # all placeholders
    try:
        columns, rows = execute_query(w, wh_id, stmt)
        return format_query_result(columns, rows)
    except RuntimeError as e:
        return f"Error: {e}"
```

**Reference:** `{REF}/tools/query_*.py`

### Step 5: Register Tools in agent.py

Import each `query_*` tool and add to the `tools` list in `init_agent()` (alongside existing tools like `get_current_time`, `update_flight_risk`, etc.).

**Reference:** `{REF}/agent_server/agent.py` (lines 28–76)

### Step 6: Update Prompt

In `prompt/main.prompt`:

1. **Add SQL-tools-first principle** (after "Current time"):  
   `**Data queries:** Prefer SQL tools over Genie. Use the query_* tools below for each request type. Genie is slower (NLP-to-SQL); only use Genie when no SQL tool exists.`

2. **Replace each Genie instruction** with the corresponding tool:
   - Border Control Performance: `query_checkin_performance_metrics(zone)` or `query_checkin_performance_metrics()`
   - Check-in Performance: same
   - Identify at-risk flights: `get_current_time(advance=True)`, parse time, add 60 min, then `query_flights_at_risk(zone, time_start, time_end)`
   - Root cause data sources: `query_checkin_agent_staffing(zone)`, `query_available_agents_for_redeployment(zone)`, `query_border_officer_staffing(zone)`, `query_egate_availability(zone)`
   - LIST DUTIES (Agent persona): `query_staffing_duties(agent_id)` — requires `func/staffing_duties.sql` (SELECT zone, counter, assigned_by_id, assigned_at FROM checkin_agents WHERE agent_id = '{agent_id}' AND staffing_status = 'NEW') and `query_staffing_duties` tool

**Reference:** `{REF}/prompt/main.prompt`, `{REF}/data/func/staffing_duties.sql`, `{REF}/tools/query_staffing_duties.py`

### Step 7: Workspace Setup

- Tables and procedures: run `scripts/reset_state.py` (or `python data/run_sql.py` for individual files) to create tables and procedures in the Databricks workspace.
- The func templates are NOT deployed; they are file-based and used by Python tools at runtime.

---

## Summary: Reference Paths

| What | Path |
|------|------|
| Genie capture module | `{REF}/agent_server/genie_capture.py` |
| Agent integration | `{REF}/agent_server/agent.py` |
| SQL executor | `{REF}/tools/sql_executor.py` |
| Query tools | `{REF}/tools/query_*.py` |
| Func templates | `{REF}/data/func/*.sql` |
| Genie-capture SQL | `{REF}/data/genie-capture-sql/*.sql` |
| Prompt | `{REF}/prompt/main.prompt` |
