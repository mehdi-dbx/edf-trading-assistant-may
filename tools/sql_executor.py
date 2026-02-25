"""Shared Databricks SQL execution for agent tools."""

import os
import time

from databricks.sdk import WorkspaceClient
from databricks.sdk.service.sql import ExecuteStatementRequestOnWaitTimeout


def get_warehouse() -> tuple[WorkspaceClient, str]:
    """Return (WorkspaceClient, warehouse_id) for SQL execution."""
    w = WorkspaceClient()
    wh = os.environ.get("DATABRICKS_WAREHOUSE_ID") or next(iter(w.warehouses.list()))
    wh_id = str(getattr(wh, "id", wh) or wh)
    return w, wh_id


def execute_statement(w: WorkspaceClient, wh_id: str, stmt: str) -> None:
    """Run SQL via statement_execution, poll until done, raise on failure."""
    resp = w.statement_execution.execute_statement(
        warehouse_id=wh_id,
        statement=stmt,
        wait_timeout="30s",
        on_wait_timeout=ExecuteStatementRequestOnWaitTimeout.CONTINUE,
    )
    state = (resp.status and resp.status.state) and resp.status.state.value or ""
    if state in ("SUCCEEDED", "CLOSED"):
        return
    if state in ("FAILED", "CANCELED"):
        err = resp.status.error if resp.status else None
        raise RuntimeError(err.message if err else state)
    if state in ("PENDING", "RUNNING") and resp.statement_id:
        while True:
            time.sleep(2)
            poll = w.statement_execution.get_statement(resp.statement_id)
            s = (poll.status and poll.status.state) and poll.status.state.value or ""
            if s in ("SUCCEEDED", "CLOSED"):
                return
            if s in ("FAILED", "CANCELED"):
                err = poll.status.error if poll.status else None
                raise RuntimeError(err.message if err else s)
    raise RuntimeError(f"Statement did not complete: {state}")
