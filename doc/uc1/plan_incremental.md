# UC1 Turnaround — Incremental build plan

Build and test in small steps. Each step is one chunk; we verify before moving on.

---

## Phase 1 — Data and tables

### Step 1.1 — Add `data/flights.csv`
- Create CSV with 5 flights for today, including BA243.
- Columns: `flight_number`, `scheduled_date`, `eta_minutes`, `tobt`, `predicted_ready`, `readiness_status`.
- BA243: tightest buffer (tobt − predicted_ready), `readiness_status = AMBER`.
- **Verify:** File exists, columns correct, BA243 has smallest buffer when computed.

### Step 1.2 — Add `data/turnaround_events.csv`
- Rows for BA243 only; tasks: ULD/Baggage Load, Cleaning, Load Sheet.
- Columns: `flight_number`, `task_name`, `task_status`, `tobt`, `predicted_ready`, `readiness_status`, `event_timestamp`.
- Each task: Pending → Notified → In Progress → Completed; timestamps a few minutes apart.
- **Verify:** File exists, status progression makes sense.

### Step 1.3 — Run `csv_to_delta.py` and enable CDF on `turnaround_events`
- Run `python data/csv_to_delta.py` (or pass `data/flights.csv` then `data/turnaround_events.csv`).
- Ensure `turnaround_events` has CDF: either extend [data/csv_to_delta.py](data/csv_to_delta.py) to set `delta.enableChangeDataFeed = true` for that table, or run a one-off `ALTER TABLE ... SET TBLPROPERTIES (...)` after creation.
- **Verify:** In Databricks, both tables exist in `AMADEUS_UNITY_CATALOG_SCHEMA`; `turnaround_events` has CDF enabled.

### Step 1.4 — Turnaround Genie space and `AMADEUS_GENIE_TURNAROUND`
- Rewrite [data/create_genie_space.py](data/create_genie_space.py) so it can create a **Turnaround** space (title/description for Flight Prioritisation + Turnaround), using tables `flights` and `turnaround_events` from `AMADEUS_UNITY_CATALOG_SCHEMA`, and write the space ID to `.env.local` as `AMADEUS_GENIE_TURNAROUND`.
- Decide: one script with two modes (check-in vs turnaround) or a dedicated turnaround script; either way, output env var is `AMADEUS_GENIE_TURNAROUND`.
- **Verify:** Run script; `.env.local` contains `AMADEUS_GENIE_TURNAROUND=<id>`; in Genie, space has both tables and answers a prioritisation-style question.

### Step 1.5 — Wire Turnaround Genie MCP in the agent
- In [agent_server/agent.py](agent_server/agent.py), extend `init_mcp_client`: when `AMADEUS_GENIE_TURNAROUND` is set, append a second `DatabricksMCPServer` (e.g. name `genie-turnaround`, same URL pattern `{host}/api/2.0/mcp/genie/{space_id}`). Do not add a new tool; Genie tools come from MCP. Existing check-in MCP (`genie-checkin` + `AMADEUS_GENIE_CHECKIN`) can stay as-is.
- **Verify:** Restart app, ask "Which flight to prioritise?"; agent should use the Turnaround Genie MCP and return a ranked list (e.g. BA243 first).

---

## Phase 2 — Tools (one at a time)

### Step 2.1 — `get_turnaround_checklist` tool
- New tool: reads `turnaround_events` in `AMADEUS_UNITY_CATALOG_SCHEMA` (from env), filters by `flight_number`, returns current task list (latest status per task).
- **Verify:** Standalone test with flight BA243; then add to agent and ask "What's the checklist for BA243?".

### Step 2.2 — `poll_tms` tool
- New tool: input `last_version` (int); reads `turnaround_events` via Delta CDF from that version; filters `_change_type` in (`update_postimage`, `insert`); returns new events and new `last_version`.
- **Verify:** Standalone test: call with `last_version=0`, get events and next version; add to agent and call when user asks for “latest updates” or “status”.

---

## Phase 3 — Agent flow and prompt

### Step 3.1 — UC1 system prompt
- Add or adjust system prompt (e.g. in [prompt/main.prompt](prompt/main.prompt)) for the two-block flow: (1) Prioritise using Genie (Turnaround MCP), recommend top flight, ask for confirmation; (2) On confirm, use `get_turnaround_checklist`, show checklist, (optionally) notify teams, report readiness vs TOBT; use `poll_tms` when user asks for updates.
- **Verify:** Chat through “Which flight to prioritise?” → agent recommends BA243 → “Yes, coordinate BA243” → agent shows checklist and status.

### Step 3.2 — (Optional) Background polling and queue
- **Deferred per design (out of scope):** Background thread, 30s CDF poll, queue, drain-on-response, stream events to chat. We can add this later; for now the agent can call `poll_tms` on demand when the user asks for status.

---

## Summary

| Phase | Steps | What we test |
|-------|--------|--------------|
| 1     | 1.1–1.5 | CSVs, Delta tables, CDF, Genie space, `.env.local`, Turnaround Genie MCP in agent |
| 2     | 2.1–2.2 | `get_turnaround_checklist` and `poll_tms` in isolation, then wired into agent |
| 3     | 3.1–3.2 | Prompt and full conversation; optional polling later |

We do one step at a time and only move on when the “Verify” for that step is done.
