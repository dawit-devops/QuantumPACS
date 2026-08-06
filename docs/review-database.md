# Database Review — QuantumPACS

- **Reviewer role**: Database specialist (PostgreSQL 16)
- **Skill applied**: `postgresql-table-design` (types, constraints, indexing, migration safety, JSONB, enums)
- **Scope**: `backend/migrations/versions/*.py` (38 migrations), `backend/db/*.py` (access layer), `backend/migrations/env.py`
- **Date**: 2026-08-03
- **Verdict**: Generally strong — TIMESTAMPTZ everywhere, TEXT over VARCHAR, JSONB with `jsonb_path_ops`, partial unique indexes, CHECK constraints instead of native enums, FK indexes present. Two high-severity items: a migration that cannot run in this env.py's transaction wrapping, and `updated_at` columns that are never maintained for FHIR sync.

---

## 1. Strengths

| Area | Observation |
|---|---|
| Data types | `TIMESTAMPTZ` for all event time (correct); `TEXT` not `VARCHAR`; `JSONB` not `JSON`; `UUID` PKs via `gen_random_uuid()` (built-in on PG13+). |
| Enums | `CHECK` constraints for status/severity/priority sets (`033_exams.py:59-63`) instead of native enum types — the right call for evolving business states. |
| Indexing | Indexes on every new FK column (`ix_acquisitions_exam`, `ix_incidents_exam`, `ix_safety_checks_exam`, `ix_protocol_overrides_exam`, `ix_qa_scores_reviewed`...); partial unique index `uq_worklist_accession ... WHERE accession_number != ''` (`027`) and `uq_protocols_code ... WHERE protocol_code != ''` (`036:98-99`) — correct patterns for "unique when set". |
| Migration hygiene | Linear revision chain, documented "Why/Data migration/Rollback" headers on every migration, matching downgrades, `IF NOT EXISTS`/`IF EXISTS` guards, `ADD COLUMN IF NOT EXISTS` for idempotent evolution (`036:83-95`). |
| Multi-tenant | Per-tenant databases with `TENANT_SLUG` migration targeting (`env.py`) and connection pooling (`tenant_middleware.py`). |
| Analytics | GIN `jsonb_path_ops` index on `logs.log` (`032`) — correct choice for containment-only queries. |

---

## 2. Findings

### D1 (High) — `CREATE INDEX CONCURRENTLY` cannot run under this migration env
`032_add_performance_indexes.py:30-47` issues five `CREATE INDEX CONCURRENTLY` statements, but `env.py:51-52` wraps every migration in `context.begin_transaction()`. PostgreSQL raises `CREATE INDEX CONCURRENTLY cannot run inside a transaction block`.
- **Scenario**: Any `alembic upgrade head` (fresh DB or `./manage db init`) stops at revision 032 — unless this deployment runs migrations through a path that never reached 032, the schema is pinned below it.
- **Fix**: Wrap the CONCURRENTLY block with `with op.get_context().autocommit_block():` (each statement needs its own block, since the block auto-commits), or drop `CONCURRENTLY` for the local/test path.
- **Verify**: Run `alembic current` against the dev DB and confirm whether 032 is applied; if it is, check how (it may have been applied via a raw psql session).

### D2 (High) — `updated_at` is never maintained for `patients`, `studies`, `shared_files`
Migration `023` adds `updated_at` columns explicitly *for FHIR `_lastUpdated` support* (`023_updated_at_columns.py`), but no trigger exists and the access layer never writes them: `db/patient.py` has no update path at all (only `insert_or_select`/`get_extra`), and `grep updated_at` in `db/patient.py`, `db/study.py`, `db/share_files.py`, `db/files.py` returns nothing.
- **Impact**: FHIR `_lastUpdated` always equals the insert timestamp. Incremental FHIR sync (the stated purpose of 023) will never see updates to a patient/study — it silently falls back to full sync or misses changes entirely, depending on the consumer.
- **Fix**: Either a `BEFORE UPDATE ... SET updated_at = now()` trigger (simplest, catches all writers) or explicit `updated_at = now()` in every app-side UPDATE. Note the same gap applies to `exams.updated_at`/`qa` tables *if* any code path updates rows without going through the `fields = ['status', 'updated_at']` pattern — the newer modules (`db/exams.py:131`, `db/qa.py:350`) do set it correctly.

### D3 (Medium) — New exam/QA tables (033-036) have no FK constraints
`exams.worklist_entry_id`, `acquisitions.exam_id`, `safety_checks.exam_id`, `incidents.exam_id`, `protocol_overrides.exam_id`, `qa_scores.exam_id`/`protocol_id`, `corrective_actions.*` are UUID columns with indexes but **no `REFERENCES` clauses** (unlike the original schema, `001_initial_schema.py`, which defines FKs, and `003` which added cascades).
- **Impact**: Orphaned acquisitions/incidents/QA scores survive exam deletion; joins silently drop rows; no `ON DELETE CASCADE` guardrails. For a PACS (compliance-sensitive audit trails) orphan rows are a data-integrity liability.
- **Fix**: Add FKs (with `ON DELETE CASCADE` where the child is a detail row, `SET NULL`/`RESTRICT` where it is a reference) in a follow-up migration; indexes already exist, so the constraint adds no new scan cost.

### D4 (Low) — `exams.patient_id TEXT` is a denormalized snapshot, not a link
`033_exams.py:51-57` copies `patient_name`/`patient_birth_date`/`patient_sex`/`accession_number` onto the exam and stores `patient_id` as free-form TEXT with no FK to `patients`.
- **Scenario**: A patient's demographics change in `patients`; historical exams keep the old snapshot (good for audit) but there is no way to tell whether the copied name is stale, and `patient_id` may not match `patients.id` (INTEGER) at all.
- **Recommendation**: Acceptable as a documented snapshot pattern; at minimum document the semantics and index `exams(patient_id, accession_number)` for lookups.

### D5 (Low) — `updated_at` maintenance is inconsistent across modules
Newer modules (`db/exams.py`, `db/qa.py`, `db/reports.py`, `db/roles.py`, `db/routing_rule.py`, `db/fhir_clients.py`) set `updated_at = now()` explicitly in UPDATE paths, while 023-era tables rely on nothing. One convention, applied by habit, is a failure mode.
- **Recommendation**: Central trigger helper (e.g., one function called by all table creators) so every future `updated_at` column is self-maintaining.

### D6 (Info) — `FLOAT` for dose/benchmark values
`kvp`, `mas`, `dlp`, `ctdivol`, `exposure_time` and `acr_benchmark_*` use `FLOAT` (`033`, `036`). Fine for physics/QA display; if these ever feed billing or regulatory reporting requiring exact decimals, switch to `NUMERIC`.

### D7 (Info) — `qa_scores.exam_id` is UNIQUE
`uq_qa_scores_exam` (`036:60`) enforces one QA review row per exam. `skipped` occupies the slot, so an exam marked "skipped" can never receive a real review. Confirm this matches the R05 workflow (if not, drop to a partial unique index on `pass_fail != 'skipped'`).

---

## 3. Recommendations (priority order)

1. **D1** — fix the CONCURRENTLY/transaction conflict and verify the dev DB's actual head (blocking migration path).
2. **D2** — trigger-based `updated_at` for patients/studies/shared_files; FHIR `_lastUpdated` is currently wrong.
3. **D3** — add FK constraints for 033-036 tables (indexes exist; cheap).
4. **D5/D7** — decide on a single `updated_at` convention; revisit `qa_scores` skipped semantics.

*Reviewed with skill: `postgresql-table-design` — types, constraints, partial/expression indexes, JSONB guidance, migration safety sections applied.*
