# Simulated current time tool

Single source of truth for **simulated time** in the UC1 turnaround scenario. Used by the agent and by the header time widget so both stay in sync.

## Module: `tools/get_current_time.py`

### What it does

- Holds a **fixed queue** of timestamps (e.g. 13:50, 13:55, 14:00, …).
- Exposes:
  - **`get_next_time(advance: bool = True, backward: bool = False) -> str`** — returns a timestamp; if `backward=True`, steps the queue back (with wrap) then returns; if `advance=True`, steps forward then returns; else peeks.
  - **`get_current_time(advance: bool = False)`** — LangChain tool used by the agent; wraps `get_next_time(advance)` and returns a string like `"Current time: 2025-02-20T13:50:00.000"`.

### Advance vs peek vs backward

| Call | Params | Effect | Typical use |
|------|--------|--------|-------------|
| **Peek** | `advance=False` | Returns current time **without** moving the queue. | Widget initial load (show time without consuming a step). |
| **Advance** | `advance=True` | Moves the queue **forward** by one step, then returns the new current time. | Widget “Skip” (forward) click; agent when it needs the time for this turn (e.g. before querying Genie). |
| **Backward** | `backward=True` | Moves the queue **back** by one step (with wrap: index 0 → last), then returns the new current time. | Widget “Backwards” button (left of time). |

So:

- **Widget:** on load calls with `advance=false` (peek); on Backwards click calls with `backward=true`; on Skip (forward) click calls with `advance=true`.
- **Agent:** when it needs simulated time for the turn (e.g. turnaround checklist), it must call the tool with **`advance=True`** so it “takes” that time and stays aligned with the widget.

### Queue behaviour

- **Peek:** `_index` unchanged; returns `_TIME_QUEUE[_index % len(_TIME_QUEUE)]`.
- **Advance:** `_index` is incremented, then the value at the new index is returned. So the first advance after a peek returns the *next* time in the queue (e.g. 13:55 after 13:50).
- **Backward:** `_index` is set to `(_index - 1) % len(_TIME_QUEUE)` (wrap: from 0 backward goes to last), then the value at the new index is returned.
- The queue is **cyclic** in both directions: after the last timestamp, advance wraps to the first; from the first, backward wraps to the last.
- Access is **thread-safe** (one lock around queue read/update).

### HTTP API

The agent server exposes **GET /current-time** with query params **`advance`** (default `false`) and **`backward`** (default `false`):

- `GET /current-time` or `?advance=false&backward=false` → peek (no move).
- `GET /current-time?advance=true` → advance and return new time.
- `GET /current-time?backward=true` → step back (with wrap) and return new time.

Response: `{"currentTime": "2025-02-20T13:55:00.000"}`.

The Node server proxies **GET /api/current-time?advance=...&backward=...** to the backend; the header widget uses it for peek (on mount), backward (Backwards button), and advance (Skip forward button).

### Timestamp format

- Stored and returned **without** timezone (e.g. `2025-02-20T13:50:00.000`).
- The frontend displays them as-is (no conversion to user local time), so the widget shows “13:50”, “13:55”, etc. for the scenario.

### Prompt

The agent prompt instructs: when you need the simulated time for this turn (e.g. Block 2 turnaround or checklist), call **get_current_time** with **advance=True** so the time is taken for this turn and stays in sync with the UI.
