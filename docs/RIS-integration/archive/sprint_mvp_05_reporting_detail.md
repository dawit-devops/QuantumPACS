# Sprint MVP-05 Detail — Reading Worklist + Structured Reporting + Sign-Off (E-RIS-08)

**Version:** 1.0 · **Date:** 2026-08-18 · **Source:** `ris-integration-spec.md` §9.1; `RELEASE_PLAN.md` E-RIS-08; `02_end_to_end_workflows.md` RIS-WF4; `04_uiux_requirements.md` RIS-UI-24…29
**Cadence:** two 2-week sprints (S8–S9) · **Squads:** RIS-MVP — two backend, two frontend, part-time integration engineer, QA

---

## 1. Sprint Goal

> **"A radiologist opens a priority-sorted reading worklist, dictates a structured report with auto-saved drafts, signs it, and the signed report is automatically distributed to EMR and billing — all in under 5 minutes from sign-off."**

**Scope in:** Reading worklist (priority-sorted, filters, unread toggle), report editor with structured templates, report versioning (JSONB diffs), viewer launch deep-link, sign & route (→ ORU + billing), WIP draft preservation.

**Scope out:** Speech recognition integration (v1.1), critical results (S10).

---

## 2. Team Capacity (two 10-day sprints)

| Role | FTE | Available dev-days (×2) | Notes |
| :--- | :-: | :-: | :--- |
| Backend engineer ×2 | 2.0 | 40 | Reading list API, report editor backend, sign-off + distribution hooks, report versioning |
| Frontend engineer ×2 | 2.0 | 40 | Reading worklist UI, report editor UI, template library, viewer launch, draft preservation |
| Integration engineer | 0.5 | 10 | ORU distribution conformance, report template validation |
| QA | 1.0 | 20 | Reporting E2E, sign-off flow, distribution, RLS regression |
| **Total** | **5.5** | **~110** | Total task estimate below: **~52 dev-days** (BE 16.0 · FE 22.0 · INT 4.0 · QA 10.0) — ~58 days slack |

---

## 3. Task Board

### 3.1 Reading Worklist — E-RIS-08 #1
**Source:** `RELEASE_PLAN.md` E-RIS-08 #1; `ris-integration-spec.md` §4.1; `04_uiux_requirements.md` RIS-UI-24.

| ID | Task | Owner | Est. | Dep | Acceptance check |
| :-: | :--- | :-: | :-: | :-: | :--- |
| S5-01 | Reading list API: `GET /api/ris/reports/reading-list` — priority-sorted (STAT > inpatient > outpatient), filters (modality/site/status/date), unread toggle, server-side pagination; extend existing `reports.reading_list()` | BE | 2.0 | S4-11 | Priority sorting correct; RIS-AC-P01-01 |
| S5-02 | Reading list UI: extend existing `frontend/src/radiologist/ReadingWorklist.tsx` — priority badges, unread toggle, modality/site/status filters, row click → PACS viewer launch | FE | 4.0 | S5-01 | RIS-UI-24 parity; WCAG 2.1 AA |
| S5-03 | Viewer launch deep-link: worklist row click → PACS viewer opens on that study (StudyInstanceUID); return-to-RIS preserves worklist state | FE | 2.0 | S5-02 | RIS-AC-P01-05; RIS-UI-26 |
| S5-04 | Reading list assignment: `POST /api/ris/reports/{exam_id}/assign` — assign to radiologist; unread indicator per user | BE | 1.0 | S5-01 | Assignment works; unread per user |

**Epic exit contribution:** E-RIS-08 #1 (reading worklist).

### 3.2 Report Editor — E-RIS-08 #2/3
**Source:** `RELEASE_PLAN.md` E-RIS-08 #2/3; `ris-integration-spec.md` §3.2 Migration 3; `04_uiux_requirements.md` RIS-UI-25/29; `06_acceptance_criteria.md` RIS-AC-P01-02/06.

| ID | Task | Owner | Est. | Dep | Acceptance check |
| :-: | :--- | :-: | :-: | :-: | :--- |
| S5-05 | `ris_report_templates` table + Alembic migration (Migration 3 partial); template library with modality/body_part | BE | 1.0 | — | Table created; seed templates for common modalities |
| S5-06 | Report templates API: `GET /api/ris/reports/templates` (list by modality), `POST /api/ris/reports/templates` (create) | BE | 1.5 | S5-05 | Templates listed; create works; RIS-AC-P01-02 |
| S5-07 | Report versioning: `ris_report_versions` table + migration; version on every edit (JSONB diff from previous); version history API | BE | 2.0 | S5-05 | Every edit attributed; RIS-AC-P01-06 |
| S5-08 | Auto-save: report content saved asynchronously on edit (debounced); no duplicate reports on re-entry | BE | 1.5 | S5-07 | Draft preserved across sessions; RIS-AC-P01-06 |
| S5-09 | Report editor UI: extend existing `frontend/src/radiologist/ReportPanel.tsx` — structured template library (searchable), sections (findings/impression/recommendations), smart fields, autosave indicator | FE | 5.0 | S5-06 | RIS-UI-25 parity; WCAG 2.1 AA |
| S5-10 | WIP draft list: auto-saved drafts restorable; no duplicate reports on re-entry; draft indicator on reading list | FE | 2.0 | S5-08 | RIS-UI-29 parity; RIS-AC-P01-06 |

**Epic exit contribution:** E-RIS-08 #2/3 (report editor + versioning + drafts).

### 3.3 Sign & Distribute — E-RIS-08 #4/6
**Source:** `RELEASE_PLAN.md` E-RIS-08 #4/6; `ris-integration-spec.md` §5.6 (partial); `06_acceptance_criteria.md` RIS-AC-P01-04.

| ID | Task | Owner | Est. | Dep | Acceptance check |
| :-: | :--- | :-: | :-: | :-: | :--- |
| S5-11 | Sign & route API: `POST /api/ris/reports/{exam_id}/sign` — transition report to SIGNED; emit audit event; trigger ORU distribution hook (stub); trigger charge drop hook (stub) | BE | 2.5 | S5-07 | Report signed; audit logged; RIS-AC-P01-04 |
| S5-12 | ORU distribution stub: signed report → mock ORU payload (HL7 ORU^R01); real distribution in S10; for now, log + mark distributed_at | BE | 1.0 | S5-11 | ORU payload generated; distributed_at set |
| S5-13 | Charge drop stub: signed report → mock billing record; real auto charge drop in S11; for now, log + create placeholder `ris_charges` row | BE | 1.0 | S5-11 | Placeholder charge created; S11-ready |
| S5-14 | Sign dialog UI: completeness warnings (missing required sections); signed report shows status; auto-routing indicator to EMR/billing | FE | 3.0 | S5-11 | RIS-UI-28 parity; warnings shown |
| S5-15 | Report status indicator: signed reports show status on reading list; routing indicator | FE | 1.5 | S5-14 | Status visible; routing indicator |

**Epic exit contribution:** E-RIS-08 #4/6 (sign & distribute — stubs).

### 3.4 Cross-cutting: E2E

| ID | Task | Owner | Est. | Dep | Acceptance check |
| :-: | :--- | :-: | :-: | :-: | :--- |
| S5-16 | Reporting E2E: completed exam → reading list → open → select template → type report → autosave → sign → audit logged → distribution stub → charge stub created | QA | 2.5 | S5-01…15 | RIS-AC-P01-01/02/04/05/06 |
| S5-17 | Draft preservation E2E: start report → close tab → reopen → draft restored; no duplicate | QA | 1.0 | S5-08 | RIS-AC-P01-06 |
| S5-18 | Report versioning E2E: edit report 3 times → version history shows all 3 diffs | QA | 1.0 | S5-07 | RIS-AC-P01-06 |
| S5-19 | RLS on reports: cross-facility report reads denied; home-facility reads work | QA | 0.5 | S5-11 | PAC-SL-61 |

---

## 4. Sprint Milestones

| Milestone | Target | Evidence |
| :--- | :--- | :--- |
| **Day 3 (S8)** | Reading list API + UI scaffold; report templates table + API; versioning | S5-01/02, S5-05/06, S5-07 started |
| **Day 8 (S8)** | Report editor UI; auto-save; sign API + stubs; viewer launch | S5-09/10, S5-08, S5-11…13, S5-03 closed |
| **Day 5 (S9)** | Sign dialog; status indicator; WIP draft list | S5-14/15, S5-10 closed |
| **Day 10 (S9, demo)** | Reporting E2E green; draft preservation; versioning; demo: reading list → template → report → sign → stubs | S5-16…19; sprint review |

---

## 5. Sprint Definition of Done

| # | Check | Verifies | Method |
| :-: | :--- | :--- | :--- |
| D1 | Reading worklist: priority-sorted, filters, unread toggle, viewer launch | RIS-AC-P01-01/05, RIS-UI-24 | S5-16 |
| D2 | Report editor: templates, sections, autosave, versioning, drafts | RIS-AC-P01-02/06, RIS-UI-25/29 | S5-16/17/18 |
| D3 | Sign & distribute: signed → audit → ORU stub → charge stub; completeness warnings | RIS-AC-P01-04, RIS-UI-28 | S5-16 |
| D4 | Engineering DoD: `tsc --noEmit` + `vite build` clean; unit tests green; migrations reviewed | release-plan §6 | CI gate |
| D5 | No P0/P1 open defects | release-plan §6 | Defect triage |

---

## 6. Risks & Watch Items

| Risk | Watch indicator | Mitigation |
| :--- | :--- | :--- |
| Report editor UX complexity (templates, sections, smart fields) | S5-09 estimate 5.0 FE | Start with findings/impression/recommendations sections; smart fields in slack |
| Autosave race conditions (multiple tabs, network interruption) | S5-17 draft test | Debounced save; version conflict detection; last-write-wins with version check |
| ORU distribution stub not representative of real HL7 | S5-12 | Generate real ORU^R01 structure; real distribution wire-up in S10 |
| Report template library scope (how many to seed?) | S5-05 | Seed 10 common modality templates; admin creates rest via UI in v1.1 |

---

## Traceability

| Source work item | Tasks |
| :--- | :--- |
| E-RIS-08 #1 (reading worklist) | S5-01…04 |
| E-RIS-08 #2 (report editor) | S5-05/06/09 |
| E-RIS-08 #3 (versioning + drafts) | S5-07/08/10 |
| E-RIS-08 #4 (sign & route) | S5-11/12/14/15 |
| E-RIS-08 #5 (SR integration) | Deferred to v1.1 |
| E-RIS-08 #6 (charge drop stub) | S5-13 |
| Cross-cutting (reporting E2E, draft, versioning, RLS) | S5-16…19 |
