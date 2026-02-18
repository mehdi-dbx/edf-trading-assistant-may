#!/usr/bin/env python3
"""Upload data/*.csv to Delta tables in AMADEUS_UNITY_CATALOG_SCHEMA. Creates volume 'data' if missing."""
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)
load_dotenv(ROOT / ".env", override=True)
load_dotenv(ROOT / ".env.local", override=True)

def main():
    from databricks.sdk import WorkspaceClient
    from databricks.sdk.service.catalog import VolumeType

    w = WorkspaceClient()
    spec = os.environ.get("AMADEUS_UNITY_CATALOG_SCHEMA") or ""
    if "." not in spec:
        print("Set AMADEUS_UNITY_CATALOG_SCHEMA to catalog.schema", file=sys.stderr)
        sys.exit(1)
    catalog, schema = spec.strip().split(".", 1)

    vol_name = "data"
    try:
        w.volumes.create(catalog_name=catalog, schema_name=schema, name=vol_name, volume_type=VolumeType.MANAGED)
    except Exception as e:
        if "already exists" not in str(e).lower() and "RESOURCE_ALREADY_EXISTS" not in str(e):
            raise

    wh_id = os.environ.get("DATABRICKS_WAREHOUSE_ID") or next(iter(w.warehouses.list()), None)
    if not wh_id:
        print("No warehouse. Set DATABRICKS_WAREHOUSE_ID or create one.", file=sys.stderr)
        sys.exit(1)
    wh_id = getattr(wh_id, "id", wh_id)
    vol = f"/Volumes/{catalog}/{schema}/{vol_name}"

    data_dir = Path(__file__).resolve().parent
    if len(sys.argv) > 1:
        csv_path = Path(sys.argv[1])
        if not csv_path.is_absolute():
            csv_path = (data_dir / csv_path).resolve()
        if not csv_path.exists():
            print(f"File not found: {csv_path}", file=sys.stderr)
            sys.exit(1)
        if csv_path.suffix.lower() != ".csv":
            print("Expected a .csv file.", file=sys.stderr)
            sys.exit(1)
        csv_files = [csv_path]
    else:
        csv_files = sorted(data_dir.glob("*.csv"))

    for csv in csv_files:
        rpath = f"{vol}/{csv.name}"
        w.files.upload_from(file_path=rpath, source_path=str(csv), overwrite=True)
        t = f"`{catalog}`.`{schema}`.`{csv.stem.replace('-', '_')}`"
        w.statement_execution.execute_statement(warehouse_id=wh_id, statement=f"CREATE OR REPLACE TABLE {t} AS SELECT * FROM read_files('{rpath}', header => true)")
    print("Done.")

if __name__ == "__main__":
    main()
