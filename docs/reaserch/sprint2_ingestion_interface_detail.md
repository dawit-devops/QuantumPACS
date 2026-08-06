# Sprint 2 Detail — Ingestion Gateway (E-PAC-02) & Interface Engine (E-RIS-02)

**Version:** 1.0 · **Date:** 2026-08-04 · **Source:** `requrements/PACS/RELEASE_PLAN.md` E-PAC-02, `requrements/RIS/RELEASE_PLAN.md` E-RIS-02
**Cadence:** 2-week sprint (10 working days) · **Squads:** PACS-Core (ingestion) + RIS-Clinical (interface) with a shared integration engineer · **Format parity:** `requrements/sprint1_platform_foundation_detail.md`

> **Sprint numbering:** this is **Sprint 2** of the delivery sequence = release-plan roadmap **S3** (PACS S3 = E-PAC-02; RIS S3 = E-RIS-02). Per the RIS roadmap, E-RIS-03 (registration/MPI) shares S3 — it starts mid-sprint once the HL7 listener is live (see §4).

---

## 1. Sprint Goal

> **"A modality can push studies via DIMSE C-STORE or DICOMweb STOW-RS — validated, deduplicated, indexed, and retrievable in < 5 min, with orphans landing in an exception worklist — while HL7 v2 ORM/ORU/ADT messages are received, ACKed, parsed, mapped to orders/results, and any failure lands in an exception queue that alerts within 5 minutes."**

**Scope in:** modality registry + AE/IP auth, C-STORE SCP + STOW-RS receiver, DICOM parser → metadata index, validation + duplicate detection, exception/orphan worklist, redo/add-series; HL7 v2 listener + ACK + raw persistence, message parser → normalized JSONB, ORM→order + ORU→result mapping, exception queue + retry, interface health dashboard + ≤ 5-min alerting, FHIR R4 read-only (D).

**Scope out (later sprints):** MWL serving & MPPS (E-PAC-03 / E-RIS-06 — Sprint 3+), tiered archive + Storage Commitment (E-PAC-04), DICOMweb QIDO/WADO retrieval (E-PAC-05), viewer (E-PAC-06), admin console (E-PAC-07), DR/security hardening (E-PAC-10); RIS registration/MPI (E-RIS-03 — Sprint 3), scheduling (E-RIS-05), reporting (E-RIS-08).

**Sprint 1 handoff (required to start):** RBAC seed + `FILE_WRITE`/`FILE_READ`/`INTERFACE_MONITOR`/`INTERFACE_ADMIN` permission wiring (S1-05/S1-22), `app.facility_id` middleware (S1-07), tenant-prefixed object keys (S1-23), metering hooks (S1-24), audit triggers (S1-14), service keys for machine actors (S1-29).

---

## 2. Team Capacity (10 working days)

| Role | FTE | Available dev-days | Notes |
| :--- | :-: | :-: | :--- |
| Backend engineer ×2 | 2.0 | 20 | One on PACS ingestion, one on RIS interface |
| Integration engineer | 0.75 | 7.5 | DICOM/HL7 conformance — **critical path** this sprint |
| Frontend engineer | 0.5 | 5 | Upload status panel + interface health dashboard (shared) |
| QA | 0.5 | 5 | Conformance lab + E2E integration tests |
| **Total** | **3.75** | **~37.5** | Total task estimate below: **~40 dev-days** (BE 24.5 · INT 8.0 · FE 3.5 · QA 4.0) — over capacity by ~2.5 days; BE overhang 4.5, INT overhang 0.5, handled per §6 |

---

## 3. Task Board (grouped by source work item)

> Estimates in dev-days. `Owner:` BE = backend, INT = integration engineer, FE = frontend, QA = test. `Check:` acceptance check (maps to AC/SL IDs where applicable).

### 3.1 Modality registry & DICOM auth — E-PAC-02 #1
**Source:** `pacs-ris-schema.sql` §3 (`modalities`); `PAC/06` PAC-AC-P04-01; `RBAC_matrix_spec.md` §6 (machine access).

| ID | Task | Owner | Est. | Dep | Acceptance check |
| :-: | :--- | :-: | :-: | :-: | :--- |
| S2-01 | Modality registry CRUD + migration: add `ip_allowlist JSONB` to `modalities`; AE-title/IP allow-list auth scoped per facility | BE | 1.5 | S1-03 | PAC-AC-P04-01: unregistered AE/IP rejected + logged; `UNIQUE (facility_id, station_ae_title)` holds |
| S2-02 | DIMSE association security: reject unknown AE title / IP at the SCP handshake; IP change audited + immediately effective | INT | 1.0 | S2-01 | Association refused with audit row; change effective without restart |

**Epic exit contribution:** E-PAC-02 #1 (unregistered AE rejected and logged).

### 3.2 C-STORE SCP + STOW-RS receiver — E-PAC-02 #2
**Source:** `pacs-ris-schema.sql` §6 (`dicom_transactions`, `transfer_sessions`); `docs/specs/uploads_design.md`; `research/pacs-ris-viewer-integration-spec.md` §4 (STOW-RS).

| ID | Task | Owner | Est. | Dep | Acceptance check |
| :-: | :--- | :-: | :-: | :-: | :--- |
| S2-03 | DIMSE C-STORE SCP service (association, store, failure responses) logging `txn_type='C-STORE'` rows | INT | 2.0 | S2-02 | Test modality C-STORE accepted; `dicom_transactions` row per store |
| S2-04 | DICOMweb STOW-RS endpoint (multipart) behind `FILE_WRITE` / service key | BE | 1.5 | S1-05 | STOW accepted; `txn_type='STOW-RS'` logged; 400 on non-DICOM payload |
| S2-05 | Transfer session + disconnect cleanup: partial object writes removed on failure | BE | 1.0 | S2-04 | `uploads_design.md` disconnect case: no orphan objects remain |
| S2-06 | Payload validation: size limit (500 MB default) + DICOM magic bytes + required-tags conformance (`PatientID`, `StudyInstanceUID`, `SeriesInstanceUID`, `SOPInstanceUID`) | BE | 1.0 | S2-04 | Rejects with specific 400 codes per `uploads_design.md` |

**Epic exit contribution:** E-PAC-02 #2 (test modality accepted on both protocols).

### 3.3 Parser → metadata index — E-PAC-02 #3
**Source:** `pacs-ris-schema.sql` §6 (`studies`, `series`, `instances`); `PAC/06` PAC-AC-P04-05; `PAC/05` PAC-SL-20.

| ID | Task | Owner | Est. | Dep | Acceptance check |
| :-: | :--- | :-: | :-: | :-: | :--- |
| S2-07 | DICOM metadata extractor → `studies`/`series`/`instances` insert with upsert semantics (receive complete + re-sent SOPs) | BE | 2.0 | S2-06 | Study retrievable via metadata query < 5 min after C-STORE (PAC-SL-20); counts correct |
| S2-08 | Patient/order matching: accession lookup against `worklist_entries`, patient MPI match; unmatched → QUARANTINED | BE | 1.5 | S2-07 | Unmatched study lands quarantined, never silently dropped |
| S2-09 | Study state machine: `status` (ARRIVED→VERIFIED/COMPLETE/QUARANTINED) + `storage_status` (INCOMING→STORED) with guards | BE | 1.0 | S2-07 | Invalid transitions blocked (schema CHECKs enforced) |

**Epic exit contribution:** E-PAC-02 #3 (index & retrievable < 5 min).

### 3.4 Validation, duplicate detection & exception worklist — E-PAC-02 #4/5
**Source:** `docs/specs/uploads_design.md` (duplicate response); `PAC/06` PAC-AC-P02-03, PAC-AC-P04-05; `PAC/05` PAC-SL-22.

| ID | Task | Owner | Est. | Dep | Acceptance check |
| :-: | :--- | :-: | :-: | :-: | :--- |
| S2-10 | Duplicate detection (SOP/instance hash): existing record → `200 {id, duplicate: true}` | BE | 1.0 | S2-07 | PAC-AC-P02-03: duplicate labeled, no second object |
| S2-11 | Upload/ingest status panel: per-series progress, success/failure with reason, one-click retry (fix the retry-bug from `uploads_design.md`) | FE | 1.5 | S2-10 | PAC-AC-P02-03; failed send shows reason + retry works |
| S2-12 | Exception/orphan worklist API + reconciliation actions (merge, assign accession, discard with audit) + 24 h SLA timer | BE | 1.5 | S2-08 | PAC-AC-P04-05: 100% orphans resolved ≤ 24 h (PAC-SL-22) |
| S2-13 | Orphan-rate dashboard metric (`< 0.5%` of studies) | BE | 0.5 | S2-12 | PAC-SL-22 numerator/denominator visible |

**Epic exit contribution:** E-PAC-02 #4/5 (0 silent drops; orphans worked ≤ 24 h).

### 3.5 Redo / add-series — E-PAC-02 #6
**Source:** `PAC/06` PAC-AC-P02-05; `pacs-ris-schema.sql` §6.

| ID | Task | Owner | Est. | Dep | Acceptance check |
| :-: | :--- | :-: | :-: | :-: | :--- |
| S2-14 | Redo/add-series: same accession → append series to the correct study (reuse `series_number` increment); retrievable as part of the study | BE | 1.5 | S2-07 | PAC-AC-P02-05: appended series part of the original study |

**Epic exit contribution:** E-PAC-02 #6 (redo/add-series correct).

### 3.6 HL7 v2 listener & endpoint registry — E-RIS-02 #1
**Source:** `pacs-ris-schema.sql` §9 (`interface_endpoints`, `hl7_messages`); RIS-WF8; `RBAC_matrix_spec.md` §7 (`INTERFACE_MONITOR/ADMIN`).

| ID | Task | Owner | Est. | Dep | Acceptance check |
| :-: | :--- | :-: | :-: | :-: | :--- |
| S2-15 | HL7 v2 TCP/MLLP listener (ADT/ORM/ORU) with ACK handling + raw message persistence to `hl7_messages` | INT | 2.0 | S2-02 | Messages persisted + ACKed (HL7 ACK on every receipt) |
| S2-16 | `interface_endpoints` registry: create/list per facility, direction/transport/protocol, `last_message_at` updated | BE | 1.0 | S2-15 | `UNIQUE (facility_id, name)`; endpoint status tracked |

**Epic exit contribution:** E-RIS-02 #1 (messages persisted, ACKed).

### 3.7 Message parser → normalized mapping — E-RIS-02 #2
**Source:** RIS-WF1/WF8; `RIS/06` RIS-AC-P08-01, RIS-AC-P06-01; `RIS/05` RIS-SL-20; `pacs-ris-schema.sql` §5 (`orders`, `order_procedures`).

| ID | Task | Owner | Est. | Dep | Acceptance check |
| :-: | :--- | :-: | :-: | :-: | :--- |
| S2-17 | Message parser → normalized segments stored as parsed JSONB on `hl7_messages` | INT | 1.5 | S2-15 | ORM/ORU segments parse without loss; unparseable → exception |
| S2-18 | ORM → order creation: accession + priority (Routine/Urgent/STAT) + indication + prior-auth flag | BE | 1.5 | S2-17 | RIS-AC-P08-01: order accessible for scheduling < 1 min (RIS-SL-20) |
| S2-19 | ORU → results mapping; ADT A04/A08 demographics + A40 merge stub (full MPI in E-RIS-03) | BE | 1.5 | S2-17 | Demographics sync; merge flagged for review |
| S2-20 | Accession uniqueness enforced per facility (partial unique index) — 0 collisions | BE | 0.5 | S2-18 | RIS-AC-P06-01: duplicate accession insert rejected |

**Epic exit contribution:** E-RIS-02 #2 (ORM/ORU map to orders/results; RIS-SL-20).

### 3.8 Exception queue + retry/reconcile — E-RIS-02 #3
**Source:** `RIS/06` RIS-AC-P06-02; `RIS/05` RIS-SL-23 (G5).

| ID | Task | Owner | Est. | Dep | Acceptance check |
| :-: | :--- | :-: | :-: | :-: | :--- |
| S2-21 | Exception queue: failed/unparseable messages land with reason + status; retry/reconcile actions | BE | 1.5 | S2-17 | 0 silent drops (RIS-SL-23); queue shows reason |
| S2-22 | Retry/reprocess worker + poison-message handling (max retries, quarantine + alert) | BE | 1.0 | S2-21 | Poison message quarantined, alerted, never looped |

**Epic exit contribution:** E-RIS-02 #3 (0 silent drops).

### 3.9 Interface health dashboard & alerting — E-RIS-02 #4 (shared with PACS E-PAC-08)
**Source:** `pacs-ris-schema.sql` §9 (`interface_events`); `RIS/06` RIS-AC-P06-02; `PAC/06` PAC-AC-P04-08; `RIS/05` RIS-SL-23; `PAC/05` PAC-SL-23.

| ID | Task | Owner | Est. | Dep | Acceptance check |
| :-: | :--- | :-: | :-: | :-: | :--- |
| S2-23 | `interface_events` capture (INFO/WARNING/ERROR/CRITICAL) from both DICOM and HL7 paths (incl. modality `last_heartbeat_at`) | BE | 1.0 | S2-03, S2-15 | Events persisted with severity; open/unresolved tracked |
| S2-24 | Interface health dashboard: DICOM queues, HL7 failures, modality online/offline, drill-down; `INTERFACE_MONITOR` | FE | 2.0 | S2-23 | RIS-AC-P06-02 + PAC-AC-P04-08: fault visible with drill-down |
| S2-25 | ≤ 5-min alerting on severity ≥ ERROR via notification subsystem (built S1-25) | BE | 1.0 | S2-23 | RIS-SL-23 / PAC-SL-23: alert fires ≤ 5 min in staging |

**Epic exit contribution:** E-RIS-02 #4 (G5; `INTERFACE_MONITOR`); reused by E-PAC-08.

### 3.10 FHIR R4 read-only — E-RIS-02 #5 (D)
**Source:** RIS PRD §4.2; `pacs-ris-schema.sql` §5.

| ID | Task | Owner | Est. | Dep | Acceptance check |
| :-: | :--- | :-: | :-: | :-: | :--- |
| S2-26 | FHIR R4 read endpoints: `ServiceRequest` + `DiagnosticReport` (MVP read-only) | BE | 1.5 | S2-18 | Conformance smoke tests (may slip to Sprint 3 if BE over budget) |

**Epic exit contribution:** E-RIS-02 #5 (conformance smoke tests).

### 3.11 Conformance lab & E2E integration tests (cross-cutting)
**Source:** `PAC/05` PAC-SL-20/22; `RIS/05` RIS-SL-20/23; G1/G5 exit gates.

| ID | Task | Owner | Est. | Dep | Acceptance check |
| :-: | :--- | :-: | :-: | :-: | :--- |
| S2-27 | DICOM conformance lab: repeatable C-STORE/MWL/MPPS test-set scripts for modality onboarding | INT | 1.5 | S2-03 | Repeatable scripts; G1/G5 evidence (reused by E-PAC-08) |
| S2-28 | Ingestion E2E: modality → C-STORE → index → retrievable < 5 min; duplicate → 200; orphan → worklist; **RLS isolation on all new tables** | QA | 2.0 | S2-07…S2-13 | PAC-SL-20/22, PAC-AC-P02-03, P04-05 pass in staging |
| S2-29 | HL7 E2E: ORM → order < 1 min; failure injection → exception queue + alert ≤ 5 min | QA | 1.5 | S2-18…S2-25 | RIS-AC-P08-01/P06-02; RIS-SL-20/23 pass |
| S2-30 | Audit completeness for ingestion/interface events (view/retrieve/export/delete + DICOM/HL7 tx) | QA | 0.5 | S2-28 | 100% of scripted events logged (PAC-SL-60) |

---

## 4. Sprint Milestones

| Milestone | Target | Evidence |
| :--- | :--- | :--- |
| **Day 3** | Modality registry + AE/IP auth live; C-STORE SCP association accepted on test modality | S2-01…S2-02 closed, S2-03 in progress; conformance lab scripts run |
| **Day 5** | Both protocols accept (C-STORE + STOW-RS); HL7 listener ACKs an ORM | S2-03…S2-06, S2-15…S2-16 closed; PAC-SL-20 + RIS-SL-20 asserted |
| **Day 8** | Parser → `studies`/`series`/`instances`; ORM → order; duplicate + orphan handling; exception queue + retry; alert fires | S2-07…S2-14, S2-17…S2-23, S2-25 closed; 0 silent drops |
| **Day 10 (demo)** | Interface health dashboard live; conformance lab + E2E suites green; full loop: modality C-STORE → verified & retrievable; ORM → order → injected failure → exception queue + ≤ 5-min alert | S2-24, S2-26 (or slipped), S2-27…S2-30; sprint review; G1/G5 pre-checks; E-RIS-03 starts (registration) |

---

## 5. Sprint Definition of Done (acceptance checks)

| # | Check | Verifies | Method |
| :-: | :--- | :--- | :--- |
| D1 | Ingestion path: C-STORE + STOW-RS accepted, validated, deduplicated, retrievable < 5 min | E-PAC-02 #2/3/4, PAC-SL-20 | S2-28 E2E test |
| D2 | Modality auth: unregistered AE/IP rejected and logged; IP change audited | PAC-AC-P04-01 | S2-01/S2-02 tests |
| D3 | Orphans < 0.5%, 100% resolved ≤ 24 h; redo/add-series appends correctly | PAC-SL-22, PAC-AC-P02-05, P04-05 | S2-12/S2-13/S2-14 tests |
| D4 | ORM → order < 1 min with accession + priority; ORU → results | RIS-AC-P08-01, RIS-SL-20 | S2-29 HL7 E2E |
| D5 | Interface delivery > 99.9%, 0 silent drops, failures alerted ≤ 5 min | RIS-SL-23, PAC-SL-23, RIS-AC-P06-02 | S2-21/S2-22/S2-25 tests |
| D6 | 100% of DICOM/HL7 transactions + view/retrieve/export/delete events audited | PAC-SL-60 | S2-30 |
| D7 | Engineering DoD: `tsc --noEmit` + `vite build` clean; unit tests green; migrations reviewed | release-plan §6 | CI gate |
| D8 | No P0/P1 open defects at sprint close | release-plan §6 | Defect triage |

---

## 6. Risks & Watch Items (Sprint 2)

| Risk | Watch indicator | Mitigation |
| :--- | :--- | :--- |
| Modality conformance variance (C-STORE quirks, non-standard transfer syntaxes) | PAC-SL-20 retrieval | Conformance lab (S2-27); vendor conformance statements; parser conformance suite |
| HL7 latency / mapping drift (site-specific Z-segments) | RIS-SL-20 order intake | Interface lab daily; configurable segment maps (RIS-US-P06-03 later); exception queue alerts |
| **BE capacity over budget (24.5 vs 20 dev-days)** | Velocity vs. 20 BE-days | Slip S2-26 (FHIR, D-priority) **and** S2-13 (orphan metric) to Sprint 3; integration engineer assists S2-06/S2-10; re-estimate S2-07/S2-08 at stand-up |
| **INT capacity over budget (8.0 vs 7.5 dev-days)** | INT as critical path | Protect INT time; QA runs lab scripts (S2-27 split with QA); defer S2-17 parse-polish to Sprint 3 if needed |
| RLS gap on new high-volume tables (`instances`, `hl7_messages`) | Isolation regression (S2-28) | Follow `NOBYPASSRLS` + `FORCE ROW LEVEL SECURITY` convention from `pacs-ris-multitenancy.md` §3 |
| Upload retry bug regresses | PAC-AC-P02-03 retry test | S2-11 fixes root cause; E2E covers retry-after-failure path |

---

## Traceability

| Source work item | Tasks |
| :--- | :--- |
| E-PAC-02 #1 (modality registry & auth) | S2-01…S2-02 |
| E-PAC-02 #2 (C-STORE SCP + STOW-RS) | S2-03…S2-06 |
| E-PAC-02 #3 (parser → metadata index) | S2-07…S2-09 |
| E-PAC-02 #4 (validation & duplicate) | S2-10…S2-11 |
| E-PAC-02 #5 (exception/orphan worklist) | S2-12…S2-13 |
| E-PAC-02 #6 (redo/add-series) | S2-14 |
| E-RIS-02 #1 (HL7 listener + ACK) | S2-15…S2-16 |
| E-RIS-02 #2 (parser → normalized mapping) | S2-17…S2-20 |
| E-RIS-02 #3 (exception queue + retry) | S2-21…S2-22 |
| E-RIS-02 #4 (health dashboard + alerting) | S2-23…S2-25 |
| E-RIS-02 #5 (FHIR R4 read-only) | S2-26 |
| Cross-cutting (conformance lab, E2E, audit) | S2-27…S2-30 |
