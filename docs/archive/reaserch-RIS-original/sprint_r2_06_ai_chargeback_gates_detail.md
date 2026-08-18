# Sprint R2-06 Detail — AI-Assisted Coding (E-RIS2-10), Chargeback Analytics (E-RIS2-11), Pre-Registration (E-RIS2-12) + V2 Hardening & Exit Gates

**Version:** 1.0 · **Date:** 2026-08-05 · **Source:** `requrements/RIS/RELEASE_PLAN_V2.md` E-RIS2-10, E-RIS2-11, E-RIS2-12, §2 gates RVG-5…RVG-6; `requrements/RIS/PRD.md` §3 (AI-assisted coding), §5.1 v2.0; `requrements/RIS/06_acceptance_criteria.md` RIS-AC-*; `requrements/RIS/05_metrics_and_slas.md` RIS-SL-40/41/60/61
**Cadence:** three 2-week sprints (R2-S10–R2-S12) · **Squads:** RIS-V2 — two backend, one frontend, part-time integration engineer, part-time Ops/SRE, QA · **Format parity:** `requrements/sprint_r2_05_fhir_portal_detail.md`
> **Sprint numbering:** this is sprint detail **R2-06** — the **V2 capstone** — matching release-plan roadmap **R2-S10–R2-S12** (3 sprints: the final Phase-2 domain epics plus the V2 hardening sprint). It delivers AI-assisted coding (utility-gated), chargeback analytics, and pre-registration, then executes the **RVG-5…RVG-6** exit gates with per-persona UAT.

---

## 1. Sprint Goal

> **"Coders accept AI-suggested CPT/ICD-10 at ≥ 90% on a 30-day pilot; managers see per-site chargeback, denial, and unbilled analytics; patients pre-register digitally before arrival — and every RVG-5…RVG-6 gate passes with per-persona UAT sign-off: RIS V2 is releasable."**

**Scope in (R2-S10):** AI coding suggestion service + accept/override + audit; pilot instrumentation. **Scope in (R2-S11):** chargeback aggregation + manager dashboard; pre-registration. **Scope in (R2-S12):** AI 30-day pilot gate decision, RVG-5…RVG-6 re-verification, full performance + security suite, per-persona UAT, evidence package, go/no-go.

**Scope out (V3+):** everything beyond PRD §5.1 v2.0 (see `requrements/pacs_v3_roadmap.md` — e.g., film, thick-client, AI model development, non-radiology scheduling).

**Prior program handoff (required to start):** full FHIR + portal (R2-05), chargeback data capture at booking (R2-03-08), auto charge drop + 835 (E-RIS-11), coding suggestion base (CPT/ICD-10 from procedure + report), pre-reg data sources (portal).

---

## 2. Team Capacity (three 10-day sprints)

| Role | FTE | Available dev-days (×3) | Notes |
| :--- | :-: | :-: | :--- |
| Backend engineer ×2 | 2.0 | 60 | AI coding service, chargeback, pre-reg feed |
| Frontend engineer ×1 | 1.0 | 30 | Coder accept/override UI, manager dashboards, pre-reg UI |
| Integration engineer | 0.5 | 15 | AI vendor integration, portal feed |
| QA | 1.0 | 30 | AI pilot instrumentation, RVG-5…RVG-6 gates, UAT |
| Ops/SRE | 0.5 | 15 | Cutover runbook + rollback (R2-06-15); staging rehearsal |
| **Total** | **5.0** | **~150** | Total task estimate below: **~27 dev-days** (BE 6.0 · FE 6.0 · INT 2.0 · QA 12.0 · OPS 1.0) — ~123 days slack, absorbed per note below |

> **Slack absorption (not committed):** (a) VG rework + full-suite regression reruns after every fix; (b) extended AI pilot scenarios; (c) chargeback analytics drill-down polish; (d) evidence/documentation polish. No new features enter the capstone without RVG-6 change control.

---

## 3. Task Board (grouped by source work item)

> Estimates in dev-days. `Owner:` BE = backend, FE = frontend, INT = integration engineer, OPS = ops/SRE, QA = test. `Check:` acceptance check.

### 3.1 AI-assisted coding — E-RIS2-10 #1/2
**Source:** PRD §3 (roadmap `O` → gated); RIS-M04.

| ID | Task | Owner | Est. | Dep | Acceptance check |
| :-: | :--- | :-: | :-: | :-: | :--- |
| R2-06-01 | Coding suggestion service: CPT/ICD-10 from procedure + signed report, with confidence | BE + INT | 4.0 | R2-05-01 | Suggestions confirmable |
| R2-06-02 | Accept/override workflow; every suggestion/override audited | FE + BE | 2.5 | R2-06-01 | RIS-SL-60; audit rows |
| R2-06-03 | Pilot instrumentation: acceptance/rejection capture + utility dashboard | QA | 2.0 | R2-06-01 | Acceptance ≥ 90% measurable |

**Epic exit contribution:** E-RIS2-10 (AI coding — RVG-6).

### 3.2 Chargeback analytics — E-RIS2-11 #1/2
**Source:** RIS-AC-P03-04 (chargeback data); RIS-SL-40/41.

| ID | Task | Owner | Est. | Dep | Acceptance check |
| :-: | :--- | :-: | :-: | :-: | :--- |
| R2-06-04 | Per-site chargeback aggregation from bookings (R2-03-08) | BE | 2.0 | R2-03-08 | Chargeback by site reconciles |
| R2-06-05 | Manager dashboard: chargeback, denial rate, unbilled aging by site, drill-down | FE | 2.5 | R2-06-04 | RIS-P07 parity |

**Epic exit contribution:** E-RIS2-11 (chargeback — RVG-6).

### 3.3 Pre-registration — E-RIS2-12 #1/2
**Source:** RIS-UI-23.

| ID | Task | Owner | Est. | Dep | Acceptance check |
| :-: | :--- | :-: | :-: | :-: | :--- |
| R2-06-06 | Portal-submitted pre-registration data visible for completion before arrival | FE + BE | 2.0 | R2-05-07 | RIS-UI-23 parity |
| R2-06-07 | One-click completion at check-in (extends E-RIS-03 check-in) | FE | 1.0 | R2-06-06 | Check-in pre-fill |

**Epic exit contribution:** E-RIS2-12 (pre-reg — RVG-5).

### 3.4 V2 performance & security test
**Source:** RIS-SL-40/41/60/61; PRD §2.3.

| ID | Task | Owner | Est. | Dep | Acceptance check |
| :-: | :--- | :-: | :-: | :-: | :--- |
| R2-06-08 | Full performance suite: FHIR, scheduling, portal under load | QA | 1.5 | R2-05/06 closures | p95 assertions green |
| R2-06-09 | Security test: RLS matrix (incl. grants), RBAC, IDOR on FHIR/portal, share-link paths | QA | 1.5 | R2-06-02 | 0 critical/high; RIS-SL-61 |

**Epic exit contribution:** RVG-6 (perf/security posture).

### 3.5 V2 exit gates & go/no-go — RVG-5…RVG-6
**Source:** release-plan V2 §2.

| ID | Task | Owner | Est. | Dep | Acceptance check |
| :-: | :--- | :-: | :-: | :-: | :--- |
| R2-06-10 | RVG-5 re-verify: full FHIR writes + portal delivery + pre-registration | QA | 1.0 | R2-05 closure | Gate green |
| R2-06-11 | AI coding 30-day pilot gate: acceptance ≥ 90% → v2.0 rollout; else remediation plan | QA | 1.5 | R2-06-03 | Gate decision recorded |
| R2-06-12 | RVG-6 re-verify: charge capture ≥ 98% (RIS-SL-40), unbilled $0 > 5 days (RIS-SL-41), chargeback live | QA | 1.0 | R2-06-04/05 | Gate green |
| R2-06-13 | Per-persona UAT + sign-off: biller (AI coding), manager (chargeback), scheduler, front desk (pre-reg) | QA | 2.0 | R2-06-10…12 | UAT sign-off; 0 P0/P1 |
| R2-06-14 | Consolidated V2 evidence package: RVG-5…RVG-6 report with AC/SL traceability; Phase-1 regression (RVG-1…RVG-4) re-confirmed | QA | 1.0 | R2-06-13 | Package complete |
| R2-06-15 | Production cutover runbook (Phase-2) + rollback; rehearsed once in staging | OPS | 1.0 | R2-06-14 | Cutover rehearsed |
| R2-06-16 | V2 go/no-go review: all gates green + AI gate decision | QA | 0.5 | R2-06-14 | GO / NO-GO recorded |

---

## 4. Sprint Milestones

| Sprint | Milestone | Target | Evidence |
| :--- | :--- | :--- | :--- |
| **R2-S10** | AI coding suggestion service + accept/override live; pilot started | Day 8 | R2-06-01…03 closed |
| **R2-S11** | Chargeback analytics + manager dashboard; pre-registration live | Day 10 | R2-06-04…07 closed |
| **R2-S12** | AI pilot gate decision; RVG-5…RVG-6 re-verified; UAT sign-off; go/no-go | Day 10 | R2-06-08…16 closed; evidence package; sprint review |

---

## 5. Sprint Definition of Done (acceptance checks)

| # | Check | Verifies | Method |
| :-: | :--- | :--- | :--- |
| D1 | AI coding: suggestions with confidence, accept/override audited | RIS-SL-60 | R2-06-01/02 |
| D2 | AI 30-day pilot acceptance ≥ 90% decision recorded | PRD §3 | R2-06-03/11 |
| D3 | Chargeback analytics live; RIS-SL-40/41 sustained | RIS-SL-40/41 | R2-06-04/05/12 |
| D4 | Pre-registration visible at check-in; one-click completion | RIS-UI-23 | R2-06-06/07 |
| D5 | Perf + security suites green; evidence package; cutover rehearsed | RIS-SL-61 | R2-06-08/09/14/15 |
| D6 | RVG-5…RVG-6 green; UAT sign-off (4 personas); 0 P0/P1 | release-plan V2 §2 | R2-06-10…16 |
| D7 | Engineering DoD: `tsc --noEmit` + `vite build` clean; unit tests green | release-plan V2 §6 | CI gate |

---

## 6. Risks & Watch Items (Sprint R2-06)

| Risk | Watch indicator | Mitigation |
| :--- | :--- | :--- |
| AI coding acceptance < 90% | PRD §3 pilot | Pilot gates rollout; audited suggestions; remediation plan (tuning, alternative vendors) |
| Chargeback data drift | RIS-SL-40/41 | Capture at booking (R2-03-08); daily reconcile; by-site dashboard |
| Portal pre-reg PHI exposure | RIS-SL-60 | Consent + release policy; no PHI in URLs; audit every access |
| UAT finding volume exceeds fix capacity | Daily triage P0/P1 | Feature freeze; P0/P1 only; P2/P3 → V3 backlog |
| Gate regression after fixes | RVG re-runs | Every fix triggers full-suite rerun; regression window in slack |

---

## Traceability

| Source work item | Tasks |
| :--- | :--- |
| E-RIS2-10 (AI-assisted coding) | R2-06-01…03, R2-06-11 |
| E-RIS2-11 (chargeback analytics) | R2-06-04/05 |
| E-RIS2-12 (pre-registration) | R2-06-06/07 |
| Performance + security test | R2-06-08/09 |
| RVG-5…RVG-6 + go/no-go | R2-06-10…16 |
