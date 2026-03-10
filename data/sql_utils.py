"""Shared SQL utilities. Substitutes __SCHEMA_QUALIFIED__ and __VOLUME_PATH__ from AMADEUS_UNITY_CATALOG_SCHEMA."""
import os


def _schema_to_qualified(spec: str) -> str:
    """Convert catalog.schema to `catalog`.`schema`."""
    if not spec or "." not in spec:
        return ""
    catalog, schema = spec.strip().split(".", 1)
    return f"`{catalog}`.`{schema}`"


def get_schema_qualified() -> str:
    """Return SQL-qualified schema from AMADEUS_UNITY_CATALOG_SCHEMA (for use in Python f-strings)."""
    spec = os.environ.get("AMADEUS_UNITY_CATALOG_SCHEMA", "").strip()
    return _schema_to_qualified(spec) or "`mc`.`amadeus-checkin`"


def get_checkin_schema_qualified() -> str:
    """Return SQL-qualified checkin schema (AMADEUS_CHECKIN_SCHEMA or AMADEUS_UNITY_CATALOG_SCHEMA)."""
    spec = os.environ.get("AMADEUS_CHECKIN_SCHEMA", "").strip()
    if not spec:
        spec = os.environ.get("AMADEUS_UNITY_CATALOG_SCHEMA", "").strip()
    return _schema_to_qualified(spec) or "`mc`.`amadeus-checkin`"


def substitute_schema(content: str) -> str:
    """Replace placeholders with values from AMADEUS_UNITY_CATALOG_SCHEMA."""
    spec = os.environ.get("AMADEUS_UNITY_CATALOG_SCHEMA", "").strip()
    if "." not in spec:
        return content
    catalog, schema = spec.split(".", 1)
    schema_qualified = f"`{catalog}`.`{schema}`"
    volume_path = f"/Volumes/{catalog}/{schema}"
    checkin = get_checkin_schema_qualified()
    return (
        content.replace("__SCHEMA_QUALIFIED__", schema_qualified)
        .replace("__VOLUME_PATH__", volume_path)
        .replace("__CHECKIN_SCHEMA_QUALIFIED__", checkin)
    )
