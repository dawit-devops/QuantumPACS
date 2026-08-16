# Phase 4 — Integration Kickoff (HL7 MLLP + FHIR R4 + MWL C-FIND Parity)

Status: **verification in progress** · Target branch: `phase/hl7-fhir-integration` (off `v3-dev`, after PR #119 merges)
Sources: `docs/IMPLEMENTATION_PLAN-v3.md` §Phase 4, `ADR-012`, `ADR-013`, `ADR-028` R5.

## Headline: features already exist — this phase verifies and closes gaps

F4.1 (MLLP), F4.2 (FHIR R4) and F4.3 (routing rules) were implemented in earlier
phases. The Phase 4 gate suite already passes locally:

```bash
cd backend && venv/bin/python -m pytest tests/integration/test_hl7.py tests/integration/test_fhir.py tests/integration/test_routing.py -q
# 98 passed
```

This phase is therefore: **live verification end-to-end, ADR-028 R5 (MWL C-FIND
parity), TLS smoke, and fixing anything those expose** — not greenfield build.

## What already exists (verified in dev env, Aug 2026)

| Feature | Code | Status |
|---|---|---|
| MLLP server (MLLP framing, whitelist, TLS ctx) | `backend/services/ingestion/hl7_server.py` (`MllpServer`) | Listening on `0.0.0.0:12580` (config.local.yaml overrides default 12579) |
| ADT handlers (A01/A02/A03/A04/A05/A08) incl. merge/unmerge | `handle_adt_message`, `_upsert_patient`, `_merge_patients` | Tested (integration) |
| ORM-O01 → worklist entry (cancel/update/RE) | `handle_orm_message` | Tested (integration) |
| ORU handler | `handle_oru_message` | Tested (integration) |
| SHA-256 audit hash per message | `_store_hl7_message` | Present |
| FHIR R4: Patient read/search, ImagingStudy (nested series/instance + `endpoint` → WADO-RS base), DocumentReference, CapabilityStatement | `backend/api/fhir.py` (+ `fhir_admin.py`, `fhir_audit_middleware.py`) | Tested (integration); live 401 without auth (by design) |
| Routing rules CRUD + table | `backend/api/routing.py`, migration `020_routing_rules` (+`021` tenant_id) | Table exists in dev DB |
| MWL mirror sync (QP `worklist_entries` → dcm4chee) | `api/mwl_sync.py` (Phase 3 commit `079021d`) | Sync worker active when proxy enabled |

## Remaining work (the real Phase 4)

### P4.1 — ADR-028 R5: MWL C-FIND parity test (High)
- [x] Live test: `pynetdicom` C-FIND `ModalityWorklistInformationModelFind` → `DCM4CHEE@localhost:11112` with `ScheduledProcedureStepSequence` keys; assert the ORM-mirrored entry (accession + requested procedure) is returned with correct values.
- [x] Negative: cancelled ORM entry (order control `CA`) must not appear in the C-FIND result.
- [x] Encode as an integration test gated on archive reachability (mirror the `test_dicomweb.py` pattern: skip when archive absent) — `tests/integration/test_mwl_cfind_parity.py` (2 tests; module-skipped when the archive is down, e.g. this dev env).
- [x] Confirm dcm4chee-arc MWL SCP device is enabled in LDAP. dcm4chee-arc serves Worklist C-FIND via DIMSE only — there is **no HTTP `/mwl` endpoint** (verified 404). **Live-verified Aug 2026**: MWL SCP lives on the `WORKLIST` AE (`cn=Modality Worklist Information Model - FIND SCP, dicomAETitle=WORKLIST`, device `dcm4chee-arc`) — `DCM4CHEE` is storage-only. Association from QP (`QPPARITY`) accepted; both parity tests pass against the running archive (PR #122).
- [x] Assert sync latency: entry appears in archive within the sync worker interval (configurable; default check at 10 s). **Live-verified**: test polls C-FIND up to ~40 s (13 × 3 s) for the `mwl_sync` worker mirror — entry lands within one worker cycle (PR #122).

### P4.2 — Live MLLP E2E (Medium)
- [x] Send real ADT-A01 over MLLP (`127.0.0.1:12580`, MLLP framing `0x0B … 0x1C 0x0D`) → patient row appears in QP DB (`patients`) with mapped demographics.
- [x] Send ORM-O01 for that patient → `worklist_entries` row (status per ORC), then MWL C-FIND parity (P4.1).
- [x] Malformed message → MLLP NACK + audit row with `error` set (fail-closed).
- [x] **Gotcha resolved**: dev whitelist now `127.0.0.1/32,10.0.0.0/24` in `config.local.yaml` (fail-closed kept for LAN; loopback enabled for testing — documented decision).
- **Live bugs found & fixed** (mocked suites missed all three):
  1. `jsonb_build_object('tenant_id', $2)` → `IndeterminateDatatypeError` on facility param; fixed with `$2::text` cast (`hl7_server.py::_upsert_patient`).
  2. `jsonb_set(meta, '{}', …)` with an empty path is a **no-op** in PostgreSQL (verified on PG 18); meta never persisted. Fixed both branches to `COALESCE(meta,'{}'::jsonb) || jsonb_build_object(...)` — meta now carries `{"tenant_id": …, "sync_source": "hl7"}`.
  3. (P4.4, below) asyncpg returns jsonb as text → `str.get` AttributeError on FHIR Patient search.
- Encoded: `tests/integration/test_mllp_live.py` (3 tests: ADT patient+audit, ORM worklist+cancel, malformed NACK+audit; real DB assertions; MLLP-reachability-gated).

### P4.3 — MLLP TLS smoke (Low)
- [x] Generated self-signed cert (`/tmp/opencode/mllp-tls/`), set `hl7_mllp_tls_cert`/`hl7_mllp_tls_key` in `config.local.yaml`, restarted → TLS handshake on 12580 (`TLS_AES_256_GCM_SHA384`), ADT processed (ACK + patient row `TLS-PAT-001` with meta). Reverted to plaintext after; `test_mllp_live.py` still 3/3 green.

### P4.4 — FHIR live verification (Medium)
- [x] With auth token: `GET /api/v2/fhir/metadata` → valid CapabilityStatement (`application/fhir+json`, FHIR 4.0.1, resources Patient/ImagingStudy/DocumentReference); 401 unauthenticated (by design).
- [x] `GET /api/v2/fhir/Patient?identifier=<patient_id>` and `.../Patient/{id}` return mapped resources (incl. `sync_source`/`tenant_id` meta tag) — **bug fixed**: `fhir.py::_patient_resource` now JSON-decodes the asyncpg jsonb text.
- [x] `GET /api/v2/fhir/ImagingStudy?patient=<ref>&modality=CT` returns a study with nested `series[].endpoint` → archive WADO-RS base (proxy mode) — **gap fixed**: series-level `endpoint` added (`fhir.py`, `_archive_wado_rs_base()` in `dicomweb_proxy.py`); local mode → QP `/api/dicomweb`, proxy mode → `{dcm4chee_url}/aets/{ae}/rs`. 2 new unit tests (local + proxy).
- [x] `GET /api/v2/fhir/DocumentReference?patient=…` returns report placeholder/share link.
- Note: `ImagingStudy` requires `DICOMWEB_READ` — 403 for resident (expected RBAC); verified 200 with `test.technologist`.

### P4.5 — Gate + CI
- [x] Full Phase 4 gate: 110 passed (hl7/fhir/fhir_audit/routing + live MLLP + parity-skip) local; full backend suite 1693 passed, 4 xfailed, 2 skipped (only `test_e2e.py` container pull blocked — known docker-network issue, same as ES image).
- [x] **Aug 2026 live re-run**: with the archive stack up (`docker/dcm4chee` compose) and `dicom_proxy=true`, the parity tests execute for real — **268 integration tests pass** (2 parity + 2 live MLLP + 36 FHIR + rest). Fixes from live discovery landed via PR #122 (AE `WORKLIST`, `ae.associate()`, mirror-latency polling, FHIR patch target).
- [x] Update `docs/IMPLEMENTATION_PLAN-v3.md` — check off F4.1–F4.3 boxes; note deviations (features pre-existing, phase = verification).
- [x] ADR-028 R5 resolution note appended to the R5 row in `docs/decisions/ADR-028-dcm4chee-archive-migration.md`.

## Risks

| Risk | Impact | Mitigation |
|---|---|---|
| Archive MWL SCP not enabled in LDAP | R5 parity test fails at first step | **Resolved live**: MWL SCP on AE `WORKLIST` (device `dcm4chee-arc`); verified via ldapsearch + passing C-FIND |
| MLLP whitelist blocks 127.0.0.1 | Live E2E NACKs | Resolved: dev whitelist now `127.0.0.1/32,10.0.0.0/24` (fail-closed intentional) |
| Sync latency flakiness in parity test | Flaky CI | Resolved: poll C-FIND with deadline (13 × 3 s) instead of fixed sleep |
| `hl7_mllp_port` 12580 vs documented default 12579 | Doc drift | Keep config.local.yaml authoritative; note in doc |
| Phase 3 PR #119 not merged yet | Branch base divergence | Resolved: merged; branch created after merge |

## Suggested commit sequence (branch `phase/hl7-fhir-integration`)

1. `test(hl7): live MLLP ADT/ORM E2E + parity helper` (with archive-skip marker)
2. `test(fhir): live FHIR resource verification` (auth token fixture)
3. `feat(mwl): C-FIND parity test vs dcm4chee MWL SCP` (test-only or small helper)
4. `docs(adr): ADR-028 R5 parity resolution + phase 4 gate verification`
5. `docs(plan): check off F4.1–F4.3 in IMPLEMENTATION_PLAN-v3.md`