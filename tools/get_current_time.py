"""Simulated current time for turnaround scenario. Returns next time in queue on each call."""

import threading
from langchain_core.tools import tool

_TIME_QUEUE = [
    "2025-02-20T13:50:00.000",
    "2025-02-20T13:55:00.000",
    "2025-02-20T14:00:00.000",
    "2025-02-20T14:05:00.000",
    "2025-02-20T14:10:00.000",
    "2025-02-20T14:15:00.000",
    "2025-02-20T14:16:00.000",
    "2025-02-20T14:20:00.000",
]
_index = 0
_lock = threading.Lock()


def get_next_time(advance: bool = True) -> str:
    """Return the current simulated time. If advance is True, move the queue forward first then return the new time (so widget/agent see the next time). If False, peek without advancing."""
    global _index
    with _lock:
        if advance:
            _index += 1
        t = _TIME_QUEUE[_index % len(_TIME_QUEUE)]
    return t


@tool
def get_current_time(advance: bool = False) -> str:
    """Get the simulated current time for the turnaround scenario. Pass advance=True when you need the time for this turn (e.g. before querying Genie for checklist); then use that time in your Genie query. Use advance=False only to peek (default)."""
    return f"Current time: {get_next_time(advance)}"
