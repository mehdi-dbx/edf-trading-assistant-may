Here's your updated Cursor prompt:

---

We are building **Garv AI Ops Advisor** — an AI agent for airport ground operations. The UI and base LangGraph agent are already implemented.

We are now implementing **Use Case 1: Turnaround**

---

**What we are building**
- A two block agent flow: Flight Prioritisation → Turnaround Coordination
- Agent reads live data, reasons, recommends, executes and monitors

---

**Block 1 — Flight Prioritisation**

- User asks agent which flight to prioritise
- Agent calls Genie (space from `AMADEUS_GENIE_TURNAROUND` in .env.local) with a natural language query to rank inbound flights by priority
- Genie has access to the `flights` Delta table in `AMADEUS_UNITY_CATALOG_SCHEMA`
- Priority rules to include in the Genie prompt:
  - Compute buffer = tobt - predicted_ready for each flight
  - Rank by smallest buffer first
  - Flag flights where readiness_status is AMBER or RED
  - Return flight_number, eta_minutes, tobt, predicted_ready, buffer, readiness_status ordered by buffer ascending
- Agent receives ranked list, selects top flight (BA243)
- Agent presents recommendation to user with reasoning:
  - Arrives in N minutes
  - Tightest buffer vs TOBT
  - Downstream tasks already queued
  - Other flights have sufficient slack
- Agent asks user to confirm before proceeding

---

**Block 2 — Turnaround Coordination**

- User confirms → agent triggers turnaround for selected flight
- Agent reads `turnaround_events` Delta table (in `AMADEUS_UNITY_CATALOG_SCHEMA`) directly to get current task checklist for that flight
- Agent displays initial checklist with current statuses:
  - ULD/Baggage Load
  - Cleaning
  - Load Sheet
- Agent notifies relevant teams (write mock notification to table)
- Agent reports: Readiness vs TOBT status · Predicted Ready time
- Agent enters live monitoring loop (see Polling Mechanism below)

---

**Polling Mechanism**

- A background thread runs independently from the conversation loop
- It polls the `turnaround_events` Delta table (in `AMADEUS_UNITY_CATALOG_SCHEMA`) via Change Data Feed (CDF) every 30 seconds
- On each tick:
  - Read CDF from `startingVersion = last_version`
  - Filter for `_change_type = update_postimage` or `insert`
  - If new rows found → format event message → push into a queue
  - Update `last_version` to the latest `_commit_version` seen
  - If nothing new → silent, wait for next tick
- `last_version` is stored server side as a session variable (demo scope)
- On every agent response cycle → agent drains the queue first → streams any queued events to chat → then responds to user
- Monitoring exits when:
  - All tasks for the flight reach status Completed
  - Current time reaches TOBT

---

**Environment and data location**

- **Unity Catalog schema:** All tables for this use case live in the schema set by `AMADEUS_UNITY_CATALOG_SCHEMA` in [.env.local](.env.local) (e.g. `mc.amadeus-tms` = catalog `mc`, schema `amadeus-tms`).
- **Synthetic data (source):** CSV files under the repo folder [data/](data/). Add `flights.csv` and `turnaround_events.csv` with the specs below.
- **Table creation:** [data/csv_to_delta.py](data/csv_to_delta.py) uploads `data/*.csv` to the Volume `data` in that schema and creates Delta tables in the same schema. Run it after adding or changing CSVs (e.g. `python data/csv_to_delta.py` for all CSVs, or pass a single file path). For `turnaround_events`, CDF must be enabled (e.g. `ALTER TABLE ... SET TBLPROPERTIES (delta.enableChangeDataFeed = true)`); add this in the script or run once after table creation.
- **Genie space for Turnaround:** `AMADEUS_GENIE_TURNAROUND` in [.env.local](.env.local) is filled by running the updated [data/create_genie_space.py](data/create_genie_space.py). That script will be rewritten to create a Genie space for Turnaround (Flight Prioritisation + Turnaround Coordination) using the new UC tables (`flights`, `turnaround_events`) and to write the new space ID into `.env.local` as `AMADEUS_GENIE_TURNAROUND`.

---

**What we need — Synthetic Data (CSV → Delta)**

`flights` table (source: `data/flights.csv`)
- 5 flights for today including BA243
- Fields: flight_number, scheduled_date, eta_minutes, tobt, predicted_ready, readiness_status
- BA243 must have the tightest buffer and readiness_status = AMBER

`turnaround_events` table (source: `data/turnaround_events.csv`)
- BA243 only
- Tasks: ULD/Baggage Load · Cleaning · Load Sheet
- Each task goes through: Pending → Notified → In Progress → Completed
- Fields: flight_number, task_name, task_status, tobt, predicted_ready, readiness_status, event_timestamp
- Timestamps must be sequential and realistic with a few minutes between each status change
- In Unity Catalog: Delta table with `delta.enableChangeDataFeed = true` (CDF required for the polling mechanism)

---

**What we need — Genie (existing MCP) and LangGraph tools**

**Genie for Block 1 (no new tool)**  
- The agent already uses Genie via MCP in [agent_server/agent.py](agent_server/agent.py) (`init_mcp_client` + `DatabricksMCPServer`). For UC1 we add a second MCP server for the Turnaround Genie space: when `AMADEUS_GENIE_TURNAROUND` is set in .env.local, add a server (e.g. name `genie-turnaround`) with the same URL pattern `{host}/api/2.0/mcp/genie/{space_id}`. After we create the Turnaround Genie space (Step 1.4), the agent will use that MCP to query `flights` and get a ranked list; no separate `query_genie` tool.

`get_turnaround_checklist` tool
- Reads `turnaround_events` Delta table in `AMADEUS_UNITY_CATALOG_SCHEMA`
- Filters by flight_number
- Returns current task list with latest status per task

`poll_tms` tool
- Reads `turnaround_events` (in `AMADEUS_UNITY_CATALOG_SCHEMA`) via Delta CDF
- Input: last_version (int)
- Output: list of new events since last_version, updated last_version
- Filters for meaningful change types only (update_postimage, insert)

---

**Out of scope**
- UI changes
- Polling loop itself (just the tool)
- Multiple flights monitored simultaneously