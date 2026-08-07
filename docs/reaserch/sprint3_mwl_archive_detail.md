# Sprint 3 Detail — MWL/MPPS (E-PAC-03) & Tiered Archive + Storage Commitment (E-PAC-04)

**Version:** 1.0 · **Date:** 2026-08-04 · **Source:** `requrements/PACS/RELEASE_PLAN.md` E-PAC-03, E-PAC-04
**Cadence:** 2-week sprint (10 working days) · **Squads:** PACS-Core (MWL/MPPS + storage/ILM) with the shared integration engineer · **Format parity:** `requrements/sprint1_platform_foundation_detail.md`, `requrements/sprint2_ingestion_interface_detail.md`

> **Sprint numbering:** this is **Sprint 3** of the delivery sequence = release-plan roadmap **S4–S5** (PACS S4 = E-PAC-02 tail + E-PAC-03; S5 = E-PAC-04). The two release-plan sprints are merged here because E-PAC-03 and E-PAC-04 share the Storage Commitment handoff and both sit on the ingestion foundation from Sprint 2.

---

## 1. Sprint Goal

> **"A technologist's scanner pulls a populated worklist in under a second and reports MPPS status that drives the tracking board without manual entry, while every completed study receives a verifiable Storage Commitment before the scanner may purge — on tiered, tenant-isolated storage with retention/legal-hold and quota enforcement."**

**Scope in:** MWL SCP (C-FIND) serving, MWL metering, MPPS N-CREATE/N-SET consumer + RIS tracking-board echo, MPPS mismatch → exception, Storage-Commitment console acknowledgment; tiered object storage layer, Storage Commitment engine (success + failure paths), retention policy + legal-hold + purge dry-run, quota tracking + 75/90% alerts, ILM tier transitions (D).

**Scope out (later sprints):** DICOMweb QIDO/WADO retrieval (E-PAC-05 — but see §2 slack note), viewer (E-PAC-06), admin console incl. retention/quota **UI** (E-PAC-07 — backend-only here), interface monitoring (E-PAC-08), DR (E-PAC-10); RIS-side scheduling/MWL UI (E-RIS-05/06).

**Sprint 2 handoff (required to start):** C-STORE SCP + STOW-RS (S2-03/04), parser → `studies`/`series`/`instances` (S2-07), duplicate detection (S2-10), exception/orphan worklist API (S2-12), upload/ingest status panel (S2-11), `interface_events` capture (S2-23). **Roadmap tail:** E-PAC-02 #5/6 (orphan metric S2-13, redo/add-series S2-14) absorb any sprint slack.

---

## 2. Team Capacity (10 working days)

| Role | FTE | Available dev-days | Notes |
| :--- | :-: | :-: | :--- |
| Backend engineer ×2 | 2.0 | 20 | One on MWL/MPPS, one on storage/ILM + SC |
| Integration engineer | 0.75 | 7.5 | DICOM MWL/MPPS/SC conformance — **critical path** |
| Frontend engineer | 0.25 | 2.5 | SC console acknowledgment (PAC-UI-25) only |
| QA | 0.5 | 5 | SC accuracy, retention/quota E2E, conformance |
| **Total** | **3.5** | **~35** | Total task estimate below: **~29 dev-days** (BE 17.0 · INT 7.0 · FE 1.0 · QA 4.0) — ~6 days slack, absorbed per note below |

> **Slack absorption (not committed):** (a) E-PAC-02 roadmap tail — S2-13 (orphan metric), S2-14 (redo/add-series); (b) forward-pull of **E-PAC-05 #1 (QIDO-RS study query API, PAC-SL-16)** once DICOMweb patterns are proven; (c) SC conformance rework time. Nothing past E-PAC-04 scope is committed in this sprint.

---

## 3. Task Board (grouped by source work item)

> Estimates in dev-days. `Owner:` BE = backend, INT = integration engineer, FE = frontend, QA = test. `Check:` acceptance check (maps to AC/SL IDs where applicable).

### 3.1 MWL serving & metering — E-PAC-03 #1/5
**Source:** `pacs-ris-schema.sql` §5 (`worklist_entries`: status, `query_count`, `last_queried_at`, `UNIQUE (facility_id, accession_number)`); `PAC/06` PAC-AC-P02-01; `PAC/05` PAC-SL-14.

| ID | Task | Owner | Est. | Dep | Acceptance check |
| :-: | :--- | :-: | :-: | :-: | :--- |
| S3-01 | MWL SCP (DICOM C-FIND) serving scheduled `worklist_entries` (patient, accession, requested procedure, body part) | INT | 2.0 | S2-03 | PAC-AC-P02-01: console auto-fills without manual entry; query < 1 s p95 (PAC-SL-14) |
| S3-02 | MWL metering hook: `MWL_QUERIES` → `usage_metering` + `query_count`/`last_queried_at` update on the entry | BE | 0.5 | S3-01 | E-PAC-03 #5: metering matches query count |
| S3-03 | Empty-result handling: no matching entries → clear empty response (no misleading defaults) | BE | 0.5 | S3-01 | PAC-AC-P02-01 (empty case) |

**Epic exit contribution:** E-PAC-03 #1 (MWL auto-populates, ≥ 98% in staging).

### 3.2 MPPS consumer & tracking-board echo — E-PAC-03 #2/4
**Source:** `pacs-ris-schema.sql` §5 (`mpps_events`, partitioned; `mpps_status` enum) + the tracking view (`LATERAL` `mpps_events` join over orders/appointments/worklist entries); `PAC/06` PAC-AC-P02-04; `RIS/05` RIS-SL-22.

| ID | Task | Owner | Est. | Dep | Acceptance check |
| :-: | :--- | :-: | :-: | :-: | :--- |
| S3-04 | MPPS N-CREATE/N-SET consumer → `mpps_events` insert + `worklist_entries` status transition (SCHEDULED→IN_PROGRESS→COMPLETED/DISCONTINUED) | INT | 2.0 | S3-01 | PAC-AC-P02-04: status updates without manual entry |
| S3-05 | MPPS → RIS echo: tracking board reads the shared tracking view; update < 5 s (RIS-SL-22) | BE | 1.0 | S3-04 | RIS-SL-22: board reflects MPPS < 5 s; 100% echo to RIS |
| S3-06 | MPPS mismatch (wrong/unknown accession) → exception worklist, never silently dropped | BE | 1.0 | S3-04 | PAC-AC-P02-04 (mismatch case) |
| S3-07 | DISCONTINUED handling: `reason_discontinued` captured; study status → DISCONTINUED | BE | 0.5 | S3-04 | PAC-AC-P02-04 (discontinued shows reason) |

**Epic exit contribution:** E-PAC-03 #2/4 (MPPS drives status; mismatch → exception).

### 3.3 Storage-Commitment console acknowledgment — E-PAC-03 #3 (completion)
**Source:** `PAC/04` PAC-UI-25 (green check "Archived — safe to purge"); base upload/ingest panel from S2-11.

| ID | Task | Owner | Est. | Dep | Acceptance check |
| :-: | :--- | :-: | :-: | :-: | :--- |
| S3-08 | SC acknowledgment UI in the upload/ingest panel: green check "Archived — safe to purge" on SC success; failure shows reason + retry, never a purge prompt | FE | 1.0 | S2-11, S3-13 | PAC-AC-P02-02 console-facing case; PAC-UI-25 parity |

**Epic exit contribution:** E-PAC-03 #3 (status panel parity — base delivered in S2-11).

### 3.4 Tiered object storage layer — E-PAC-04 #1
**Source:** `pacs-ris-schema.sql` §6 (`storage_objects`: `object_key` UNIQUE, `sha256`, `storage_tier_id`, status ACTIVE/TRANSITIONING/EXPIRED/PURGED; `storage_tiers`: TIER1_HOT/TIER2_WARM/TIER3_ARCHIVE); `pacs-ris-multitenancy.md` §4 (tenant-prefixed keys); `PAC/05` PAC-SL-40/41/42/44.

| ID | Task | Owner | Est. | Dep | Acceptance check |
| :-: | :--- | :-: | :-: | :-: | :--- |
| S3-09 | S3-compatible object-store client with tier routing (hot/warm/cold) and tenant-prefixed immutable keys | BE | 2.0 | S2-07 | Tier keys immutable; retrieval meets PAC-SL-40/41/42 per tier |
| S3-10 | `storage_objects` lifecycle: row per ingested object (sha256, size, tier) created on commit of S2-07 ingest | BE | 1.0 | S3-09 | Object rows match ingested studies 1:1 |
| S3-11 | WORM/immutability configuration for the archive tier | BE | 1.5 | S3-09 | PAC-SL-44: archive objects immutable |

**Epic exit contribution:** E-PAC-04 #1 (tiered, tenant-isolated, immutable keys).

### 3.5 Storage Commitment engine — E-PAC-04 #2
**Source:** `pacs-ris-schema.sql` §6 (`storage_commitments`: status PENDING/SUCCESS/WARNING/FAILURE, `UNIQUE (facility_id, transaction_uid)`); `PAC/06` PAC-AC-P02-02; `PAC/05` PAC-SL-15/21.

| ID | Task | Owner | Est. | Dep | Acceptance check |
| :-: | :--- | :-: | :-: | :-: | :--- |
| S3-12 | SC N-ACTION consumer: modality request → `storage_commitments` row (PENDING) + validation of study completeness | INT | 1.5 | S3-04, S3-09 | Request persisted with transaction UID |
| S3-13 | SC success path: validate → commit → N-EVENT-REPORT SUCCESS (`responded_at`, study `storage_status`→ARCHIVED); WARNING for partial | BE | 1.5 | S3-12 | PAC-SL-15: ack < 60 s for a complete series set |
| S3-14 | SC failure path: FAILURE + `failure_reason`; console shows failure + retry; scanner cache **not** purged | BE | 1.0 | S3-13 | PAC-AC-P02-02 (failure case): no purge signal on failure |
| S3-15 | SC accuracy suite: 100% of committed studies verifiable; 0 silent purges | QA | 1.5 | S3-13 | PAC-SL-21 assertion green |

**Epic exit contribution:** E-PAC-04 #2 (SC success/failure semantics correct — G1).

### 3.6 Retention policy engine — E-PAC-04 #3
**Source:** `pacs-ris-schema.sql` §3 (`retention_policies`: `retention_years` 1–100, `legal_hold`, `is_default`, `UNIQUE (facility_id, modality_code)`); `PAC/06` PAC-AC-P04-03; `PAC/05` PAC-SL-43. *(Admin **UI** deferred to E-PAC-07 per PAC-UI-30.)*

| ID | Task | Owner | Est. | Dep | Acceptance check |
| :-: | :--- | :-: | :-: | :-: | :--- |
| S3-16 | Retention policy CRUD per facility (5–30+ yr, pediatric, modality default) + legal-hold override flag | BE | 1.5 | S3-09 | PAC-AC-P04-03 config side; `UNIQUE (facility_id, modality_code)` holds |
| S3-17 | Compliant purge job: dry-run first, age-threshold purge with legal-hold block, every delete audited | BE | 1.5 | S3-16 | PAC-AC-P04-03: 0 accidental purges (PAC-SL-43) |

**Epic exit contribution:** E-PAC-04 #3 (retention/legal-hold honored — G4).

### 3.7 Quota tracking & alerts — E-PAC-04 #4
**Source:** `tenants_design.md` (`storage_quota_bytes`); `PAC/06` PAC-AC-P04-04; `PAC/05` PAC-SL-45; notification subsystem (S1-25).

| ID | Task | Owner | Est. | Dep | Acceptance check |
| :-: | :--- | :-: | :-: | :-: | :--- |
| S3-18 | Quota tracking: per-facility usage aggregation (from `storage_objects`/`usage_metering`) vs. configured quota | BE | 1.0 | S3-10 | Usage vs. quota matches storage |
| S3-19 | 75%/90% quota alerts via notification subsystem; configurable hard-stop blocking new ingestion | BE | 1.0 | S3-18 | PAC-AC-P04-04: alert fires at threshold in staging (PAC-SL-45) |

**Epic exit contribution:** E-PAC-04 #4 (quota alerts + hard-stop — G4).

### 3.8 ILM tier transitions — E-PAC-04 #5 (D)
**Source:** `storage_objects.status` (TRANSITIONING); `PAC/05` PAC-SL-40/41/42.

| ID | Task | Owner | Est. | Dep | Acceptance check |
| :-: | :--- | :-: | :-: | :-: | :--- |
| S3-20 | ILM lifecycle job: automated hot→warm→cold transitions by age with TRANSITIONING guard; reads fall back to source tier | BE | 1.5 | S3-09 | PAC-SL-40/41/42 transition paths; no read failure during move |

**Epic exit contribution:** E-PAC-04 #5 (ILM transitions; WORM on archive tier).

### 3.9 Conformance & E2E acceptance (cross-cutting)
**Source:** G1/G2/G4 exit gates; `PAC/05` PAC-SL-14/15/21/43/45/60/61.

| ID | Task | Owner | Est. | Dep | Acceptance check |
| :-: | :--- | :-: | :-: | :-: | :--- |
| S3-21 | MWL/MPPS/SC conformance E2E: scanner query → MWL; MPPS IN_PROGRESS→COMPLETED; C-STORE → SC ack < 60 s | INT | 1.5 | S3-01, S3-13 | PAC-AC-P02-01/02/04, PAC-SL-14/15 pass in staging |
| S3-22 | Retention/quota E2E: policy → dry-run → compliant purge; legal-hold blocks; quota alert fires | QA | 1.5 | S3-16…S3-19 | PAC-AC-P04-03/04, PAC-SL-43/45 pass |
| S3-23 | RLS isolation regression on new tables (`storage_objects`, `retention_policies`, `mpps_events`) | QA | 0.5 | S3-10 | Cross-facility query returns 0 rows (PAC-SL-61 style) |
| S3-24 | Audit completeness: SC requests/acks, purges, quota events all logged | QA | 0.5 | S3-17, S3-19 | 100% of scripted events (PAC-SL-60) |

---

## 4. Sprint Milestones

| Milestone | Target | Evidence |
| :--- | :--- | :--- |
| **Day 3** | MWL SCP serves seeded entries; MPPS N-CREATE consumed; SC N-ACTION handler in progress | S3-01…S3-04 started; conformance lab scripts run |
| **Day 5** | Full MWL/MPPS loop live (query → IN_PROGRESS → COMPLETED, board echo < 5 s); SC success path returns ack | S3-01…S3-07, S3-12…S3-13 closed; PAC-SL-14/15 asserted |
| **Day 8** | Tiered storage + retention/quota engines; SC failure path; ILM job | S3-09…S3-20 closed; PAC-SL-15/21, PAC-AC-P04-03/04 |
| **Day 10 (demo)** | Conformance + retention/quota E2E suites green; audit complete; demo: scanner query → MWL → MPPS → C-STORE → SC "safe to purge" | S3-21…S3-24; G1/G2/G4 pre-checks; sprint review |

---

## 5. Sprint Definition of Done (acceptance checks)

| # | Check | Verifies | Method |
| :-: | :--- | :--- | :--- |
| D1 | MWL auto-populates at console ≥ 98% without manual entry; query < 1 s p95 | PAC-AC-P02-01, PAC-SL-14 | S3-21 conformance E2E |
| D2 | MPPS drives status without manual entry; mismatch → exception; board echo < 5 s | PAC-AC-P02-04, RIS-SL-22 | S3-04…S3-07 tests |
| D3 | SC success + failure paths correct; console shows before purge; 100% committed verifiable, 0 silent purges | PAC-AC-P02-02, PAC-SL-15/21 | S3-15 SC accuracy suite |
| D4 | Retention/legal-hold honored; 0 accidental purges | PAC-AC-P04-03, PAC-SL-43 | S3-22 E2E |
| D5 | Quota alerts at 75/90%; hard-stop configurable | PAC-AC-P04-04, PAC-SL-45 | S3-22 E2E |
| D6 | RLS isolation + 100% audit on new tables | PAC-SL-60/61 | S3-23/S3-24 |
| D7 | Engineering DoD: `tsc --noEmit` + `vite build` clean; unit tests green; migrations reviewed | release-plan §6 | CI gate |
| D8 | No P0/P1 open defects at sprint close | release-plan §6 | Defect triage |

---

## 6. Risks & Watch Items (Sprint 3)

| Risk | Watch indicator | Mitigation |
| :--- | :--- | :--- |
| SC correctness (premature purge signal) | PAC-SL-21 accuracy | SC validation suite (S3-15); failure path never signals success; conformance lab |
| MPPS conformance variance (modality N-CREATE quirks) | PAC-AC-P02-04 mismatch rate | Conformance lab (S3-21); mismatch → exception worklist (S3-06), never dropped |
| MWL latency under query load | PAC-SL-14 p95 | `(facility_id, modality_id, status)` index; metering hook adds negligible overhead (S3-02) |
| Retention purge regression | PAC-SL-43 | Dry-run before purge (S3-17); legal-hold test suite; 0 accidental purges |
| Tier-transition read race | Retrieval success during TRANSITIONING | TRANSITIONING guard + read fallback to source tier (S3-20) |
| **INT capacity (7.0 vs 7.5 dev-days)** | INT as critical path | Protect INT time; QA runs lab scripts; defer S3-11 (WORM, D) to Sprint 4 if needed |

---

## Traceability

| Source work item | Tasks |
| :--- | :--- |
| E-PAC-03 #1 (MWL SCP serving) | S3-01…S3-03 |
| E-PAC-03 #2 (MPPS consumer + RIS echo) | S3-04…S3-05 |
| E-PAC-03 #3 (upload status panel — base in S2-11) | S3-08 |
| E-PAC-03 #4 (MPPS mismatch → exception) | S3-06…S3-07 |
| E-PAC-03 #5 (MWL metering hook) | S3-02 |
| E-PAC-04 #1 (tiered storage layer) | S3-09…S3-11 |
| E-PAC-04 #2 (Storage Commitment engine) | S3-12…S3-15 |
| E-PAC-04 #3 (retention & legal hold) | S3-16…S3-17 |
| E-PAC-04 #4 (quota tracking & alerts) | S3-18…S3-19 |
| E-PAC-04 #5 (ILM transitions, D) | S3-20 |
| Cross-cutting (conformance, E2E, RLS, audit) | S3-21…S3-24 |
