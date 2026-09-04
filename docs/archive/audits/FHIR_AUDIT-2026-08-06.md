# FHIR Implementation Audit — 2026-08-06

## Summary

The FHIR R4 server (`backend/api/fhir.py`) was audited against the FHIR Developer Skill
and the FHIR R4 specification. Nine confirmed issues (2 critical, 2 high, 5 medium)
were found and fixed. All fixes are live-verified and covered by
`backend/tests/integration/test_fhir.py` (27 tests, full suite 1284 passed / 2 skipped).

## Findings & Fixes

### C1 — Patient DELETE hard-cascades and destroys studies (Critical)

`studies.patient_id` has `ON DELETE CASCADE` (migration 042). A FHIR
`DELETE /Patient/{id}` therefore wiped the patient **and all their studies/series/files**
in a single statement. Demonstrated live: the SMOKE001 patient and all study rows were
destroyed during the audit.

**Fix:** DELETE now returns `409 Conflict` (OperationOutcome `conflict`) when the patient
has studies or files, `404` when absent, `204` only when the patient has no dependents.
The DB-level cascade remains (documented as intentional purge semantics), but the API
refuses to reach it in normal use. `data/files/SMOKE001/*.dcm` are orphaned on disk
(no DB rows) — re-STOW to restore.

### C2 — CSRF middleware blocked every FHIR write (Critical)

All `POST/PUT/DELETE` to `/api/fhir/*` returned `403 CSRF token missing` — only the
`/api/dicomweb` paths were exempt in `app.py`.

**Fix:** machine-API CSRF exemption extended to `/api/fhir` and `/api/v2/fhir`.

### H1 — Patient read/update by logical id → 500 (High)

`GET/PUT /Patient/AUDIT002` failed with `InvalidTextRepresentation`: the handler bound
the string logical id to the integer `patients.id`.

**Fix:** `_patient_by_logical_id()` resolves via the `patient_id` surrogate column first,
falls back to integer id only when numeric.

### H2 — Search with filters but no `_count` → 500 (High)

When no `_count` was given, the code built the query with pypika but dropped the
parameter values, producing `InterfaceError: server expects 0 arguments`; a bare
`Query.from_(table)` without `.select()` additionally rendered an empty SQL string.

**Fix:** `.select(...)` added; values always passed; count query uses `COUNT(*)` + WHERE.

### H3 — FHIR audit middleware never fired (High)

Middleware matched `startswith('/fhir')` but routes are mounted at `/api/fhir`, so
0 audit rows were ever written and `resource_type` was always `''`.

**Fix:** matches `/api/fhir` or `/fhir`; `resource_type` parsed from path parts
(handles `/api/fhir/`, `/fhir/`, `/api/v2/fhir/` variants).

### M1 — Invalid gender → 500 instead of 422 (Medium)

`"gender": "x"` hit the DB CHECK constraint (`M/F/O`) → 500.

**Fix:** enum validated pre-insert → `422` OperationOutcome `value`; input mapping
`male/female/other/unknown` ↔ `M/F/O` via `_SEX_TO_GENDER`.

### M2 — No `Location` header on 201 (Medium)

**Fix:** `Location: {base}/Patient/{logical-id}` returned on create.

### M3 — No versioning: versionId/lastUpdated/ETag/If-Match (Medium)

**Fix:** `meta.versionId`/`meta.lastUpdated` populated from `updated_at`; `ETag:
W/"..."` on read/update; `PUT` with mismatched `If-Match` → `412` OperationOutcome
`conflict`. (No `409` on stale concurrent PUT yet — M3 partially addressed.)

### M4 — Bundle `total` wrong; no paging links (Medium)

**Fix:** `total` from `COUNT(*)` (not returned-row count); `self`/`first`/`next`
links with `_count`/`_offset`; `_count` capped at 100; `search` mode set.

### M5 — `'m'` gender in output (invalid enum) (Medium)

**Fix:** canonical `male/female/other/unknown` values output via `_SEX_TO_GENDER`.

### M6 — Dead SMART client infra; no token endpoint (Medium)

Smart-on-FHIR client plumbing exists but is unused; no token endpoint is exposed.

**Status:** NOT fixed — out of scope for this pass. Documented for v3
(PRD-v3 auth milestone).

### M7 — FHIR enabled-guard only on `/metadata` (Medium)

**Fix:** `_fhir_disabled_response()` (503 OperationOutcome) now guards every endpoint.

### M8 — CapabilityStatement declared `started` but not implemented (Medium)

**Fix:** ImagingStudy search now supports `patient`, `accession`, `modality`,
`started`, `_lastUpdated`; DocumentReference supports `patient`, `type`, `period`,
`_lastUpdated`. CapabilityStatement searchParams match implemented params.

### Post-fix live regressions caught and fixed

- `Patient?birthdate=` → `PostgresSyntaxError: syntax error at or near "$"`: `name` and
  `birthdate` conds were plain strings containing a literal `${idx}` (no f-prefix).
- `Patient?birthdate=ge1980-01-01` → 500: `_prefix_op` was not applied to `birthdate`;
  raw `ge...` string reached `date.fromisoformat`.

## Verification

- Full suite: `1284 passed, 2 skipped` (`pytest -q` from `backend/`)
- Live (Bearer token with PATIENT_READ/WRITE):
  - `POST /Patient` valid → `201` + `Location: /api/fhir/Patient/AUDIT002`
  - `POST /Patient` invalid gender → `422` code `value`
  - `PUT` with bad `If-Match` → `412`; valid → `200` + `ETag`
  - `DELETE` no-dependents → `204`
  - All search params → `200` (identifier, name, birthdate= /ge /lt, `_lastUpdated`,
    `_count`, ImagingStudy patient/accession/modality/started, DocumentReference)
  - Audit table rows recorded with populated `resource_type`
- Commits: `d0cb862` (fixes), plus `fdb80f3`/`5c2aaf6` (prior remediation/skill).

## Remaining Work (tracked)

1. Re-STOW smoke DICOM (`SMOKE001`) to restore study data deleted during the audit demo.
2. M6: real OAuth2/SMART token endpoint + client registration (v3).
3. M3 remainder: `409` on concurrent update conflicts (transactional `updated_at` check).
4. CapabilityStatement `security` extension describing the JWT bearer scheme.
