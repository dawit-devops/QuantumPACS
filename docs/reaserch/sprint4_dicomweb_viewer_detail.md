# Sprint 4 Detail — DICOMweb Gateway (E-PAC-05) & Reading Worklist + Viewer (E-PAC-06)

**Version:** 1.0 · **Date:** 2026-08-04 · **Source:** `requrements/PACS/RELEASE_PLAN.md` E-PAC-05, E-PAC-06
**Cadence:** 2-week sprint (10 working days) · **Squads:** PACS-Core — Backend (DICOMweb) + two frontend engineers (worklist + zero-footprint viewer) · **Format parity:** `requrements/sprint1_platform_foundation_detail.md`, `sprint2_ingestion_interface_detail.md`, `sprint3_mwl_archive_detail.md`

> **Sprint numbering:** this is **Sprint 4** of the delivery sequence = release-plan roadmap **S6–S7** (PACS S6 = E-PAC-05 DICOMweb; S7 = E-PAC-06 viewer). The two release-plan sprints are merged here because the viewer consumes the DICOMweb gateway directly; E-PAC-06's roadmap S8 tail (worklist polish, D-items) is absorbed into this sprint's slack (§2).

---

## 1. Sprint Goal

> **"A radiologist opens a prioritized reading worklist, clicks a study, and sees first frames in under 3 seconds on a zero-footprint web viewer served entirely over an IUA/OAuth2-gated DICOMweb API — with hanging protocols, diagnostic basics, critical-flagging, and key images — on multi-GB studies that stream progressively without ever blanking."**

**Scope in:** QIDO-RS query API, WADO-RS metadata + full-frame retrieval, frame-level WADO-RS progressive streaming, DICOMweb IHE IUA/OAuth2 auth gate + service/share keys, FHIR `ImagingStudy` read (D); prioritized reading worklist (server pagination, filters, search, batch actions), viewer shell (series navigator, viewport basics), hanging protocols, first-frame < 3 s + loading/error states, WIP preservation (D), critical-finding flag + key images, keyboard shortcuts + WCAG 2.1 AA.

**Scope out (later sprints):** advanced tools MPR/MIP/3D/fusion/measurements (v1.1), AI overlay (v2.0), priors panel (v1.1), referring-MD read-only mode + SMART launch (PAC-UI-39/40 — v2.0/EMR), admin console (E-PAC-07), interface monitoring (E-PAC-08).

**Sprint 3 handoff (required to start):** metadata index `studies`/`series`/`instances` (S2-07), tiered storage + `storage_objects` (S3-09/10), Storage Commitment (S3-12…14), MWL/MPPS (S3-01…07), `interface_events` (S2-23), audit triggers + `app.facility_id` middleware (S1-07/14).

---

## 2. Team Capacity (10 working days)

| Role | FTE | Available dev-days | Notes |
| :--- | :-: | :-: | :--- |
| Backend engineer ×2 | 2.0 | 20 | DICOMweb gateway + auth + FHIR |
| Frontend engineer ×2 | 2.0 | 20 | One on worklist, one on the zero-footprint viewer (dedicated per release plan) |
| Integration engineer | 0.5 | 5 | DICOMweb conformance tooling (lighter this sprint) |
| QA | 0.5 | 5 | DICOMweb + reading-path E2E, performance |
| **Total** | **5.0** | **~50** | Total task estimate below: **~36 dev-days** (BE 13.5 · FE 18.5 · INT 1.5 · QA 2.5) — ~14 days slack, absorbed per note below |

> **Slack absorption (not committed):** (a) E-PAC-06 D-items — S4-16 (multi-monitor/calendar view), S4-19 (WIP) — fully complete; (b) forward-pull of **E-PAC-07 #1/#2** (modality registry UI, queue monitor API) on FE/BE slack; (c) PAC-SL-10/11 performance rework time; (d) **QA under-utilized** (2.5 of 5 days) → E-PAC-07 QA smoke testing pulled into QA slack. Nothing past E-PAC-06 scope is committed.

---

## 3. Task Board (grouped by source work item)

> Estimates in dev-days. `Owner:` BE = backend, FE = frontend, INT = integration engineer, QA = test. `Check:` acceptance check (maps to AC/SL IDs where applicable).

### 3.1 QIDO-RS query API — E-PAC-05 #1
**Source:** `research/pacs-ris-viewer-integration-spec.md` §4 (QIDO-RS); `pacs-ris-schema.sql` §6; `PAC/05` PAC-SL-16.

| ID | Task | Owner | Est. | Dep | Acceptance check |
| :-: | :--- | :-: | :-: | :-: | :--- |
| S4-01 | QIDO-RS study/series query: filters (patient, accession, modality, date range), pagination, `total` | BE | 2.0 | S2-07 | PAC-SL-16: query < 500 ms p95; `total` from server |
| S4-02 | QIDO search-param coverage + `includefield` support; empty-result handling | BE | 1.0 | S4-01 | Conformance smoke: documented params return correct DICOMweb JSON |
| S4-03 | QIDO txn metering: `QIDO-RS` rows to `dicom_transactions` (`txn_type` CHECK covers QIDO-RS) | BE | 0.5 | S4-01 | Metering matches query count (PAC-SL-50) |

**Epic exit contribution:** E-PAC-05 #1 (QIDO-RS study query < 500 ms p95).

### 3.2 WADO-RS retrieval — E-PAC-05 #2
**Source:** `research/pacs-ris-viewer-integration-spec.md` §4 (WADO-RS); `PAC/05` PAC-SL-17, PAC-SL-40/41/42.

| ID | Task | Owner | Est. | Dep | Acceptance check |
| :-: | :--- | :-: | :-: | :-: | :--- |
| S4-04 | WADO-RS metadata (`Accept: application/dicom+json`) from `studies`/`series`/`instances` | BE | 1.5 | S2-07 | PAC-SL-17: metadata < 1 s p95 |
| S4-05 | WADO-RS full-instance + single-frame retrieval (`Accept: application/dicom`, image types) from `storage_objects` | BE | 1.5 | S3-10 | Retrieval meets tier SLA (PAC-SL-40/41/42); bytes metered |

**Epic exit contribution:** E-PAC-05 #2 (WADO-RS metadata + frames).

### 3.3 Frame-level progressive streaming — E-PAC-05 #3
**Source:** `PAC/06` PAC-AC-P01-10; `PAC/05` PAC-SL-11; viewer-integration-spec §5.

| ID | Task | Owner | Est. | Dep | Acceptance check |
| :-: | :--- | :-: | :-: | :-: | :--- |
| S4-06 | Frame-level WADO-RS (`/frames/{n}`): partial/short-multipart responses; frames stream as requested | BE | 2.0 | S4-05 | PAC-AC-P01-10: first frames < 3 s on a 2+ GB study; viewer never blocks |
| S4-07 | Rendered/thumbnail fallback (`image/jpeg`) for non-progressive clients + per-frame range | BE | 1.0 | S4-06 | PAC-AC-P01-10 partial: preview renders without full download |

**Epic exit contribution:** E-PAC-05 #3 (progressive retrieval — G3).

### 3.4 DICOMweb auth — E-PAC-05 #4
**Source:** `research/pacs-ris-viewer-integration-spec.md` §6 (IUA/OAuth2), §8 (no PHI in URLs); `RBAC_matrix_spec.md` §6; `docs/specs/share_design.md`, `auth_design.md`.

| ID | Task | Owner | Est. | Dep | Acceptance check |
| :-: | :--- | :-: | :-: | :-: | :--- |
| S4-08 | IHE IUA/OAuth2 bearer-token gate on all QIDO/WADO/STOW routes; UID-based deep links (no PHI in URLs) | BE | 1.5 | S4-01, S4-04 | Token-only access; unauthenticated → 401; no patient identifiers in URLs |
| S4-09 | Service-key (machine) + share-key (read-only) support on DICOMweb routes | BE | 1.0 | S4-08 | Share key renders read-only (share_design parity); scope enforced |

**Epic exit contribution:** E-PAC-05 #4 (IUA/OAuth2 token gate; no PHI in URLs).

### 3.5 FHIR ImagingStudy read — E-PAC-05 #5 (D)
**Source:** RIS PRD §4.2; `pacs-ris-schema.sql` §6.

| ID | Task | Owner | Est. | Dep | Acceptance check |
| :-: | :--- | :-: | :-: | :-: | :--- |
| S4-10 | FHIR R4 `ImagingStudy` read endpoint (MVP read-only) | BE | 1.5 | S4-04 | Conformance smoke tests (may slip to Sprint 5 on BE overrun) |

**Epic exit contribution:** E-PAC-05 #5 (conformance smoke tests).

### 3.6 Prioritized reading worklist — E-PAC-06 #1
**Source:** `PAC/06` PAC-AC-P01-01; `PAC/04` PAC-UI-08/09/10/11; `docs/specs/worklist_design.md` (server `total`, station-AE endpoint, status guard).

| ID | Task | Owner | Est. | Dep | Acceptance check |
| :-: | :--- | :-: | :-: | :-: | :--- |
| S4-11 | Prioritized worklist (STAT > inpatient > outpatient, study date desc), filters (modality/site/date/status/unread), server pagination with `total` | FE | 2.0 | S4-01 | PAC-AC-P01-01; PAC-UI-08/09/10; `total` from server (not client-side) |
| S4-12 | Search (patient ID/name, accession, MRN) + filter-set persistence per user | FE | 1.0 | S4-11 | PAC-AC-P01-01: filters persist across sessions |
| S4-13 | Batch actions + status guard (Mark Performed only for scheduled entries; tooltip) | FE | 1.0 | S4-11 | PAC-UI-11; guard disabled state + tooltip |

**Epic exit contribution:** E-PAC-06 #1 (prioritized worklist with server pagination).

### 3.7 Viewer shell & viewport — E-PAC-06 #2
**Source:** `PAC/06` PAC-AC-P01-04 (MVP subset); `PAC/04` PAC-UI-16/19/20/12/21.

| ID | Task | Owner | Est. | Dep | Acceptance check |
| :-: | :--- | :-: | :-: | :-: | :--- |
| S4-14 | Viewer shell: study/series navigator (thumbnail strip, series number/description/images, empty-series warning) | FE | 2.0 | S4-06 | PAC-UI-19; series with no images show warning |
| S4-15 | Viewport basics: window/level presets (brain/lung/mediastinum/abdomen), zoom, pan, invert, flip/rotate, cine with speed control | FE | 2.5 | S4-14 | PAC-AC-P01-04 (MVP subset); PAC-UI-16 |
| S4-16 | Table + calendar worklist views; double-click opens in new tab; multi-monitor workspace layout | FE | 1.5 | S4-11 | PAC-UI-12/21 (D — absorbed by slack) |

**Epic exit contribution:** E-PAC-06 #2 (viewer shell + diagnostic basics).

### 3.8 Hanging protocols — E-PAC-06 #3
**Source:** `PAC/06` PAC-AC-P01-02; `PAC/04` PAC-UI-14.

| ID | Task | Owner | Est. | Dep | Acceptance check |
| :-: | :--- | :-: | :-: | :-: | :--- |
| S4-17 | Hanging protocol engine: auto-apply per anatomy/modality/priority (e.g., CT-chest 2×4 lung+mediastinum), one-click override, saved per user; generic fallback for unrecognized anatomy | FE | 2.0 | S4-15 | PAC-AC-P01-02 (auto-apply, override persisted, generic fallback prompt) |

**Epic exit contribution:** E-PAC-06 #3 (hanging protocols auto-applied).

### 3.9 First-frame performance & loading states — E-PAC-06 #4
**Source:** `PAC/06` PAC-AC-P01-08; `PAC/04` PAC-UI-20.

| ID | Task | Owner | Est. | Dep | Acceptance check |
| :-: | :--- | :-: | :-: | :-: | :--- |
| S4-18 | First-frame < 3 s: progressive bar/skeleton, explicit error + Retry per failed series, never a blank viewport | FE | 1.5 | S4-14 | PAC-AC-P01-08; PAC-UI-20; series-level retry works |

**Epic exit contribution:** E-PAC-06 #4 (study opens < 3 s — G3).

### 3.10 WIP preservation — E-PAC-06 #5 (D)
**Source:** `PAC/06` PAC-AC-P01-09.

| ID | Task | Owner | Est. | Dep | Acceptance check |
| :-: | :--- | :-: | :-: | :-: | :--- |
| S4-19 | WIP preservation: open study + draft state restored across logout/device switch; no duplicate draft | FE | 1.5 | S4-14 | PAC-AC-P01-09 (state restored, no duplicate report) |

**Epic exit contribution:** E-PAC-06 #5 (WIP preserved).

### 3.11 Critical flag & key images — E-PAC-06 #6
**Source:** `PAC/06` PAC-AC-P01-06/07; `PAC/04` PAC-UI-13/17; notification subsystem (S1-25). *(Deviation note per release plan: on-site flag loop in MVP; teleradiology callback v1.1.)*

| ID | Task | Owner | Est. | Dep | Acceptance check |
| :-: | :--- | :-: | :-: | :-: | :--- |
| S4-20 | Critical-finding flag (one action) + tracked notification (worklist badge persists until acknowledged; ack time recorded) | FE | 1.5 | S4-11 | PAC-AC-P01-06 (flag → documented notification; badge clears on ack) |
| S4-21 | Key-image bookmark (star per frame) + auto-link into report template thumbnails | FE | 1.0 | S4-15 | PAC-AC-P01-07 (key image linked at sign) |

**Epic exit contribution:** E-PAC-06 #6 (critical loop + key images — reading-path gate).

### 3.12 Keyboard shortcuts & accessibility — E-PAC-06 #7
**Source:** `PAC/04` PAC-UI-03/05.

| ID | Task | Owner | Est. | Dep | Acceptance check |
| :-: | :--- | :-: | :-: | :-: | :--- |
| S4-22 | Keyboard-first shortcuts (scroll/zoom/window-level/layout/next-study, configurable per user) + WCAG 2.1 AA audit (focus states, contrast, screen-reader labels) | FE | 1.0 | S4-15 | PAC-UI-03/05; accessibility audit green |

**Epic exit contribution:** E-PAC-06 #7 (keyboard-first + AA pass).

### 3.13 Conformance, E2E & performance (cross-cutting)
**Source:** G3 exit gate; `PAC/05` PAC-SL-16/17/50/60/61.

| ID | Task | Owner | Est. | Dep | Acceptance check |
| :-: | :--- | :-: | :-: | :-: | :--- |
| S4-23 | DICOMweb conformance E2E: QIDO/WADO metadata/frames; frame-level streaming on a 2+ GB study over reference bandwidth | INT | 1.5 | S4-01…S4-06 | PAC-SL-16/17; PAC-AC-P01-10 pass in staging |
| S4-24 | Reading-path E2E: worklist → open study < 3 s → hanging protocol applied → critical flag → key image | QA | 1.5 | S4-11…S4-21 | PAC-AC-P01-01/02/06/07/08 pass |
| S4-25 | RLS + audit regression on DICOMweb routes: every view/retrieve logged; cross-tenant denied | QA | 0.5 | S4-08 | PAC-SL-60/61 (100% view events; denial logged) |
| S4-26 | Performance: QIDO < 500 ms and WADO metadata < 1 s under concurrent load | QA | 0.5 | S4-23 | PAC-SL-16/17 p95 assertions green |

---

## 4. Sprint Milestones

| Milestone | Target | Evidence |
| :--- | :--- | :--- |
| **Day 3** | QIDO-RS query live (PAC-SL-16); worklist list renders with server pagination; viewer shell frame loads | S4-01, S4-11, S4-14 started/closed; conformance tooling run |
| **Day 5** | WADO metadata + frames; worklist search/filters; study opens in viewer viewport | S4-04…S4-07, S4-11…S4-15 closed; first frames < 3 s asserted |
| **Day 8** | Frame-level streaming; hanging protocols; critical flag + key images; WIP; auth gate on all routes | S4-06…S4-09, S4-17…S4-21 closed; PAC-AC-P01-10 partial |
| **Day 10 (demo)** | Conformance + reading-path E2E green; demo: worklist → study < 3 s → read → flag → key image | S4-23…S4-26; G3 pre-checks; sprint review |

---

## 5. Sprint Definition of Done (acceptance checks)

| # | Check | Verifies | Method |
| :-: | :--- | :--- | :--- |
| D1 | QIDO-RS < 500 ms p95; WADO-RS metadata < 1 s p95 | PAC-SL-16/17 | S4-26 perf test |
| D2 | Progressive frame-level streaming: first frames < 3 s on multi-GB studies; viewer never blocks; error + retry, never blank | PAC-AC-P01-10, PAC-SL-11 | S4-23 conformance E2E |
| D3 | Prioritized worklist with server pagination, persisted filters, status guards | PAC-AC-P01-01, PAC-UI-08…11 | S4-24 reading-path E2E |
| D4 | Hanging protocols auto-applied with override; study opens < 3 s | PAC-AC-P01-02/08 | S4-24 E2E |
| D5 | Critical flag tracked to acknowledgment; key images linked | PAC-AC-P01-06/07 | S4-24 E2E |
| D6 | IUA/OAuth2 token gate on all DICOMweb routes; no PHI in URLs; 100% view/retrieve audited; cross-tenant denied | PAC-SL-60/61, PAC-AC-P20-03 | S4-25 regression |
| D7 | Engineering DoD: `tsc --noEmit` + `vite build` clean; unit tests green; migrations reviewed | release-plan §6 | CI gate |
| D8 | No P0/P1 open defects at sprint close | release-plan §6 | Defect triage |

---

## 6. Risks & Watch Items (Sprint 4)

| Risk | Watch indicator | Mitigation |
| :--- | :--- | :--- |
| First-frame latency (progressive rendering complexity) | PAC-SL-10/11 | Frame-level WADO-RS (S4-06), edge cache, rendered fallback (S4-07); perf rework time in slack |
| Viewer never-blank guarantee | PAC-AC-P01-10 error path | Explicit error + series-level retry (S4-18); fail-open never a blank viewport |
| Hanging-protocol edge cases (unrecognized anatomy) | PAC-AC-P01-02 fallback | Generic protocol + save-preference prompt (S4-17) |
| QIDO latency under concurrent load | PAC-SL-16 p95 | Index review on `studies`; metering overhead negligible (S4-03); S4-26 perf test |
| Auth regression on web routes | S4-25 denial tests | IUA gate tests + share-key read-only check (S4-08/09) |
| **FE capacity (18.5 vs 20 dev-days)** | Velocity vs. 20 FE-days | Protect the two viewer engineers; D-items (S4-16/19) slip into slack; worklist polish absorbed |
| DICOMweb conformance drift (vendor client quirks) | S4-23 E2E | Conformance tooling first (Day 3); viewer integration against staging, not mocks |

---

## Traceability

| Source work item | Tasks |
| :--- | :--- |
| E-PAC-05 #1 (QIDO-RS query API) | S4-01…S4-03 |
| E-PAC-05 #2 (WADO-RS metadata + frames) | S4-04…S4-05 |
| E-PAC-05 #3 (frame-level progressive) | S4-06…S4-07 |
| E-PAC-05 #4 (IUA/OAuth2 auth) | S4-08…S4-09 |
| E-PAC-05 #5 (FHIR ImagingStudy, D) | S4-10 |
| E-PAC-06 #1 (prioritized worklist) | S4-11…S4-13 |
| E-PAC-06 #2 (viewer shell & viewport) | S4-14…S4-16 |
| E-PAC-06 #3 (hanging protocols) | S4-17 |
| E-PAC-06 #4 (first-frame < 3 s + loading) | S4-18 |
| E-PAC-06 #5 (WIP preservation, D) | S4-19 |
| E-PAC-06 #6 (critical flag + key images) | S4-20…S4-21 |
| E-PAC-06 #7 (keyboard + accessibility) | S4-22 |
| Cross-cutting (conformance, E2E, RLS/audit, perf) | S4-23…S4-26 |
