# Dynamic Schema Qualification

This document explains how SQL files use `__SCHEMA_QUALIFIED__` and `__VOLUME_PATH__` placeholders, resolved at runtime from `UNITY_CATALOG_SCHEMA` in `.env.local`.

---

## How It Works

1. **Source of truth:** `UNITY_CATALOG_SCHEMA` in `.env.local` (format: `catalog.schema`)
2. **Placeholders:** `__SCHEMA_QUALIFIED__` and `__VOLUME_PATH__` in SQL files
3. **Substitution:** `data/sql_utils.py` converts `catalog.schema` → `` `catalog`.`schema` ``
4. **Execution:** Scripts that run SQL call `substitute_schema()` before sending to Databricks

---

## Placeholders

| Placeholder | Replaced with | Example |
|-------------|---------------|---------|
| `__SCHEMA_QUALIFIED__` | `` `catalog`.`schema` `` | `` `mc`.`template` `` |
| `__VOLUME_PATH__` | `/Volumes/catalog/schema` | `/Volumes/mc/template` |

---

## Configuration

**`.env.local`**

```bash
UNITY_CATALOG_SCHEMA=mc.template
```

---

## Files Using Placeholders

- **`data/init/create_example_data.sql`** — CREATE TABLE, INSERT
- **`data/func/example_query.sql`** — SELECT FROM

---

## Code That Implements Dynamic Schema

- **`data/sql_utils.py`** — `substitute_schema()`, `get_schema_qualified()`
- **`data/run_sql.py`** — runs SQL with substitution
- **`data/init/create_catalog_schema.py`** — creates catalog/schema from env
- **`scripts/reset_state.py`** — uses `substitute_schema()` for init SQL
