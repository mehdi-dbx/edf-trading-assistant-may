#!/usr/bin/env python3
"""Verify Delta tables in AMADEUS_UNITY_CATALOG_SCHEMA: flights and turnaround_events exist, CDF enabled on turnaround_events.
Uses Databricks SDK (same auth as CLI). Run from repo root: python3 data/verify_tables.py
"""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)

from dotenv import load_dotenv
load_dotenv(ROOT / ".env.local", override=True)


def main() -> int:
    spec = os.environ.get("AMADEUS_UNITY_CATALOG_SCHEMA") or ""
    if "." not in spec:
        print("FAIL: Set AMADEUS_UNITY_CATALOG_SCHEMA to catalog.schema", file=sys.stderr)
        return 1
    catalog, schema = spec.strip().split(".", 1)

    from databricks.sdk import WorkspaceClient
    w = WorkspaceClient()

    required_tables = ["flights", "turnaround_events"]
    cdf_table = "turnaround_events"
    ok = True

    for name in required_tables:
        full_name = f"{catalog}.{schema}.{name}"
        try:
            t = w.tables.get(full_name)
            print(f"OK table exists: {full_name}")
        except Exception as e:
            print(f"FAIL table missing: {full_name} — {e}", file=sys.stderr)
            ok = False
            continue

        # Check CDF for turnaround_events
        if name == cdf_table:
            props = getattr(t, "properties", None) or {}
            cdf = props.get("delta.enableChangeDataFeed", "false").lower() in ("true", "1")
            if cdf:
                print(f"OK CDF enabled: {full_name}")
            else:
                print(f"FAIL CDF not enabled: {full_name} (delta.enableChangeDataFeed not true)", file=sys.stderr)
                ok = False

    if not ok:
        return 1
    print("Verify done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
