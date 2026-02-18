#!/usr/bin/env python3
"""Upload a local image to a Unity Catalog Volume path via CLI.

Usage:
  uv run python data/upload_img_to_volume.py [source] [destination]

  source      Local image path (default: data/img/air_france_logo.png)
  destination Volume path (default: /Volumes/<catalog>/<schema>/reports/logos/default/logo.png)
               Uses AMADEUS_UNITY_CATALOG_SCHEMA for catalog.schema.

  Or set VOLUME_LOGO_PATH to the full destination path (overrides default destination).
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
    default_src = data_dir / "img" / "air_france_logo.png"

    source = Path(sys.argv[1]) if len(sys.argv) > 1 else default_src
    if not source.is_absolute():
        source = (data_dir / source).resolve()
    if not source.exists():
        print(f"File not found: {source}", file=sys.stderr)
        sys.exit(1)

    w = WorkspaceClient()
    spec = os.environ.get("AMADEUS_UNITY_CATALOG_SCHEMA", "").strip()
    if "." not in spec:
        print("Set AMADEUS_UNITY_CATALOG_SCHEMA to catalog.schema", file=sys.stderr)
        sys.exit(1)
    catalog, schema = spec.split(".", 1)

    dest = os.environ.get("VOLUME_LOGO_PATH", "").strip()
    if not dest and len(sys.argv) > 2:
        dest = sys.argv[2]
    if not dest:
        dest = f"/Volumes/{catalog}/{schema}/reports/logos/default_logo.png"

    if not dest.startswith("/Volumes/"):
        print("Destination must be a Volume path: /Volumes/<catalog>/<schema>/<volume>/...", file=sys.stderr)
        sys.exit(1)

    # Create volume if missing (e.g. reports)
    parts = dest.removeprefix("/Volumes/").split("/")
    if len(parts) >= 3:
        vol_name = parts[2]
        try:
            w.volumes.create(catalog_name=catalog, schema_name=schema, name=vol_name, volume_type=VolumeType.MANAGED)
        except Exception as e:
            if "already exists" not in str(e).lower() and "RESOURCE_ALREADY_EXISTS" not in str(e):
                raise

    w.files.upload_from(file_path=dest, source_path=str(source), overwrite=True)
    print(f"Uploaded {source} -> {dest}")


if __name__ == "__main__":
    main()
