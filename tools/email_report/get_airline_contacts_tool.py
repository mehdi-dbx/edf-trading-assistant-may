"""LangGraph @tool: load airline contacts from Unity Catalog table airline_contacts."""

import json
import logging
import os
import time

from databricks.sdk import WorkspaceClient
from databricks.sdk.service.sql import ExecuteStatementRequestOnWaitTimeout
from langchain_core.tools import tool


def _get_warehouse_id(w: WorkspaceClient) -> str:
    wh_id = os.environ.get("DATABRICKS_WAREHOUSE_ID", "").strip()
    if wh_id:
        return wh_id
    first = next(iter(w.warehouses.list()), None)
    if not first:
        raise RuntimeError("No warehouse. Set DATABRICKS_WAREHOUSE_ID or create one.")
    return getattr(first, "id", first)


def _execute_and_wait(w: WorkspaceClient, warehouse_id: str, statement: str):
    """Execute SQL and wait for completion; return StatementResponse with result."""
    resp = w.statement_execution.execute_statement(
        warehouse_id=warehouse_id,
        statement=statement,
        wait_timeout="50s",
        on_wait_timeout=ExecuteStatementRequestOnWaitTimeout.CONTINUE,
    )
    state = (resp.status and resp.status.state) and resp.status.state.value or ""
    if state in ("SUCCEEDED", "CLOSED"):
        return resp
    if state in ("FAILED", "CANCELED"):
        err = resp.status.error if resp.status else None
        msg = err.message if err else state
        raise RuntimeError(f"Statement {state}: {msg}")
    if state in ("PENDING", "RUNNING") and resp.statement_id:
        while True:
            time.sleep(2)
            poll = w.statement_execution.get_statement(resp.statement_id)
            s = (poll.status and poll.status.state) and poll.status.state.value or ""
            if s in ("SUCCEEDED", "CLOSED"):
                return poll
            if s in ("FAILED", "CANCELED"):
                err = poll.status.error if poll.status else None
                raise RuntimeError(f"Statement {s}: {err.message if err else s}")
    raise RuntimeError(f"Statement did not complete: {state}")


@tool
def get_airline_contacts_tool(input: str = "") -> str:
    """Load the list of airline contacts from the system.

    Call with no input or empty input to fetch all contacts. Returns a JSON array of
    objects: { "airline": str, "contact_name": str, "to_email": str } for each row.
    Use this result together with your list of airlines (and their pdf_path, period_label)
    to match each contact to an airline by name, then build the email_recipients list
    for the send-report checklist.
    """
    w = WorkspaceClient()
    warehouse_id = _get_warehouse_id(w)
    
    catalog, schema = os.environ["AMADEUS_UNITY_CATALOG_SCHEMA"].strip().split(".", 1)
    table = "airline_contacts"
    
    stmt = f'SELECT Airline, Contact_Person_Name, Email_Id FROM `{catalog}`.`{schema}`.`{table}`'
    resp = _execute_and_wait(w, warehouse_id, stmt)

    logging.warning(
        "get_airline_contacts chunking: total_chunk_count=%s, manifest.chunks=%s (len=%s), result.next_chunk_index=%s",
        getattr(resp.manifest, "total_chunk_count", None),
        [getattr(c, "chunk_index", None) for c in (resp.manifest.chunks or [])],
        len(resp.manifest.chunks or []),
        getattr(resp.result, "next_chunk_index", None),
    )

    all_arrays = list(resp.result.data_array or [])
    n_chunks = resp.manifest.total_chunk_count
    if n_chunks and n_chunks > 1:
        for i in range(1, n_chunks):
            chunk = w.statement_execution.get_statement_result_chunk_n(resp.statement_id, i)
            all_arrays.extend(chunk.data_array or [])
    else:
        next_index = getattr(resp.result, "next_chunk_index", None)
        while next_index is not None:
            chunk = w.statement_execution.get_statement_result_chunk_n(resp.statement_id, next_index)
            all_arrays.extend(chunk.data_array or [])
            next_index = getattr(chunk, "next_chunk_index", None)

    rows = []
    for arr in all_arrays:
        a, b, c = (v or "" for v in (list(arr) + [""] * 3)[:3])
        rows.append({"airline": a, "contact_name": b, "to_email": c})

    return json.dumps(rows)
