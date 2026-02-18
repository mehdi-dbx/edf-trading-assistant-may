#!/usr/bin/env python3
"""Upload local PNG logos to Unity Catalog Volume: /Volumes/{catalog}/{schema}/reports/logos/[airline_name]_logo.png.

Usage:
  uv run python data/upload_img_to_volume.py
      Upload all data/img/*.png to .../reports/logos/{stem}_logo.png (e.g. air_france.png -> air_france_logo.png).

  uv run python data/upload_img_to_volume.py [source]
      Upload a single file; destination is .../reports/logos/{stem}_logo.png.

  uv run python data/upload_img_to_volume.py [source] [destination]
      Upload source to the given Volume path (overrides default naming).

Uses AMADEUS_UNITY_CATALOG_SCHEMA for catalog.schema.
"""
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)
load_dotenv(ROOT / ".env", override=True)
load_dotenv(ROOT / ".env.local", override=True)


def main() -> None:
    from databricks.sdk import WorkspaceClient
    from databricks.sdk.service.catalog import VolumeType

    data_dir = Path(__file__).resolve().parent
    img_dir = data_dir / "img"

    w = WorkspaceClient()
    spec = os.environ.get("AMADEUS_UNITY_CATALOG_SCHEMA", "").strip()
    if "." not in spec:
        print("Set AMADEUS_UNITY_CATALOG_SCHEMA to catalog.schema", file=sys.stderr)
        sys.exit(1)
    catalog, schema = spec.split(".", 1)
    base = f"/Volumes/{catalog}/{schema}/reports/logos"

    # Resolve source file(s)
    if len(sys.argv) >= 2:
        source = Path(sys.argv[1])
        if not source.is_absolute():
            source = (data_dir / source).resolve()
        if not source.exists():
            print(f"File not found: {source}", file=sys.stderr)
            sys.exit(1)
        if source.suffix.lower() != ".png":
            print("Expected a .png file.", file=sys.stderr)
            sys.exit(1)
        sources = [source]
    else:
        sources = sorted(img_dir.glob("*.png"))
        if not sources:
            print(f"No PNG files in {img_dir}", file=sys.stderr)
            sys.exit(1)

    # Create volume if missing
    try:
        w.volumes.create(catalog_name=catalog, schema_name=schema, name="reports", volume_type=VolumeType.MANAGED)
    except Exception as e:
        if "already exists" not in str(e).lower() and "RESOURCE_ALREADY_EXISTS" not in str(e):
            raise

    for source in sources:
        if len(sys.argv) >= 3 and len(sources) == 1:
            dest = sys.argv[2]
        else:
            dest = f"{base}/{source.stem}_logo.png"
        if not dest.startswith("/Volumes/"):
            print(f"Destination must be a Volume path: {dest}", file=sys.stderr)
            sys.exit(1)
        w.files.upload_from(file_path=dest, source_path=str(source), overwrite=True)
        print(f"Uploaded {source.name} -> {dest}")


if __name__ == "__main__":
    main()
