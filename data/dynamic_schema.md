# Dynamic Schema Qualification: Migration from Hardcoded to Environment-Driven

This document explains the migration from hardcoded catalog/schema names in SQL to dynamic qualification via `__SCHEMA_QUALIFIED__`, and lists all code that makes it work.

---

## 1. Before vs After

### Before (hardcoded)

```sql
DROP TABLE IF EXISTS mc.`amadeus-checkin`.border_officers;

CREATE TABLE mc.`amadeus-checkin`.border_officers (
  ...
);
```

- Catalog and schema were **baked into the SQL**
- Changing workspace or schema required editing every SQL file
- Different workspaces had different paths; copying SQL meant manual find/replace

### After (dynamic)

```sql
CREATE OR REPLACE TABLE __SCHEMA_QUALIFIED__.border_officers (
  ...
);
```

- `__SCHEMA_QUALIFIED__` is a **placeholder** replaced at runtime
- Catalog and schema come from `AMADEUS_UNITY_CATALOG_SCHEMA` in `.env.local` (e.g. `amadeus.checkin` or `mc.amadeus-checkin`)
- Substitution produces `` `amadeus`.`checkin` `` (backtick-quoted for SQL)
- Same SQL files work across workspaces; only `.env.local` changes

---

## 2. How It Works

1. **Source of truth:** `AMADEUS_UNITY_CATALOG_SCHEMA` in `.env.local` (format: `catalog.schema`)
2. **Placeholder:** `__SCHEMA_QUALIFIED__` in SQL files
3. **Substitution:** `data/sql_utils.py` converts `catalog.schema` → `` `catalog`.`schema` ``
4. **Execution:** Any script that runs SQL calls `substitute_schema()` before sending to Databricks

---

## 3. Placeholders

| Placeholder | Replaced with | Example |
|-------------|---------------|---------|
| `__SCHEMA_QUALIFIED__` | `` `catalog`.`schema` `` | `` `amadeus`.`checkin` `` |
| `__VOLUME_PATH__` | `/Volumes/catalog/schema` | `/Volumes/amadeus/checkin` |
| `__CHECKIN_SCHEMA_QUALIFIED__` | Checkin schema (for cross-project) | `` `mc`.`amadeus-checkin` `` (fallback if `AMADEUS_CHECKIN_SCHEMA` unset) |

---

## 4. All Code That Implements Dynamic Schema

### 4.1 Core substitution logic

**`data/sql_utils.py`**

- `substitute_schema(content)` — replaces `__SCHEMA_QUALIFIED__`, `__VOLUME_PATH__`, `__CHECKIN_SCHEMA_QUALIFIED__`
- `get_schema_qualified()` — returns SQL-qualified schema for use in Python f-strings (e.g. `CALL {schema}.update_flight_risk(...)`)
- `get_checkin_schema_qualified()` — for cross-project references

### 4.2 SQL execution with substitution

**`data/run_sql.py`**

- Loads `.env.local`
- Reads SQL file
- Calls `substitute_schema(path.read_text())` before executing
- Used by `create_all_assets.py` for all `data/init/*.sql` and `data/proc/*.sql`

### 4.3 Catalog and schema creation

**`data/init/create_catalog_schema.py`**

- Reads `AMADEUS_UNITY_CATALOG_SCHEMA` from `.env.local`
- Parses `catalog.schema`
- Runs `CREATE CATALOG IF NOT EXISTS`, `CREATE SCHEMA IF NOT EXISTS`

### 4.4 Agent tools (procedure calls and SQL)

| File | Usage |
|------|-------|
| `tools/update_flight_risk.py` | `schema = get_schema_qualified()` → `CALL {schema}.update_flight_risk(...)` |
| `tools/update_checkin_agent.py` | `schema = get_schema_qualified()` → `CALL {schema}.update_checkin_agent(...)` |
| `tools/confirm_arrival.py` | `schema = get_schema_qualified()` → `CALL {schema}.confirm_arrival(...)` |
| `tools/update_border_officer.py` | `schema = get_schema_qualified()` → `CALL {schema}.update_border_officer(...)` |
| `tools/back_to_normal.py` | `schema = get_schema_qualified()` → `INSERT INTO {schema}.checkin_metrics ...` |
| `tools/create_checkin_incident.py` | `schema = get_schema_qualified()` → DELETE/INSERT on `{schema}.checkin_metrics` |
| `tools/create_border_incident.py` | `schema = get_schema_qualified()` → DELETE/INSERT on `{schema}.checkin_metrics` |

### 4.5 Agent tools (query from func SQL)

| File | Usage |
|------|-------|
| `tools/query_flights_at_risk.py` | `sql = substitute_schema((_FUNC_DIR / "flights_at_risk.sql").read_text())` |
| `tools/query_staffing_duties.py` | Same pattern |
| `tools/query_border_officer_staffing.py` | Same pattern |
| `tools/query_border_officers_by_post.py` | Same pattern |
| `tools/query_egate_availability.py` | Same pattern |
| `tools/query_checkin_performance_metrics.py` | Same pattern |
| `tools/query_checkin_agents_by_counter_status.py` | Same pattern |
| `tools/query_border_terminal_details.py` | Same pattern |
| `tools/query_checkin_agent_staffing.py` | Same pattern |
| `tools/query_available_agents_for_redeployment.py` | Same pattern |

### 4.6 Scripts

| File | Usage |
|------|-------|
| `scripts/reset_state.py` | `content = substitute_schema(path.read_text())` for init and procedure SQL |

### 4.7 Other data scripts

| File | Usage |
|------|-------|
| `data/init/create_genie_space.py` | Uses `AMADEUS_UNITY_CATALOG_SCHEMA` for table discovery |
| `data/init/create_all_assets.py` | Uses `AMADEUS_UNITY_CATALOG_SCHEMA` for verification |

### 4.8 Deploy and init

| File | Usage |
|------|-------|
| `deploy/grant/grant_app_tables.py` | `AMADEUS_UNITY_CATALOG_SCHEMA` for schema (default `mc.amadeus-checkin`) |
| `deploy/grant/grant_app_functions.py` | Same |
| `scripts/init_check_dbx_env.py` | Interactive setup and verification of `AMADEUS_UNITY_CATALOG_SCHEMA` |

---

## 5. SQL Files Using `__SCHEMA_QUALIFIED__`

### Init (tables)

| File | Placeholder usage |
|------|-------------------|
| `data/init/create_checkin_metrics.sql` | DROP, CREATE, INSERT |
| `data/init/create_flights.sql` | DROP, CREATE, INSERT |
| `data/init/create_checkin_agents.sql` | DROP, CREATE, INSERT |
| `data/init/create_border_officers.sql` | DROP, CREATE, INSERT |
| `data/init/create_border_terminals.sql` | DROP, CREATE, INSERT |

### Procedures

| File | Placeholder usage |
|------|-------------------|
| `data/proc/confirm_arrival_procedure.sql` | CREATE PROCEDURE, UPDATE |
| `data/proc/update_checkin_agents_procedure.sql` | CREATE PROCEDURE, UPDATE |
| `data/proc/update_border_officer_procedure.sql` | CREATE PROCEDURE, UPDATE |
| `data/proc/update_flight_risk_procedure.sql` | CREATE PROCEDURE, UPDATE |

### Func (query templates)

| File | Placeholder usage |
|------|-------------------|
| `data/func/flights_at_risk.sql` | SELECT FROM |
| `data/func/checkin_performance_metrics.sql` | SELECT FROM |
| `data/func/border_officers_by_post.sql` | SELECT FROM |
| `data/func/border_terminal_details.sql` | SELECT FROM |
| `data/func/available_agents_for_redeployment.sql` | SELECT FROM |
| `data/func/checkin_agent_staffing.sql` | SELECT FROM |
| `data/func/border_officer_staffing.sql` | SELECT FROM |
| `data/func/checkin_agents_by_counter_status.sql` | SELECT FROM |
| `data/func/egate_availability.sql` | SELECT FROM |
| `data/func/staffing_duties.sql` | SELECT FROM |

### Genie capture

| File | Placeholder usage |
|------|-------------------|
| All 9 files in `data/genie-capture-sql/` | SELECT FROM (for Genie capture) |

---

## 6. Configuration

**`.env.local`**

```bash
AMADEUS_UNITY_CATALOG_SCHEMA=amadeus.checkin
```

Or:

```bash
AMADEUS_UNITY_CATALOG_SCHEMA=mc.amadeus-checkin
```

Optional (for cross-project references):

```bash
AMADEUS_CHECKIN_SCHEMA=mc.amadeus-checkin   # used by __CHECKIN_SCHEMA_QUALIFIED__
```

**`app.yaml`** (deployed app)

```yaml
- name: AMADEUS_UNITY_CATALOG_SCHEMA
  value: "amadeus.checkin"
```

---

## 7. Execution Flow

```
.env.local (AMADEUS_UNITY_CATALOG_SCHEMA=amadeus.checkin)
       │
       ▼
data/sql_utils.substitute_schema(content)
       │
       ├── __SCHEMA_QUALIFIED__  →  `amadeus`.`checkin`
       ├── __VOLUME_PATH__       →  /Volumes/amadeus/checkin
       └── __CHECKIN_SCHEMA_QUALIFIED__  →  (from AMADEUS_CHECKIN_SCHEMA or fallback)
       │
       ▼
SQL sent to Databricks (e.g. CREATE OR REPLACE TABLE `amadeus`.`checkin`.border_officers ...)
```

---

## 8. Summary: Files to Replicate

To replicate this pattern in another project:

1. **`data/sql_utils.py`** — substitution logic and `get_schema_qualified()`
2. **`data/run_sql.py`** — run SQL with substitution
3. **`data/init/create_catalog_schema.py`** — create catalog/schema from env
4. **`.env.local`** — set `AMADEUS_UNITY_CATALOG_SCHEMA=catalog.schema`
5. **SQL files** — use `__SCHEMA_QUALIFIED__` instead of hardcoded paths
6. **Tools/scripts** — call `substitute_schema()` or `get_schema_qualified()` before executing SQL
