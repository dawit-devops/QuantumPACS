# Sprint R2-04 Detail — FHIR Read APIs (E-RIS2-07) & Phase-1 Gates (RVG-1…RVG-4)

**Version:** 1.0 · **Date:** 2026-08-05 · **Source:** `requrements/RIS/RELEASE_PLAN_V2.md` E-RIS2-07, §2 gates RVG-1…RVG-4; `requrements/RIS/06_acceptance_criteria.md` RIS-AC-*; `requrements/RIS/05_metrics_and_slas.md` RIS-SL-36/41/60/61; `research/pacs-ris-viewer-integration-spec.md` §4–§6
**Cadence:** one 2-week sprint (R2-S7) · **Squads:** RIS-V2 — two backend, one frontend, part-time integration engineer (FHIR conformance), QA · **Format parity:** `requrements/sprint_r2_01_prior_auth_reminders_detail.md` … `sprint_r2_03_idn_grants_scheduling_detail.md`
> **Sprint numbering:** this is sprint detail **R2-04** of the RIS V2 delivery sequence = release-plan roadmap **R2-S7** — the **Phase-1 (v1.1) capstone**: it completes the FHIR read API surface and executes the **RVG-1…RVG-4** exit gates with per-persona UAT and the Phase-1 evidence package.

---

## 1. Sprint Goal

> **"The v1.1 backlog is declared releasable: FHIR read APIs serve Patient/ServiceRequest/DiagnosticReport/ImagingStudy with RLS enforcement; and every RVG-1…RVG-4 gate passes — prior-auth ≥ 95% pre-scan, unbilled $0 > 5 days, IDN grants live with 0 cross-tenant writes, FHIR conformance green — with per-persona UAT sign-off."**

**Scope in:** FHIR read API surface (search + pagination + RLS), FHIR conformance harness + version pinning, RVG-1…RVG-4 re-verification, per-persona UAT (scheduler, biller, RIS admin, radiologist), Phase-1 evidence package + go/no-go.

**Scope out (Phase 2, later R2 sprints):** full FHIR read/write (R2-05), portal delivery (R2-05), AI-assisted coding + chargeback analytics + pre-registration + v2.0 gates (R2-06).

**Prior program handoff (required to start):** prior-auth + reminders (R2-01), denial + templates + SR polish (R2-02), IDN grants + multi-site scheduling (R2-03), MVP read-only FHIR endpoints (E-RIS-02 #5), RLS + audit foundations (S1-14).

---

## 2. Team Capacity (one 10-day sprint)

| Role | FTE | Available dev-days | Notes |
| :--- | :-: | :-: | :--- |
| Backend engineer ×2 | 2.0 | 20 | FHIR read surface + RLS |
| Frontend engineer ×1 | 1.0 | 10 | UAT fixes, gate evidence touches |
| Integration engineer | 0.5 | 5 | FHIR conformance harness |
| QA | 1.0 | 10 | RVG-1…RVG-4 gates + UAT |
| **Total** | **4.5** | **~45** | Total task estimate below: **~16 dev-days** (BE 5.0 · INT 3.0 · QA 8.0) — ~29 days slack, absorbed per note below |

> **Slack absorption (not committed):** (a) gate rework + full-suite regression reruns after every fix; (b) extra FHIR search-param coverage; (c) forward-pull of **E-RIS2-08 #1** (FHIR write scaffold). No new features enter the capstone without RVG-4 change control.

---

## 3. Task Board (grouped by source work item)

> Estimates in dev-days. `Owner:` BE = backend, FE = frontend, INT = integration engineer, QA = test. `Check:` acceptance check.

### 3.1 FHIR read surface — E-RIS2-07 #1/2
**Source:** `pacs-ris-viewer-integration-spec.md` §4; FHIR R4.

| ID | Task | Owner | Est. | Dep | Acceptance check |
| :-: | :--- | :-: | :-: | :-: | :--- |
| R2-04-01 | FHIR read API: `Patient`/`ServiceRequest`/`DiagnosticReport`/`ImagingStudy` + search params + pagination (extend E-RIS-02 #5) | BE | 3.0 | E-RIS-02 #5 | Conformance smoke tests |
| R2-04-02 | RLS enforcement on all FHIR routes; cross-facility read → denied + logged | BE | 2.0 | R2-04-01 | RIS-SL-61; `cross_tenant.denied` |
| R2-04-03 | FHIR conformance harness + version pinning (CI gate) | INT | 3.0 | R2-04-01 | Suite green; drift caught |

**Epic exit contribution:** E-RIS2-07 (FHIR read — RVG-4).

### 3.2 Phase-1 gates & UAT — RVG-1…RVG-4
**Source:** release-plan V2 §2 (RVG-1…RVG-4); RIS-AC-*; RIS-SL-*.

| ID | Task | Owner | Est. | Dep | Acceptance check |
| :-: | :--- | :-: | :-: | :-: | :--- |
| R2-04-04 | RVG-1 re-verify: prior-auth ≥ 95% pre-scan (RIS-SL-36); booking block + override; expiry alerts | QA | 2.0 | R2-01 closure | Gate green |
| R2-04-05 | RVG-2 re-verify: denial rework + unbilled $0 > 5 days (RIS-SL-41); reminders opt-out; templates rollback | QA | 1.5 | R2-02 closure | Gate green |
| R2-04-06 | RVG-3 re-verify: IDN grants + multi-site; 0 cross-tenant writes; 100% audited | QA | 1.5 | R2-03 closure | Gate green; CTG-AC-01…07 |
| R2-04-07 | Per-persona UAT + sign-off: scheduler, biller, RIS admin, radiologist (SR) | QA | 2.0 | R2-04-04…06 | RVG-4: UAT sign-off; 0 P0/P1 |
| R2-04-08 | Phase-1 evidence package: RVG-1…RVG-4 report with AC/SL traceability + audit completeness (RIS-SL-60/61) + go/no-go | QA | 1.0 | R2-04-07 | Package complete; Phase-1 cutover ready |

---

## 4. Sprint Milestones

| Milestone | Target | Evidence |
| :--- | :--- | :--- |
| **Day 3** | FHIR read surface scaffold; conformance harness started | R2-04-01/03 started |
| **Day 5** | FHIR read + RLS live; harness green | R2-04-01…03 closed |
| **Day 8** | RVG-1…RVG-4 re-verification complete | R2-04-04…06 closed |
| **Day 10 (go/no-go)** | UAT sign-off; Phase-1 evidence package; v1.1 releasable | R2-04-07/08; RVG-1…RVG-4; Phase-1 go/no-go; sprint review |

---

## 5. Sprint Definition of Done (acceptance checks)

| # | Check | Verifies | Method |
| :-: | :--- | :--- | :--- |
| D1 | FHIR read conformance green; RLS isolation intact | E-RIS2-07, RIS-SL-61 | R2-04-01…03 |
| D2 | RVG-1…RVG-4 green; UAT sign-off (4 personas); 0 P0/P1 | release-plan V2 §2 | R2-04-04…07 |
| D3 | Phase-1 evidence package + go/no-go recorded | RIS-SL-60/61 | R2-04-08 |
| D4 | Engineering DoD: `tsc --noEmit` + `vite build` clean; unit tests green | release-plan V2 §6 | CI gate |
| D5 | No P0/P1 open defects; Phase-1 releasable | release-plan V2 §6 | Defect triage |

---

## 6. Risks & Watch Items (Sprint R2-04)

| Risk | Watch indicator | Mitigation |
| :--- | :--- | :--- |
| Gate regression after fixes | RVG-1…RVG-4 | Feature freeze; every fix triggers full-suite rerun (R2-04-07); regression window in slack |
| FHIR version/search drift | R2-04-03 suite | Version pinning + public test servers; CI conformance gate |
| UAT finding volume exceeds fix capacity | Daily triage P0/P1 | P0/P1 only; P2/P3 → v2.0/backlog |
| Go/no-go scope creep ("one more feature") | VG evidence drift | Evidence package is the contract; changes after sign-off → Phase-2 |

---

## Traceability

| Source work item | Tasks |
| :--- | :--- |
| E-RIS2-07 #1 (FHIR read surface) | R2-04-01 |
| E-RIS2-07 #2 (RLS enforcement) | R2-04-02 |
| E-RIS2-07 #3 (conformance harness) | R2-04-03 |
| RVG-1/RVG-2/RVG-3 re-verification | R2-04-04…06 |
| RVG-4 UAT + evidence package | R2-04-07/08 |
