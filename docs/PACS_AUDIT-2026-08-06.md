# PACS Workflow Audit — QuantumPACS

**Date**: 2026-08-06
**Method**: Read-only audit by 4 parallel reviewers (DICOM SCP layer, DICOMweb, storage/retrieval, workflow integration) against the `pacs-workflow` skill reference patterns (C-FIND query models, study retrieval, MWL, workflow integration, error handling). Top findings cross-verified directly in source.
**Baseline**: Backend 1240 tests passing, ruff clean (commit `0afe24f`).

## Executive Summary

QuantumPACS has a **solid DICOMweb-capable image repository**: C-STORE + STOW-RS ingestion with hash dedup, WADO-RS study/series/instance retrieval, QIDO-RS study search, a full MWL loop (HL7 ORM/ADT → worklist → C-FIND → auto-perform), tenant isolation, replication + routing rules, and FHIR ImagingStudy. However it is **not yet a complete production PACS**:

- **1 runtime-blocking bug** (MWL C-FIND always returns empty — the headline finding).
- **2 silent-failure traps** (C-MOVE/C-GET advertise success but transfer nothing).
- **4 of the skill's core patterns are missing**: DIMSE Q/R C-FIND (patient/study/series/instance), study-level archive/export, radiologist/physician worklists, STAT/priority queries.
- **Security/robustness gaps**: unauthenticated plaintext DICOM listener (no TLS/AE/IP allowlist), unbounded STOW bodies and QIDO limits, quota bypass on 2 of 3 ingest paths, cross-tenant routing leakage.

## Findings by Severity

### Critical (P0)

#### CR-01 — MWL C-FIND returns zero results at runtime (tuple-unpacking bug)
`dcm/server.py:86` assigns `entries = await Worklist(conn).search(...)` without unpacking, but `search()` returns `(rows, total)` (`db/worklist.py:106`). Iterating the tuple yields the row **list** as the first element; `_entry_to_dataset` calls `.get()` on it → `AttributeError` → caught at `dcm/server.py:94-96` → **Success (0x0000) with an empty result set**. Every modality MWL query gets zero matches; the modality then sees an empty worklist (or, worse, queues nothing).
**Verified**: yes (source read).
**Masked by**: unit test mocks `search` to return a bare list (`tests/test_mwl_handler.py:107-108`).
**Fix**: `rows, _ = await Worklist(conn).search(...)`; add a regression test with the real return shape.

#### CR-02 — C-MOVE and C-GET are no-op "success" stubs
`dcm/server.py:148-155` — both handlers log "not fully implemented" and return `0x0000` (Success). PatientRoot/StudyRoot Q/R MOVE/GET contexts ARE offered at association (`lifecycle.py:81-85`), so a modality/viewer that sends C-MOVE believes the study was moved/retrieved; nothing is ever transmitted (there is no C-STORE SCU anywhere in the codebase — grep: zero hits).
**Fix**: either implement C-MOVE (SCU to destination AE) or stop advertising the contexts and reject with `0xA801`/`0xA801`-style failure.

#### CR-03 — Study/series/instance queries over DIMSE do not exist
Only `ModalityWorklistInformationFind` is offered (`lifecycle.py:79`); no PatientRoot/StudyRoot C-FIND contexts, no Q/R C-FIND handler. The skill's core query models (patient/study/series/instance levels, filters, wildcards) exist only via REST QIDO-RS. Legacy modalities cannot query the archive over DICOM.
**Fix**: add Q/R C-FIND contexts + handler backed by the same filters as QIDO (`api/dicomweb.py:87-177`).

### High (P1)

#### HI-01 — Open, unauthenticated DICOM listener
No TLS, no AE-title restriction, no IP allowlist, no ACSE/DIMSE timeouts, no association/request audit logging on the SCP (`dcm/server.py:158-163`, `lifecycle.py:75-92`). Binds all interfaces (11112). Contrast: the HL7 MLLP listener has IP allowlist + TLS (`lifecycle.py:118-149`). Any host can C-STORE unlimited data, read the worklist, and get false-success C-MOVE.

#### HI-02 — Quota enforced on only one of three ingest paths
Tenant storage quota check exists only in HTTP upload (`api/files.py:52-69,152-168`). C-STORE (`dcm/store.py:36-94`) and STOW-RS (`api/dicomweb.py:245`) bypass it, and `storage_used_bytes` registry isn't updated by those paths — quota bookkeeping drifts. Default quota `0` = unlimited.

#### HI-03 — Dedup keyed by content hash, not SOPInstanceUID
`dcm/store.py:42-45`:
- Same SOPInstanceUID re-sent with different bytes → hash miss → INSERT violates the partial UNIQUE `ix_files_sop_instance_uid` (`017_uids.py:51-53`) → `UniqueViolationError` caught at `db/files.py:148-149` → lookup by random uuid name fails → `storage.copy(data, None)` raises → **C-STORE 0x0001 / STOW 409 instead of graceful dedup**.
- Identical bytes with different SOP UIDs collapse into one row — second UID never retrievable.
- No `ON CONFLICT (sop_instance_uid)` upsert anywhere.

#### HI-04 — STOW-RS study-scoped POST ignores the path UID
`POST /dicomweb/studies/{uid}/instances` never reads `request.path_params['study_uid']` (`api/dicomweb.py:208-267`); a dataset whose StudyInstanceUID differs from the URL is stored anyway (PS3.18 §10.5 requires reporting it in `00081199`).

#### HI-05 — Cross-tenant routing leakage at C-STORE time
`dcm/store.py:71` calls `evaluate_routing_rules(ds)` without `tenant_id` (default `''` → falsy → filter skipped in `db/routing_rule.py:61`). All enabled rules from all tenants apply to every incoming instance. Rules are tenant-tagged at creation (`api/routing.py:52-54`).

#### HI-06 — WADO-RS memory unbounded
Study/series retrieval loads all rows, then reads each file fully into memory (`api/dicomweb.py:351-377, 394-399`); STOW buffers the entire multipart body (`request.body()`, `:210`); QIDO `limit` has no cap (`limit=1000000` → `LIMIT $n`, `:41,171-174`). A large CT/MR study or a crafted request can OOM the worker.

#### HI-07 — Schema drift: ORM `sync_db()` vs Alembic
`sync_db()` (fresh DBs, `lifecycle.py:244-251`) creates tables without the unique UID indexes (`017`) and performance indexes (`032`); Alembic adds them. Dedup/uniqueness guarantees depend on DB provenance. `db/study.py:10-19` and `db/series.py:10-19` also lack the UID columns entirely in the ORM path vs migration `017`.

#### HI-08 — No study/series-level archive or export
Only file-ID-list ZIP (`api/files.py:234-258`, `ZIP_STORED`, buffered to `/tmp` with no cleanup, blocks the event loop) and WADO multipart. No study-level ZIP, no series ZIP, no DICOMDIR, no media/CD export — the skill's "Download entire study as ZIP" pattern is unimplemented.

### Medium (P2)

#### ME-01 — QIDO series/instance filters silently ignored
`_query_series`/`_query_instances` (`api/dicomweb.py:179-206`) never read query params — `?Modality=CT` on `/series` has no effect. Missing filters: SeriesInstanceUID, BodyPartExamined, StudyTime, PatientBirthDate, ReferringPhysician, SOPClassUID, SeriesNumber, InstanceNumber. No hex-tag params (`?0020000D=`), no fuzzymatching.

#### ME-02 — WADO-RS content negotiation absent
No `Accept` header handling (`api/dicomweb.py:270-405`): `Accept: multipart/related` on a single instance still returns `application/dicom`; `application/dicom+json` (metadata) returns a raw blob. No `transferSyntax` param (as_stored only). WADO-URI `objectUID` is mandatory so study/series-level WADO-URI is unreachable (`:306-308`) and `studyUID` is validated for presence only.

#### ME-03 — MWL response and lifecycle incomplete
`_entry_to_dataset` (`dcm/server.py:99-129`) omits ScheduledProcedureStepID, ProtocolName, RequestedProcedureCodeSequence, RequestedProcedurePriority, ScheduledProcedureStepStatus, ReasonForRequestedProcedure, ScheduledStationName; hardcodes Referring/Requesting/Performing physicians `''`. ORM duplicates ignored (no update/cancel semantics, `hl7_server.py:389-391`); no time-range matching; no wildcards; results capped at 1000. `dicom_mwl_port`/`dicom_cmove_port` config dead — all SCPs share 11112.

#### ME-04 — No physician/priority workflow data on studies
Referring/Performing/Reading physician exist only in `files.meta` JSONB and ES — no `studies` columns, `get_meta` never extracts them (`dcm/file.py:22-65`), QIDO returns them empty (`dicom_json.py:26`). Priority (STAT/urgent/routine) exists on `exams` only (`db/exams.py:32-33`); it never flows from HL7 ORM or DICOM, is absent from MWL, and `/reports/reading-list` has no priority/physician/date filters (`api/reports.py:107-119`). No `assigned_radiologist` concept, no per-physician worklist (the skill's radiologist-worklist pattern is unimplemented).

#### ME-05 — No partial-study handling
No study completeness tracking, no expected-instance counts, no study status; `match_worklist_performed` fires on the **first** instance (`dcm/store.py:20-33`) so a partial study marks the MWL entry performed. Ingestion retries have no DLQ/quarantine (`worker.py:71-88`); ORU messages ACKed and dropped (`hl7_server.py:157-159`).

#### ME-06 — DICOMweb metadata/frames/bulkdata missing
Self-declared: `dicomweb_admin.py:72-79`. Also no `POST /dicomweb/studies/{study_uid}` (store-into-study by UID), no rate limiting on DICOMweb, and the CSRF middleware blocks plain STOW clients unless `X-CSRF-Token: 1` is sent (`app.py:103-123`).

#### ME-07 — Misc
- Study dates stored as TEXT (`040_dicomweb_index_columns.py:43`) — lexicographic ranges.
- No body-part modeling in imaging schema (`BodyPartExamined` never extracted).
- No study/series delete/edit endpoints (only per-file soft delete).
- C-STORE discards original filename (uuid names); ZIP names use DB ids not UIDs.
- No per-instance access audit on DICOMweb paths; no `study:complete`/`ingestion:complete` events (files trigger is per-instance).
- WADO-URI: no contentType/frameUID/window params; `studyUID` not cross-checked against `objectUID`.

## What Exists (verified strengths)

- **Ingestion**: C-STORE (11112, storage + Q/R-MOVE/GET + MWL contexts), STOW-RS multipart (validates DICM, SOPInstanceUID, modality whitelist; `00081198/00081199` report), HTTP upload (quota-enforced), HL7 MLLP (TLS + IP allowlist + ADT A01-A40 + ORM^O01 + raw-message audit tables), async Redis ingestion worker with retries.
- **Retrieval**: WADO-RS study/series/instance multipart + single DICOM, WADO-URI object, legacy per-file serve (local/S3/B2 presigned), ZIP/CSV by file IDs, thumbnails, share links, download tokens.
- **Search**: QIDO-RS with PatientID/Name(wildcard)/Accession/StudyInstanceUID/Description(ILIKE)/Modality/StudyDate(range) + limit/offset + `X-Total-Count` + includefield; ES full-text (gracefully disabled when down); FHIR ImagingStudy.
- **Worklist loop**: ORM/ADT population, REST CRUD + cancel, C-FIND SCP (except CR-01), auto-perform on store, station-AE listing.
- **Routing**: condition-based rules (eq/ne/contains/gt/gte/lt/lte/$or), priority, enable/disable, CRUD + audit — but replica fan-out only (HI-05).
- **Isolation**: tenant pools via ContextVar, JWT-claim/header scoping, permissions on all REST DICOMweb paths.
- **Hierarchy**: patient→studies→series→files tree, QIDO lists, `deleted` soft-delete filtering.

## Recommended Action Plan

1. **Fix CR-01 now** (2-line fix + regression test) — MWL is the highest-ROI correctness fix.
2. **CR-02**: stop advertising C-MOVE/C-GET contexts until implemented (fail loudly, not silently).
3. **HI-03**: dedup by `sop_instance_uid` with `ON CONFLICT` upsert; content hash only as a secondary check.
4. **HI-02**: enforce tenant quota + update `storage_used_bytes` in `store_instance()` (shared by C-STORE/STOW).
5. **HI-06**: cap QIDO `limit` (e.g. 1000), stream STOW parts, stream WADO files instead of full reads.
6. **HI-05**: pass tenant context (from worklist entry/study patient tenant or a dedicated field) into `evaluate_routing_rules`.
7. **HI-01**: AE-title allowlist + optional TLS + `require_calling_aet` + association audit events on the SCP.
8. **CR-03 / ME-04**: Q/R C-FIND via the existing QIDO filter logic; persist referring/performing physician + priority from DICOM/HL7; add `assigned_radiologist` + per-physician reading list.
9. **HI-08**: study/series ZIP export (streamed, compressed) + optional DICOMDIR.
10. **ME-01/02/06**: QIDO series/instance filters + hex-tag params, WADO Accept negotiation, metadata/frames endpoints, STOW path-UID validation.

## Review Metadata

- Reviewers: scp-layer-reviewer, dicomweb-reviewer, storage-reviewer, workflow-reviewer (parallel, read-only)
- Verification: top 6 findings re-confirmed by direct source reads; tests not re-run (no code changes)
- Reference: `pacs-workflow` skill (C-FIND models, Orthanc/DCM4CHEE patterns, MWL, retrieval, error handling)
