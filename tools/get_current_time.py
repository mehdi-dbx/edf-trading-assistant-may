"""Simulated current time for turnaround scenario. Returns next time in queue on each call."""

import threading
from langchain_core.tools import tool

_TIME_QUEUE = [
    "2025-02-20T13:50:00.000-05:00",
    "2025-02-20T13:55:00.000-05:00",
    "2025-02-20T14:00:00.000-05:00",
    "2025-02-20T14:05:00.000-05:00",
    "2025-02-20T14:10:00.000-05:00",
    "2025-02-20T14:15:00.000-05:00",
    "2025-02-20T14:16:00.000-05:00",
    "2025-02-20T14:20:00.000-05:00",
]
_index = 0
_lock = threading.Lock()


def get_next_time() -> str:
    """Advance the queue and return the raw timestamp (e.g. for HTTP API)."""
    global _index
    with _lock:
        t = _TIME_QUEUE[_index % len(_TIME_QUEUE)]
        _index += 1
    return t


@tool
def get_current_time() -> str:
    """Get the simulated current time for the turnaround scenario. Call this to update context with the next time in the queue. Use this time when querying Genie for turnaround checklist/status (as of current time)."""
    return f"Current time: {get_next_time()}"
