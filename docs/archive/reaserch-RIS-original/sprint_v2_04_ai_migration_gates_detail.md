# Sprint V2-04 Detail — AI Ingestion & Overlays (E-V2-06), Export UI & Share (E-V2-05), Migration (E-V2-07), Specialty/Protocols (E-V2-08) + Phase-1 Gates

**Version:** 1.0 · **Date:** 2026-08-05 · **Source:** `requrements/PACS/RELEASE_PLAN_V2.md` E-V2-05 (UI/share), E-V2-06, E-V2-07, E-V2-08 (specialty/protocol), §2 gates VG-1…VG-5
**Cadence:** 2-week sprint (10 working days) · **Squads:** PACS-V2 — two backend, one frontend, part-time integration engineer (SR/GSPS/FHIR conformance), QA · **Format parity:** `requrements/sprint_v2_01_advanced_viewer_priors_detail.md` … `sprint_v2_03_teleradiology_export_detail.md`
> **Sprint numbering:** this is sprint detail **V2-04** — the **Phase-1 capstone** — matching release-plan roadmap **V2-S7–V2-S8**. It completes the Phase-1 epics (export UI/share links, AI result ingestion + viewer overlays, legacy migration tooling, QC/specialty/responsive completion, hanging-protocol library) and executes the **VG-1…VG-5** Phase-1 exit gates.

---

## 1. Sprint Goal

> **"Phase 1 (v1.1) is declared releasable: AI results land in the archive and render as audited, accept/reject overlays; administrators export and share studies with full audit; legacy studies migrate with 100% count reconciliation; specialty exams archive completely; and every VG-1…VG-5 gate passes with per-persona UAT sign-off."**

**Scope in:** export UI + share links (PAC-UI-41), AI result ingestion (webhook/queue dispatch; SR/GSPS + FHIR Observation/DiagnosticReport/ImagingSelection validation + storage + worklist flag), AI viewer overlay (confidence + accept/reject, rejected hidden + audited), AI access audit; migration tooling (bulk import, count reconciliation, sample validation, PAC-UI-33); specialty workflows (cine loops, tomosynthesis, MQSA) + hanging-protocol library versioning; Phase-1 gate execution: VG-1…VG-5 verification, per-persona UAT, evidence package, go/no-go.

**Scope out (later V2 sprints):** UPS-RS workflow (V2-05 — v1.1 uses webhook/queue dispatch), full FHIR + SMART on FHIR (V2-05/06), FHIRcast (V2-06), non-DICOM content (V2-06), edge at scale (V2-06), schema-per-tenant + patient delivery + AI utility gate (V2-07).

**Prior program handoff (required to start):** export backend service (V2-03-15…19), report-routing path (V2-03-12/13), measurement/SR-GSPS layer (V2-01-09/10), viewer overlay-ready rendering layer (ADR-009), service keys (S1-29), notification subsystem (S1-25), QC screen base (V2-02-18/19), interface engine + exception queue (S2-21/22).

---

## 2. Team Capacity (10 working days)

| Role | FTE | Available dev-days | Notes |
| :--- | :-: | :-: | :--- |
| Backend engineer ×2 | 2.0 | 20 | AI ingestion/validation, migration importer, share links |
| Frontend engineer ×1 | 1.0 | 10 | Export UI + share UX, AI overlay, migration UI, specialty touches |
| Integration engineer | 0.5 | 5 | SR/GSPS/FHIR result conformance |
| QA | 1.0 | 10 | AI integrity, migration reconcile, Phase-1 gates + UAT |
| **Total** | **4.5** | **~45** | Total task estimate below: **~34.5 dev-days** (BE 17.0 · FE 8.0 · INT 3.0 · QA 6.5) — ~10.5 days slack, absorbed per note below |

> **Slack absorption (not committed):** (a) Phase-1 gate rework + full-suite regression reruns after every fix; (b) extra AI validation corpus; (c) migration edge cases (corrupt DICOMDIR, partial pulls); (d) forward-pull of **E-V2-09 #1** (UPS-RS N-CREATE scaffold) if the dispatch layer is proven. No new scope enters the capstone without VG-5 change control.

---

## 3. Task Board (grouped by source work item)

> Estimates in dev-days. `Owner:` BE = backend, FE = frontend, INT = integration engineer, QA = test. `Check:` acceptance check (maps to AC/SL/UI/PRD IDs where applicable).

### 3.1 Export UI & share links — E-V2-05 #4
**Source:** `PAC/06` PAC-AC-P04-06; `PAC/04` PAC-UI-41; share-key path (S4-09).

| ID | Task | Owner | Est. | Dep | Acceptance check |
| :-: | :--- | :-: | :-: | :-: | :--- |
| V2-04-01 | Export UI: study selection, format (DICOM/PDF/PDI/XDS-I.b), anonymization toggle, reason code, recipient — reuse export service (V2-03-15…18) | FE | 2.0 | V2-03-15 | PAC-AC-P04-06: export config captured + audited |
| V2-04-02 | Share links: generate read-only `/view/:key` with expiry; friendly expired/invalid message; revoke | BE | 1.5 | S4-09 | PAC-UI-41 parity |
| V2-04-03 | Share-link viewer mode: read-only rendering (no dictation/edit), DICOMweb share-key enforcement on QIDO/WADO | FE | 1.0 | V2-04-02 | Share renders read-only; scope enforced |
| V2-04-04 | Share lifecycle audit: create/view/expire/revoke logged; no PHI in URL | BE | 0.5 | V2-04-02 | PAC-SL-60; no patient identifiers in URLs |

**Epic exit contribution:** E-V2-05 #4 (share links + export UI — VG-4 distribution).

### 3.2 AI result ingestion — E-V2-06 #1/2
**Source:** `PAC/06` PAC-AC-P01-05 (overlay part); PRD §3.1/§3.2; PAC-WF6; RBAC §6.

| ID | Task | Owner | Est. | Dep | Acceptance check |
| :-: | :--- | :-: | :-: | :-: | :--- |
| V2-04-05 | AI dispatch (Phase 1): `ai.jobs` topic on the event backbone (ADR-011) for study-arrived; AI service pulls via WADO-RS with scoped service key (`STUDY_READ`/`RESULTS_READ`) | INT | 1.5 | S1-29, S4-08 | PAC-WF6: pull works with least-privilege token |
| V2-04-06 | Result ingestion: DICOM SR/GSPS + FHIR Observation/DiagnosticReport/ImagingSelection → validate (conformance), dedupe, store, index to study | BE | 2.5 | V2-04-05, V2-01-09 | PRD §3.2: ≥ 95% conformance; 0 corrupt/duplicate |
| V2-04-07 | Worklist AI-flag indicator (PAC-UI-08) + result latency ≤ 5 min study-complete → worklist | BE | 1.0 | V2-04-06 | PRD §3.2 latency metric |
| V2-04-08 | AI access audit: every AI pull/result write logged; no AI path can alter pixels or report | BE | 0.5 | V2-04-05 | PAC-SL-60; PRD §3.2 safety |

**Epic exit contribution:** E-V2-06 #1/2 (ingestion + flag — VG-4 AI part).

### 3.3 AI viewer overlay — E-V2-06 #3
**Source:** `PAC/06` PAC-AC-P01-05; `PAC/04` PAC-UI-18; ADR-009 (overlay-ready rendering layer).

| ID | Task | Owner | Est. | Dep | Acceptance check |
| :-: | :--- | :-: | :-: | :-: | :--- |
| V2-04-09 | Overlay renderer: AI flags as overlay icons with confidence %, toggled per finding; clean viewer when no AI results | FE | 1.5 | V2-04-06 | PAC-AC-P01-05: flag renders with confidence; no-AI → clean |
| V2-04-10 | Accept/reject controls: rejection hides finding, persists per user, audited | FE | 1.0 | V2-04-09 | PAC-AC-P01-05: rejected finding no longer renders + audited |
| V2-04-11 | Overlay data API: study-level AI result summaries for worklist + viewer (permission-gated `RESULTS_READ`) | BE | 1.0 | V2-04-06 | Access control per RBAC §6 |

**Epic exit contribution:** E-V2-06 #3 (overlay accept/reject — PAC-AC-P01-05).

### 3.4 Migration tooling — E-V2-07
**Source:** `PAC/06` PAC-AC-P04-09; `PAC/04` PAC-UI-33.

| ID | Task | Owner | Est. | Dep | Acceptance check |
| :-: | :--- | :-: | :-: | :-: | :--- |
| V2-04-12 | Bulk importer: DICOMDIR scan, C-MOVE/C-GET pull, DICOMweb pull — duplicate-safe re-ingest (S2-10) | BE | 2.0 | S2-10 | PAC-AC-P04-09 ingest path |
| V2-04-13 | Count reconciliation: automated 100% study/series/instance count compare + variance report | BE | 1.5 | V2-04-12 | PAC-AC-P04-09: counts reconcile 100% |
| V2-04-14 | Sample validation workflow: 1–2% radiologist sample checklist + sign-off | FE | 1.0 | V2-04-13 | PAC-AC-P04-09: sample report produced |
| V2-04-15 | Migration progress UI: source inventory, %, reconciliation report, sample task list (PAC-UI-33) | FE | 1.0 | V2-04-13 | PAC-UI-33 parity |

**Epic exit contribution:** E-V2-07 (migration — PAC-AC-P04-09).

### 3.5 Specialty workflows & protocol library — E-V2-08 #2/4
**Source:** `PAC/06` PAC-AC-P02-07; `PAC/06` PAC-AC-P05-02.

| ID | Task | Owner | Est. | Dep | Acceptance check |
| :-: | :--- | :-: | :-: | :-: | :--- |
| V2-04-16 | Specialty ingest/archive: US cine loops archive completely; mammo tomosynthesis series + MQSA QC records preserved and retrievable | BE | 1.5 | S2-07 | PAC-AC-P02-07: complete archival + retrieval |
| V2-04-17 | Specialty conformance: cine/tomosynthesis/MQSA test set in the conformance lab | INT | 1.5 | V2-04-16 | Repeatable scripts; VG-4 evidence |
| V2-04-18 | Hanging-protocol library: versioned libraries per site/specialty, publish + one-click rollback | BE | 1.0 | S4-17 | PAC-AC-P05-02: versioned apply + rollback |

**Epic exit contribution:** E-V2-08 #2/4 (specialty + protocol library — VG-4).

### 3.6 Phase-1 gates & UAT — VG-1…VG-5
**Source:** release-plan V2 §2 (VG-1…VG-5); `PAC/06` PAC-AC-*; `PAC/05` PAC-SL-*.

| ID | Task | Owner | Est. | Dep | Acceptance check |
| :-: | :--- | :-: | :-: | :-: | :--- |
| V2-04-19 | VG-1…VG-3 re-verify: advanced viewer (PAC-AC-P01-04), priors (PAC-SL-24/25), teleradiology + grants (PAC-AC-P03-*, CTG-AC-01…07) | QA | 1.5 | V2-01/V2-02/V2-03 closures | Gates green in staging |
| V2-04-20 | VG-4 re-verify: export/share (PAC-AC-P04-06, PAC-UI-41), AI (PAC-AC-P01-05, PRD §3.2 integrity/latency), migration (PAC-AC-P04-09), QC/specialty (PAC-AC-P02-06/07) | QA | 1.5 | V2-04-01…18 | Gates green in staging |
| V2-04-21 | Per-persona UAT + sign-off: radiologist (advanced tools), teleradiologist (session/callback/routing), technologist (QC/specialty), PACS admin (export/migration/grants UI) | QA | 2.0 | V2-03-24, V2-04-19/20 | VG-5: UAT sign-off; 0 P0/P1 |
| V2-04-22 | Phase-1 evidence package: VG-1…VG-5 report with AC/SL traceability + availability (PAC-SL-01) + audit completeness (PAC-SL-60/61) + go/no-go | QA | 1.0 | V2-04-21 | Package complete; Phase-1 cutover ready |

---

## 4. Sprint Milestones

| Milestone | Target | Evidence |
| :--- | :--- | :--- |
| **Day 3** | Export UI + share link generation live; AI dispatch webhook + first result ingested; importer scaffold | V2-04-01/02, V2-04-05/06, V2-04-12 started |
| **Day 5** | AI overlay first pass; migration count reconciliation run; specialty ingest verified; share viewer read-only | V2-04-09/10, V2-04-13/16, V2-04-03 closed |
| **Day 8** | Overlay accept/reject + audit; sample validation + migration UI; protocol library; VG-1…VG-4 re-verification | V2-04-11/14/15/18, V2-04-19/20 closed |
| **Day 10 (go/no-go)** | UAT sign-off complete; Phase-1 evidence package; Phase-1 releasable | V2-04-21/22; VG-1…VG-5; Phase-1 go/no-go; sprint review |

---

## 5. Sprint Definition of Done (acceptance checks)

| # | Check | Verifies | Method |
| :-: | :--- | :--- | :--- |
| D1 | Export UI + share links: read-only, expiry, friendly invalid, audited | PAC-AC-P04-06, PAC-UI-41 | V2-04-01…04 tests |
| D2 | AI result ingestion: ≥ 95% conformance, 0 corrupt/duplicate, ≤ 5 min to worklist | PRD §3.2, PAC-SL-60 | V2-04-06/07 tests |
| D3 | AI overlay accept/reject; rejected hidden + audited; clean no-AI view | PAC-AC-P01-05 | V2-04-09…11 |
| D4 | Migration: 100% count reconcile + sample validation | PAC-AC-P04-09 | V2-04-13/14 |
| D5 | Specialty workflows complete; protocol library versioned/rollback | PAC-AC-P02-07, PAC-AC-P05-02 | V2-04-16…18 |
| D6 | VG-1…VG-5 green; UAT sign-off (4 personas); 0 P0/P1; 99.9% availability maintained | release-plan V2 §2 | V2-04-19…22 |
| D7 | Engineering DoD: `tsc --noEmit` + `vite build` clean; unit tests green; migrations reviewed | release-plan V2 §6 | CI gate |
| D8 | No P0/P1 open defects; Phase-1 go/no-go review passes | release-plan V2 §6 | Defect triage + V2-04-22 |

---

## 6. Risks & Watch Items (Sprint V2-04)

| Risk | Watch indicator | Mitigation |
| :--- | :--- | :--- |
| AI result conformance variance (SR/GSPS from real vendors) | PRD §3.2 integrity | Conformance corpus + validator (V2-04-06); quarantine non-conforming results to exception queue |
| Overlay performance on multi-finding studies | PAC-UI-18 render | Overlay layer decoupled from pixel pipeline (ADR-009); toggled per finding |
| Migration data loss/corruption | PAC-AC-P04-09 reconcile | Duplicate-safe re-ingest (S2-10); count reconcile automated; sample validation |
| Share-link abuse | PAC-SL-60 audit | Expiry + revocation; read-only enforcement at DICOMweb layer; no PHI in URLs |
| **Phase-1 gate regressions after fixes** | VG-1…VG-5 | Feature freeze; every fix triggers full-suite rerun (V2-04-21); regression window in slack |
| Go/no-go scope creep ("one more feature") | VG evidence drift | Evidence package is the contract; changes after sign-off → Phase-2/V3 backlog |

---

## Traceability

| Source work item | Tasks |
| :--- | :--- |
| E-V2-05 #4 (export UI + share links) | V2-04-01…04 |
| E-V2-06 #1 (dispatch, Phase-1 webhook) | V2-04-05 |
| E-V2-06 #2 (result ingestion + flag) | V2-04-06…08 |
| E-V2-06 #3 (viewer overlay) | V2-04-09…11 |
| E-V2-07 (migration tooling) | V2-04-12…15 |
| E-V2-08 #2 (specialty workflows) | V2-04-16/17 |
| E-V2-08 #4 (protocol library) | V2-04-18 |
| Phase-1 gates VG-1…VG-5 | V2-04-19…22 |
