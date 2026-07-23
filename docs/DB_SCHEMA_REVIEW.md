# QuantumPACS Database Schema Review

**Review date:** 2026-07-23
**Scope:** All tables defined in `001_initial_schema.py` and `sync_db()` methods
**Reference:** PostgreSQL Table Design best practices

---

## Table of Contents

1. [Data Type Assessment](#1-data-type-assessment)
2. [Indexing Audit](#2-indexing-audit)
3. [Constraint Review](#3-constraint-review)
4. [Schema Design Patterns](#4-schema-design-patterns)
5. [Recommendations](#5-recommendations)

---

## 1. Data Type Assessment

### 1.1 `SERIAL` instead of `GENERATED ALWAYS AS IDENTITY`

**Severity: MEDIUM**

All 9 tables use `SERIAL` for primary keys:

| Table | Current | Recommended |
|-------|---------|-------------|
| users | `id SERIAL PRIMARY KEY` | `id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY` |
| patients | `id SERIAL PRIMARY KEY` | same |
| studies | `id SERIAL PRIMARY KEY` | same |
| series | `id SERIAL PRIMARY KEY` | same |
| files | `id SERIAL PRIMARY KEY` | same |
| file_changes | `id SERIAL PRIMARY KEY` | same |
| replicas | `id SERIAL PRIMARY KEY` | same |
| replica_files | `id SERIAL` (no PK!) | `id BIGINT GENERATED ALWAYS AS IDENTITY` |
| logs | `id SERIAL PRIMARY KEY` | same |
| shared_files | `id SERIAL PRIMARY KEY` | same |

`SERIAL` is a legacy shorthand that creates a plain `INTEGER` column + sequence + default. `GENERATED ALWAYS AS IDENTITY` (SQL standard) prevents manual override, preserves the sequence on `COPY`, and is visible in `information_schema`.

**Note:** `SERIAL` creates `INTEGER` (32-bit, max ~2B). For a production PACS with many files, `BIGINT` is safer.

### 1.2 `TIMESTAMP` instead of `TIMESTAMPTZ`

**Severity: HIGH**

All 6 timestamp columns use `TIMESTAMP` with `DEFAULT (now() at time zone 'utc')`:

| Column | Current | Recommended |
|--------|---------|-------------|
| users.created | `TIMESTAMP ... DEFAULT (now() at time zone 'utc')` | `TIMESTAMPTZ ... DEFAULT now()` |
| users.updated | same | same |
| files.created | same | same |
| files.updated | same | same |
| file_changes.created | same | same |
| replicas.created | *(none)* | — |
| replica_files.created | same | same |
| replica_files.updated | same | same |
| logs.created | same | same |
| shared_files.created | same | same |
| shared_files.expires | `TIMESTAMP NOT NULL` (no default) | `TIMESTAMPTZ NOT NULL` |

`TIMESTAMP WITHOUT TIME ZONE` discards timezone metadata. Although the default expression converts `now()` to UTC at insert time, clients have no way to know the stored values represent UTC. `TIMESTAMPTZ`:
- Stores values normalized to UTC internally
- Outputs in the client's session timezone automatically
- Eliminates the `AT TIME ZONE 'utc'` dance
- Makes `shared_files.expires` comparisons timezone-safe

### 1.3 String columns

**Severity: LOW**

Strings use `TEXT` throughout — correct per best practices. No `VARCHAR(n)` or `CHAR(n)` found.

### 1.4 Boolean columns

**Severity: INFO**

All booleans are properly constrained with `NOT NULL DEFAULT`:
- `users.admin BOOLEAN NOT NULL DEFAULT FALSE` ✓
- `files.indexed BOOLEAN NOT NULL DEFAULT FALSE` ✓
- `files.deleted BOOLEAN NOT NULL DEFAULT FALSE` ✓
- `replicas.master BOOLEAN NOT NULL DEFAULT FALSE` ✓

No issues.

### 1.5 `JSONB` usage

**Severity: INFO**

Six `JSONB` columns: `patients.meta`, `files.meta`, `files.tools_state`, `replicas.meta`, `replica_files.meta`, `shared_files.(none)`.

`JSONB` is the correct choice over `JSON`. No GIN indexes defined (see [Indexing Audit](#2-indexing-audit)).

### 1.6 `replica_files.id` — missing PRIMARY KEY

**Severity: CRITICAL**

```sql
CREATE TABLE IF NOT EXISTS replica_files (
    id SERIAL,                          -- no PRIMARY KEY
    replica_id INTEGER NOT NULL REFERENCES replicas(id),
    file_id INTEGER NOT NULL REFERENCES files(id),
    ...
    UNIQUE (replica_id, file_id)
);
```

The `id SERIAL` column has **no PRIMARY KEY constraint**. Without a PK:
- Orphaned `id` values (nulls, duplicates) are allowed
- Some ORMs, replication tools, and migration tools assume a PK exists
- Logical replication may refuse to replicate the table

The `UNIQUE (replica_id, file_id)` constraint creates a unique B-tree index but does **not** designate a primary key.

---

## 2. Indexing Audit

### 2.1 Existing indexes

| Index | Table | Type | Assessment |
|-------|-------|------|------------|
| `users_username` | users | B-tree | ✓ needed for login lookups |
| `patients_patient_id` | patients | B-tree | **REDUNDANT** — `patient_id` has a `UNIQUE` constraint which already creates a B-tree index |
| `studies_study_id` | studies | B-tree | ✓ needed for lookups by DICOM StudyUID |
| `series_number` | series | B-tree | ✓ needed for lookups by SeriesNumber |
| `files_name` | files | B-tree | ✓ |
| `files_hash` | files | B-tree | ✓ needed for dedup |
| `file_changes_file_id` | file_changes | B-tree | ✓ FK index |
| `replicas_master_unique` | replicas | Partial UNIQUE | ✓ correctly limits to one master |
| `replica_files_replica_id` | replica_files | B-tree | ✓ FK index |
| `shared_files_hash` | shared_files | B-tree | ✓ needed for share-link lookups |

### 2.2 Missing FK indexes

PostgreSQL does **not** automatically index foreign key columns. Missing FK indexes cause slow joins and, more critically, **row-level locks on the referencing table during parent table updates/deletes**.

| Missing FK Index | Why needed |
|-----------------|------------|
| `studies(patient_id)` | Referenced by `patients` deletes |
| `series(study_id)` | Referenced by `studies` deletes |
| `files(patient_id)` | Referenced by `patients` deletes |
| `files(study_id)` | Referenced by `studies` deletes |
| `files(series_id)` | Referenced by `series` deletes |
| `file_changes(by_user_id)` | Referenced by `users` deletes |
| `file_changes(file_id)` | Already indexed (`file_changes_file_id`) ✓ |
| `replica_files(file_id)` | Referenced by `files` deletes |
| `shared_files(file_id)` | Referenced by `files` deletes |

**Severity: HIGH** — 8 missing FK indexes.

### 2.3 Missing composite indexes

| Missing Index | Query Pattern |
|--------------|---------------|
| `files(study_id, series_id)` | `Patient.get_extra()` fetches files `WHERE study_id IN (...)` then groups by series_id |
| `files(study_id) WHERE deleted = FALSE` | Most file listings filter out soft-deleted files |
| `replica_files(replica_id, status)` | `ReplicaFiles.get_for_sync()` filters by `replica_id` AND `status IN (0, 9)` |
| `replica_files(replica_id, status, updated)` | Same query also sorts by `updated` / filters on `location = ''` |

**Severity: MEDIUM**

### 2.4 Missing partial indexes

| Missing Partial Index | Benefit |
|----------------------|---------|
| `files(deleted) WHERE deleted = FALSE` | Soft-delete filter on most queries; dramatically smaller index |
| `replica_files(status) WHERE status != 1` | Most rows have `status = 1` (ok); sync queries only touch non-ok rows |

**Severity: LOW** — optimization opportunity.

### 2.5 Missing GIN indexes on JSONB columns

Six `JSONB` columns exist. None have GIN indexes. If any query uses JSONB operators (`@>`, `?`, `?|`, `?&`), these will be sequential scans.

| Missing GIN Index | Column |
|-------------------|--------|
| `patients_meta_gin ON patients USING GIN (meta)` | patients.meta |
| `files_meta_gin ON files USING GIN (meta)` | files.meta |
| `files_tools_state_gin ON files USING GIN (tools_state)` | files.tools_state |

**Severity: LOW** — add only if queries actually use JSONB operators.

---

## 3. Constraint Review

### 3.1 Foreign Key `ON DELETE` actions

| FK | Defined Action | Recommended Action | Rationale |
|----|---------------|-------------------|-----------|
| `studies.patient_id → patients.id` | none (NO ACTION) | `ON DELETE CASCADE` | Deleting a patient should remove their studies |
| `series.study_id → studies.id` | none (NO ACTION) | `ON DELETE CASCADE` | Deleting a study should remove its series |
| `files.patient_id → patients.id` | none (NO ACTION) | `ON DELETE CASCADE` | Part of hierarchy |
| `files.study_id → studies.id` | none (NO ACTION) | `ON DELETE CASCADE` | Part of hierarchy |
| `files.series_id → series.id` | none (NO ACTION) | `ON DELETE CASCADE` | Part of hierarchy |
| `file_changes.file_id → files.id` | none (NO ACTION) | `ON DELETE CASCADE` | Audit trail orphaned if file removed |
| `file_changes.by_user_id → users.id` | none (NO ACTION) | `ON DELETE SET NULL` | Preserve audit trail if user deleted |
| `replica_files.replica_id → replicas.id` | none (NO ACTION) | `ON DELETE CASCADE` | `Replica.delete()` already does this manually |
| `replica_files.file_id → files.id` | none (NO ACTION) | `ON DELETE CASCADE` | Orphaned if file removed |
| `shared_files.file_id → files.id` | `ON DELETE CASCADE` | ✓ Keep as-is | Only explicit CASCADE — correctly done |

**Severity: HIGH** — 9 of 10 FKs lack explicit `ON DELETE` and default to `NO ACTION`, which will cause errors on cascading deletes.

### 3.2 Missing CHECK constraints

| Table.Column | Suggested CHECK | Rationale |
|-------------|----------------|-----------|
| `users.status` | `CHECK (status IN ('active', 'deactivated'))` | Only two valid values used in code |
| `users.admin` | Already `BOOLEAN NOT NULL` | ✓ OK |
| `files.indexed` | Already `BOOLEAN NOT NULL` | ✓ OK |
| `series.modality` | Prefer lookup table or enum | DICOM modality is a defined vocabulary (~80 values) |
| `patients.sex` | `CHECK (sex IN ('M', 'F', 'O'))` | DICOM VR: CS with defined values |
| `replica_files.status` | Already `INTEGER` with Status class | Consider `SMALLINT` or `TEXT` with CHECK |
| `replicas.status` | `CHECK (status IN ('indexing', 'ok', 'error'))` | Match code usage |

**Severity: LOW-MEDIUM** — missing domain constraints.

### 3.3 Missing UNIQUE constraints

| Table | Missing UNIQUE | Issue |
|-------|---------------|-------|
| `users(username)` | No unique constraint on username | **Duplicate usernames are possible** — login lookup uses `WHERE username = ?` and returns first match |

**Severity: HIGH** — `users.username` should be `UNIQUE NOT NULL`.

---

## 4. Schema Design Patterns

### 4.1 `insert_or_select` pattern

The pattern follows an optimistic "check-then-insert" approach with `ON CONFLICT ... DO UPDATE` as a safety net. Issues:

**Patient** (`patient.py:25-41`):
- `insert_or_select` checks by `patient_id`, then inserts with `ON CONFLICT (patient_id) DO UPDATE`. The `do_update` only updates `name` via `EXCLUDED.name`. This is correct.
- **Race condition:** Between the SELECT and INSERT, another transaction could insert the same patient_id. The `ON CONFLICT` handles this, but the SELECT returns `None` while the INSERT succeeds with the existing row's id. **This creates a silent partial failure** — the code will return `{'id': patient_id}` but any caller that also reads other columns from the returned dict will get stale data.

**Study** (`study.py:22-43`):
- Same race condition as Patient.
- `do_update` updates `description` via `EXCLUDED.description`. Correct.

**Series** (`series.py:23-44`):
- **BUG:** The `do_update` clause is `self.table.number = EXCLUDED.number` — updating the series **number** to the same value being inserted. This is a no-op upsert that serves no purpose. Should be `self.table.description = EXCLUDED.description` (description is the mutable field).

**Files** (`files.py:106-110`):
- Calls `get()` which joins 4 tables, then calls `add()` which calls `insert_or_select` on Patient, Study, Series, then inserts the file. The file insert has no `ON CONFLICT` clause — it relies on the SELECT check. **No upsert safety net.**

### 4.2 `notify_event()` trigger

```sql
payload = json_build_object('table', TG_TABLE_NAME,
                            'action', TG_OP,
                            'old', row_to_json(OLD),
                            'new', row_to_json(NEW));
```

Issues:

1. **NULL handling:** `row_to_json(NULL)` returns `NULL`, not `NULL::json`. `json_build_object` will produce `"old": null` for INSERT and `"new": null` for DELETE. While not a crash, the consumer must handle these.

2. **Payload size:** PostgreSQL NOTIFY has an 8000-byte limit (default `max_notify_queue_pages`). A wide row with JSONB blobs can easily exceed this. The trigger will fail silently or truncate.

3. **Only on replicas:** The trigger is defined only on the `replicas` table despite the function name being generic. The function definition is duplicated in both the migration and `Replica.sync_db()`.

4. **`FOR EACH ROW` overhead:** Every row change on replicas sends a notification. For a table that changes infrequently (one master, a few followers), this is fine.

**Severity: LOW-MEDIUM** — functional but fragile for large JSONB payloads.

### 4.3 N+1 query risks

| Location | Pattern | Risk |
|----------|---------|------|
| `Replica.get_all()` (`replica.py:117-126`) | Fetches all replicas, then for **each** replica calls `ReplicaFiles(self.conn).non_indexing(d['id'])` | **HIGH** — classic N+1. For N replicas, makes 1 + N queries. |
| `Patient.get_extra()` (`patient.py:43-84`) | Fetches patient, then studies, then series, then files — 4 queries total | **LOW** — pre-fetches all related entities in bulk with `ISIN` |
| `ReplicaFiles.add()` (`replica_files.py:40-62`) | Fetches all replicas, then loops to insert per-replica rows | **MEDIUM** — bulk insert works, but fetches all replicas in one query (acceptable) |

### 4.4 Soft-delete anomaly

`Files.delete()` (`files.py:188-197`):
- Sets `deleted = TRUE`
- Then calls `ReplicaFiles.delete()` which checks count and either marks deleted (soft) or hard-deletes
- But `ReplicaFiles.delete()` **always** hard-deletes the row matching replica_id + file_id after the soft-delete check

The flow is confusing — `Files.delete` sets `deleted = TRUE` on the file, then `ReplicaFiles.delete` may hard-delete the replica_files row. The file row itself is never hard-deleted.

### 4.5 Missing primary key on `replica_files.id`

Covered in [§1.6](#16-replica_filesid--missing-primary-key). The `replica_files` table has a `SERIAL` column named `id` but it is **not** a primary key. This is almost certainly a bug — the `SERIAL` suggests the intent was `PRIMARY KEY`.

---

## 5. Recommendations

Recommendations are ordered by priority within each tier.

### P0 — Immediate (blockers)

| # | Issue | Severity | Migration |
|---|-------|----------|-----------|
| R1 | **`replica_files` missing PRIMARY KEY** | CRITICAL | `ALTER TABLE replica_files ADD PRIMARY KEY (id);` |
| R2 | **Missing UNIQUE on `users.username`** | HIGH | `ALTER TABLE users ADD UNIQUE (username);` (remove duplicates first) |
| R3 | **Missing FK indexes** (8 of 10 FKs) | HIGH | ```
CREATE INDEX IF NOT EXISTS idx_studies_patient_id ON studies(patient_id);
CREATE INDEX IF NOT EXISTS idx_series_study_id ON series(study_id);
CREATE INDEX IF NOT EXISTS idx_files_patient_id ON files(patient_id);
CREATE INDEX IF NOT EXISTS idx_files_study_id ON files(study_id);
CREATE INDEX IF NOT EXISTS idx_files_series_id ON files(series_id);
CREATE INDEX IF NOT EXISTS idx_file_changes_by_user_id ON file_changes(by_user_id);
CREATE INDEX IF NOT EXISTS idx_replica_files_file_id ON replica_files(file_id);
CREATE INDEX IF NOT EXISTS idx_shared_files_file_id ON shared_files(file_id);
``` |

### P1 — High impact

| # | Issue | Severity | Migration |
|---|-------|----------|-----------|
| R4 | **`TIMESTAMP` → `TIMESTAMPTZ`** for all timestamp columns | HIGH | 9 `ALTER COLUMN ... TYPE TIMESTAMPTZ USING created AT TIME ZONE 'UTC'` statements, drop `AT TIME ZONE 'utc'` from defaults |
| R5 | **Missing `ON DELETE CASCADE`** on 9 FKs | HIGH | 8x `DROP CONSTRAINT ... ADD FOREIGN KEY ... ON DELETE CASCADE` + 1x `ON DELETE SET NULL` for `file_changes(by_user_id)` |
| R6 | **`SERIAL` → `GENERATED ALWAYS AS IDENTITY`** | MEDIUM | New columns: `ALTER TABLE ... ALTER id DROP DEFAULT; ALTER TABLE ... ALTER id ADD GENERATED ALWAYS AS IDENTITY;` (PG10+, requires reparenting sequence) |

### P2 — Medium impact

| # | Issue | Severity | Migration |
|---|-------|----------|-----------|
| R7 | **`SERIAL` → `BIGINT`** on all PKs | MEDIUM | `ALTER TABLE ... ALTER id TYPE BIGINT;` (safe if < 2B rows) |
| R8 | **`Replica.get_all()` N+1** | MEDIUM | Replace per-replica `non_indexing()` calls with a single `SELECT replica_id, COUNT(*) FROM replica_files WHERE status != 0 GROUP BY replica_id` |
| R9 | **Series `do_update` bug** (`series.py:40`) | MEDIUM | Change `do_update(self.table.number, ...)` to `do_update(self.table.description, PseudoColumn('EXCLUDED.description'))` |
| R10 | **Add `idx_replica_files_replica_id_status` composite index** | MEDIUM | `CREATE INDEX idx_rf_replica_status ON replica_files(replica_id, status) WHERE status != 1;` |

### P3 — Low impact / optimization

| # | Issue | Severity | Migration |
|---|-------|----------|-----------|
| R11 | **Add CHECK constraints** | LOW | ```
ALTER TABLE users ADD CHECK (status IN ('active', 'deactivated'));
ALTER TABLE patients ADD CHECK (sex IS NULL OR sex IN ('M', 'F', 'O'));
``` |
| R12 | **`notify_event()` NULL safety** | LOW | Wrap `row_to_json(OLD)` / `row_to_json(NEW)` in `COALESCE(..., '{}'::json)` |
| R13 | **`notify_event()` payload size** | LOW | Consider sending only changed columns, or switch to a dedicated queue table |
| R14 | **Partial index `WHERE deleted = FALSE` on files** | LOW | `CREATE INDEX idx_files_active ON files(study_id) WHERE deleted = FALSE;` |
| R15 | **Remove duplicate index `patients_patient_id`** | LOW | `DROP INDEX patients_patient_id;` (UNIQUE constraint on same column already provides the index) |
| R16 | **GIN indexes on JSONB columns** | LOW | `CREATE INDEX CONCURRENTLY idx_patients_meta_gin ON patients USING GIN (meta);` *(only if JSONB queries exist in workload)* |
| R17 | **`replica_files.status` data type** | LOW | Consider `SMALLINT` (range 0–9 fits) or `TEXT` with CHECK instead of `INTEGER` |

### Quick Wins (safe to apply immediately)

```sql
-- R3: FK indexes
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_studies_patient_id ON studies(patient_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_series_study_id ON series(study_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_files_patient_id ON files(patient_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_files_study_id ON files(study_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_files_series_id ON files(series_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_file_changes_by_user_id ON file_changes(by_user_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_replica_files_file_id ON replica_files(file_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_shared_files_file_id ON shared_files(file_id);

-- R1: Add PK to replica_files
ALTER TABLE replica_files ADD PRIMARY KEY (id);

-- R10: Composite index for sync queries
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_rf_replica_status ON replica_files(replica_id, status);

-- R15: Drop redundant index
DROP INDEX IF EXISTS patients_patient_id;
```

### Migration Strategy

For the non-concurrent changes (R4, R5, R6), follow this order in a single migration:

1. **Add FK indexes** (R3) — safe, concurrent, no downtime
2. **Add PK on replica_files** (R1) — requires brief lock on replica_files (small table)
3. **Add UNIQUE on users.username** (R2) — deduplicate first
4. **Add CHECK constraints** (R11) — fast, no table rewrite
5. **Add `ON DELETE CASCADE`** (R5) — requires rebuilding each FK, exclusive lock per table
6. **Convert timestamps** (R4) — table rewrite per column, plan maintenance window
7. **Convert to IDENTITY** (R6) — new column or sequence migration, plan maintenance window

Steps 5–7 require a maintenance window. Steps 1–4 can be applied hot.
