# Sprint R2-02 Detail — Denial Rework & Unbilled (E-RIS2-03), Template Manager (E-RIS2-04) & SR Polish (E-RIS2-06)

**Version:** 1.0 · **Date:** 2026-08-05 · **Source:** `requrements/RIS/RELEASE_PLAN_V2.md` E-RIS2-03, E-RIS2-04, E-RIS2-06, §2 gates RVG-2/RVG-4; `requrements/RIS/03_user_stories.md` RIS-US-P05-02, RIS-US-P06-03, RIS-US-P01-02; `requrements/RIS/06_acceptance_criteria.md` RIS-AC-P05-02, RIS-AC-P06-03, RIS-AC-P01-02 (SR); `requrements/RIS/05_metrics_and_slas.md` RIS-SL-41; `requrements/RIS/04_uiux_requirements.md` RIS-UI-36
**Cadence:** two 2-week sprints (R2-S3–R2-S4) · **Squads:** RIS-V2 — two backend, one frontend, part-time integration engineer (835/SR), QA · **Format parity:** `requrements/sprint_r2_01_prior_auth_reminders_detail.md`
> **Sprint numbering:** this is sprint detail **R2-02** of the RIS V2 delivery sequence = release-plan roadmap **R2-S3–R2-S4** (Phase 1, v1.1). Merged because denial rework, template versioning, and SR polish are three independent revenue/quality epics that fit the same squad window before the IDN grants sprint.

---

## 1. Sprint Goal

> **"Denied claims return to a reason-coded rework queue with correction and resubmission until unbilled aging is $0 actionable > 5 days; scheduling/procedure/report templates are versioned, site-applied, and one-click rollback; and dictation accuracy improves with specialty lexicons — all audited."**

**Scope in (R2-S3):** 835 denial intake → rework queue, correction + resubmission, unbilled aging dashboard. **Scope in (R2-S4):** template manager (scheduling/procedure-CPT maps, report templates), SR polish (lexicons, verify loop), FHIR `DocumentReference` export.

**Scope out (later R2 sprints):** IDN grants + multi-site scheduling (R2-03), FHIR read + v1.1 gates (R2-04), full FHIR/portal (R2-05), AI-assisted coding + chargeback + v2.0 gates (R2-06).

**Prior program handoff (required to start):** prior-auth claim linkage (R2-01-08), auto charge drop + unbilled aging base (E-RIS-11), 835 export/import (E-RIS-11 #4, D), report templates base (E-RIS-08 #2), SR integration (E-RIS-08 #5), interface engine (S2-21/22).

---

## 2. Team Capacity (two 10-day sprints)

| Role | FTE | Available dev-days (×2) | Notes |
| :--- | :-: | :-: | :--- |
| Backend engineer ×2 | 2.0 | 40 | Denial queue, template versioning, DocumentReference |
| Frontend engineer ×1 | 1.0 | 20 | Rework UI, unbilled dashboard, template manager UI |
| Integration engineer | 0.5 | 10 | 835 intake, SR lexicons |
| QA | 0.5 | 10 | RVG-2 pre-checks, template rollback tests |
| **Total** | **4.0** | **~80** | Total task estimate below: **~23 dev-days** (BE 8.0 · FE 8.0 · INT 4.0 · QA 3.0) — ~57 days slack, absorbed per note below |

> **Slack absorption (not committed):** (a) extra 835 rejection code coverage; (b) template library seed packs per modality; (c) forward-pull of **E-RIS2-05 #1** (grants reuse smoke) if the PACS V2-02 grants land early; (d) SR lexicon expansion. Nothing past E-RIS2-03/E-RIS2-04/E-RIS2-06 scope is committed.

---

## 3. Task Board (grouped by source work item)

> Estimates in dev-days. `Owner:` BE = backend, FE = frontend, INT = integration engineer, QA = test. `Check:` acceptance check.

### 3.1 Denial intake & rework queue — E-RIS2-03 #1/2
**Source:** RIS-AC-P05-02; RIS-M04 (835).

| ID | Task | Owner | Est. | Dep | Acceptance check |
| :-: | :--- | :-: | :-: | :-: | :--- |
| R2-02-01 | 835 denial intake: parse rejection codes → rework queue with reason + priority | INT | 2.5 | E-RIS-11 #4 | RIS-AC-P05-02: denial appears with reason |
| R2-02-02 | Rework queue UI: filters, reason grouping, correction workspace (RIS-UI billing) | FE | 2.5 | R2-02-01 | Rework parity |
| R2-02-03 | Correction + resubmission workflow; full history preserved | BE | 2.0 | R2-02-01 | RIS-AC-P05-02: resubmit + history |
| R2-02-04 | Prior-auth linkage reuse on rework rows (from R2-01-08) | BE | 0.5 | R2-01-08 | Claim line parity |

**Epic exit contribution:** E-RIS2-03 #1/2/4 (queue + resubmission — RVG-2).

### 3.2 Unbilled aging dashboard — E-RIS2-03 #3
**Source:** RIS-SL-41.

| ID | Task | Owner | Est. | Dep | Acceptance check |
| :-: | :--- | :-: | :-: | :-: | :--- |
| R2-02-05 | Unbilled aging dashboard: $0 actionable > 5 days, daily reconcile (extends E-RIS-11 #3) | FE | 2.0 | E-RIS-11 #3 | RIS-SL-41 metric |
| R2-02-06 | Aging escalation alerts (aging > 10 days → biller/manager) | BE | 1.0 | R2-02-05 | Alerts wired to notifications |

**Epic exit contribution:** E-RIS2-03 #3 (unbilled — RVG-2).

### 3.3 Template manager — E-RIS2-04 #1/2/3
**Source:** RIS-AC-P06-03; RIS-UI-36.

| ID | Task | Owner | Est. | Dep | Acceptance check |
| :-: | :--- | :-: | :-: | :-: | :--- |
| R2-02-07 | Template versioning model: scheduling templates + procedure/CPT maps, versioned | BE | 2.0 | E-RIS-05 | RIS-AC-P06-03: versioned apply |
| R2-02-08 | Report template manager UI: tree, version history, publish/rollback, permissions (RIS-UI-36) | FE | 2.5 | E-RIS-08 #2 | RIS-UI-36 parity |
| R2-02-09 | Site-apply with duplicate validation + **one-click rollback** | BE | 1.5 | R2-02-07/08 | RIS-AC-P06-03: rollback verified |

**Epic exit contribution:** E-RIS2-04 (templates — RVG-2).

### 3.4 SR polish & DocumentReference — E-RIS2-06 #1/2/3
**Source:** RIS-AC-P01-02 (SR); RIS-M06.

| ID | Task | Owner | Est. | Dep | Acceptance check |
| :-: | :--- | :-: | :-: | :-: | :--- |
| R2-02-10 | Specialty lexicons (MSK, neuro, cardiac) + accuracy tuning | INT | 1.5 | E-RIS-08 #5 | Dictation verify-loop acceptance |
| R2-02-11 | Verification highlight loop polish (uncertain-word highlighting) | FE | 1.0 | E-RIS-08 #5 | RIS-AC-P01-02 (SR) |
| R2-02-12 | FHIR `DocumentReference` export of dictated report | BE | 1.0 | R2-02-10 | DocumentReference smoke test |

**Epic exit contribution:** E-RIS2-06 (SR polish — RVG-4).

### 3.5 Cross-cutting: E2E & gates
**Source:** RVG-2 pre-checks; RIS-SL-41.

| ID | Task | Owner | Est. | Dep | Acceptance check |
| :-: | :--- | :-: | :-: | :-: | :--- |
| R2-02-13 | E2E: 835 denial → rework → correct → resubmit → aging $0; template publish → site apply → rollback | QA | 2.0 | R2-02-01…09 | RIS-AC-P05-02/P06-03 pass; RVG-2 pre-checks |
| R2-02-14 | Unbilled $0 > 5 days instrumentation (RIS-SL-41) | QA | 1.0 | R2-02-05 | RIS-SL-41 measurable |

---

## 4. Sprint Milestones

| Milestone | Target | Evidence |
| :--- | :--- | :--- |
| **Day 3** | 835 intake scaffold; rework queue data model | R2-02-01/02, R2-02-07 started |
| **Day 5 (R2-S3)** | Rework queue + correction/resubmission live; unbilled dashboard | R2-02-01…05 closed |
| **Day 8 (R2-S4)** | Template versioning + manager UI + rollback; SR lexicons | R2-02-07…11 closed |
| **Day 10 (R2-S4, demo)** | E2E green; demo: denial → rework → resubmit; template rollback; dictation | R2-02-12…14; RVG-2 pre-checks; sprint review |

---

## 5. Sprint Definition of Done (acceptance checks)

| # | Check | Verifies | Method |
| :-: | :--- | :--- | :--- |
| D1 | Denial rework queue with reason codes + resubmission + history | RIS-AC-P05-02 | R2-02-01…04 tests |
| D2 | Unbilled aging $0 actionable > 5 days sustained | RIS-SL-41 | R2-02-05/06/14 |
| D3 | Templates versioned, site-applied, one-click rollback | RIS-AC-P06-03 | R2-02-07…09 tests |
| D4 | SR verify-loop + DocumentReference export | RIS-AC-P01-02 (SR) | R2-02-10…12 |
| D5 | Engineering DoD: `tsc --noEmit` + `vite build` clean; unit tests green; migrations reviewed | release-plan V2 §6 | CI gate |
| D6 | No P0/P1 open defects at sprint close | release-plan V2 §6 | Defect triage |

---

## 6. Risks & Watch Items (Sprint R2-02)

| Risk | Watch indicator | Mitigation |
| :--- | :--- | :--- |
| 835 rejection-code variance | Rework misclassification | Code map library + exception queue; manual reclassify |
| Template drift across sites | Duplicate validation failures | Version pinning; one-click rollback; publish approval |
| SR accuracy regression | Verify-loop highlight rate | Lexicon packs; regression corpus in conformance lab |
| Aging target slip | RIS-SL-41 | Daily reconcile + escalation alerts (R2-02-06) |

---

## Traceability

| Source work item | Tasks |
| :--- | :--- |
| E-RIS2-03 #1/2 (denial intake + queue) | R2-02-01…03 |
| E-RIS2-03 #4 (prior-auth linkage) | R2-02-04 |
| E-RIS2-03 #3 (unbilled dashboard) | R2-02-05/06 |
| E-RIS2-04 #1/2/3 (template manager) | R2-02-07…09 |
| E-RIS2-06 #1/2/3 (SR polish + DocumentReference) | R2-02-10…12 |
| RVG-2 pre-checks + E2E | R2-02-13/14 |
