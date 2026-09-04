# Sprint R2-01 Detail — Prior-Auth Engine (E-RIS2-01) & Appointment Reminders (E-RIS2-02)

**Version:** 1.0 · **Date:** 2026-08-05 · **Source:** `requrements/RIS/RELEASE_PLAN_V2.md` E-RIS2-01, E-RIS2-02, §2 gates RVG-1/RVG-2; `requrements/RIS/03_user_stories.md` RIS-US-P03-02/03; `requrements/RIS/06_acceptance_criteria.md` RIS-AC-P03-02/03; `requrements/RIS/05_metrics_and_slas.md` RIS-SL-36; `RBAC_matrix_spec.md` §8 (`PRIOR_AUTH_*`)
**Cadence:** two 2-week sprints (R2-S1–R2-S2) · **Squads:** RIS-V2 — two backend, one frontend, part-time integration engineer (payer/portal), QA · **Format parity:** `requrements/sprint_v2_01_advanced_viewer_priors_detail.md` … `sprint_v2_07_tenant_hatch_patient_ai_detail.md`
> **Sprint numbering:** this is sprint detail **R2-01** of the RIS V2 delivery sequence = release-plan roadmap **R2-S1–R2-S2** (Phase 1, v1.1). Merged because the prior-auth engine feeds the scheduling rules that reminders ride on, and both are scheduler-domain revenue/no-show epics.

---

## 1. Sprint Goal

> **"Orders that need prior authorization are tracked, verified, and enforced at booking — with ≥ 95% of required exams authorized before the scan — while appointment reminders on configured channels (with opt-out honored) reduce no-shows, all fully logged and audited."**

**Scope in (R2-S1):** prior-auth status model + payer integration, booking block + audited override, expiry alerts. **Scope in (R2-S2):** claim linkage + dashboard, reminder configuration + providers, opt-out registry, send logging.

**Scope out (later R2 sprints):** denial rework + unbilled dashboards (R2-02), template manager + SR polish (R2-02), IDN grants + multi-site scheduling (R2-03), FHIR read + v1.1 gates (R2-04).

**Prior program handoff (required to start):** order model + accession (E-RIS-04), scheduling resource model + conflict checks (E-RIS-05), eligibility stub → provider API (E-RIS-03 #5), notification subsystem (S1-25), interface engine + exception queue (S2-21/22), RBAC `PRIOR_AUTH_READ/WRITE` seed (matrix §8).

---

## 2. Team Capacity (two 10-day sprints)

| Role | FTE | Available dev-days (×2) | Notes |
| :--- | :-: | :-: | :--- |
| Backend engineer ×2 | 2.0 | 40 | Prior-auth model/APIs, booking rule, reminder send + logging |
| Frontend engineer ×1 | 1.0 | 20 | Prior-auth panel (RIS-UI-16), reminder config (RIS-UI-17), dashboard |
| Integration engineer | 0.5 | 10 | Payer API conformance, SMS/email/phone providers |
| QA | 0.5 | 10 | RVG-1/RVG-2 pre-checks, E2E |
| **Total** | **4.0** | **~80** | Total task estimate below: **~27 dev-days** (BE 10.0 · FE 8.5 · INT 4.5 · QA 4.0) — ~53 days slack, absorbed per note below |

> **Slack absorption (not committed):** (a) extra payer-API variance corpus; (b) reminder A/B templates; (c) forward-pull of **E-RIS2-03 #1** (denial intake scaffold) if the 835 pattern is proven; (d) UI polish for the prior-auth panel. Nothing past E-RIS2-01/E-RIS2-02 scope is committed.

---

## 3. Task Board (grouped by source work item)

> Estimates in dev-days. `Owner:` BE = backend, FE = frontend, INT = integration engineer, QA = test. `Check:` acceptance check (maps to AC/SL/UI/RBAC IDs where applicable).

### 3.1 Prior-auth status model — E-RIS2-01 #1/2
**Source:** RIS-AC-P03-03; RIS-UI-16; `RBAC_matrix_spec.md` §8.

| ID | Task | Owner | Est. | Dep | Acceptance check |
| :-: | :--- | :-: | :-: | :-: | :--- |
| R2-01-01 | `prior_auth_requests` schema: status enum (NOT_REQUIRED/REQUIRED/PENDING/APPROVED/DENIED/EXPIRED), order/procedure/CPT linkage, payer ref | BE | 2.0 | E-RIS-04 | RIS-AC-P03-03: order flag + claim link |
| R2-01-02 | Prior-auth APIs: create/query/update status + expiry; `PRIOR_AUTH_READ/WRITE` enforcement | BE | 1.5 | R2-01-01 | Endpoint→permission map (§7) verified |
| R2-01-03 | Prior-auth panel UI: status, expiry, CPT linkage; expired/none → warning badge + blocked booking (RIS-UI-16) | FE | 2.5 | R2-01-02 | RIS-UI-16 parity |
| R2-01-04 | Live payer/eligibility integration (extend E-RIS-03 #5 stub) + manual fallback | INT | 3.0 | E-RIS-03 #5 | RIS-AC-P04-02 (v2 live); fallback path |

**Epic exit contribution:** E-RIS2-01 #1/2 (status + payer — RVG-1).

### 3.2 Booking rule & alerts — E-RIS2-01 #3/4
**Source:** RIS-AC-P03-03 (blocked + override + expiry cases); RIS-WF3.

| ID | Task | Owner | Est. | Dep | Acceptance check |
| :-: | :--- | :-: | :-: | :-: | :--- |
| R2-01-05 | Scheduling rule: missing/denied/expired auth blocks booking; **audited override** with reason (extends E-RIS-05 conflict checks) | BE | 2.0 | R2-01-01, E-RIS-05 | RIS-AC-P03-03 (block + override, audited) |
| R2-01-06 | Override UX: reason capture + confirm; override logged with actor/order/reason | FE | 1.5 | R2-01-05 | RIS-SL-60: override audit rows |
| R2-01-07 | Expiry alerts: ≤ 7 days before expiry → scheduler alert (notification subsystem) | BE | 1.0 | S1-25 | RIS-AC-P03-03 (alert case) |

**Epic exit contribution:** E-RIS2-01 #3/4 (rule + alerts — RVG-1).

### 3.3 Claim linkage & dashboard — E-RIS2-01 #5/6
**Source:** RIS-UI-33; RIS-P07.

| ID | Task | Owner | Est. | Dep | Acceptance check |
| :-: | :--- | :-: | :-: | :-: | :--- |
| R2-01-08 | Prior-auth linkage on claim line (billing view); missing auth highlighted (RIS-UI-33) | BE | 1.0 | R2-01-01 | RIS-UI-33 parity |
| R2-01-09 | Prior-auth dashboard: status mix, aging, denial reasons (manager view) | FE | 2.0 | R2-01-02 | RIS-P07 dashboard parity |

**Epic exit contribution:** E-RIS2-01 #5/6 (linkage + dashboard).

### 3.4 Reminders — E-RIS2-02 #1/2/3
**Source:** RIS-AC-P03-02; RIS-UI-17; RIS-M05.

| ID | Task | Owner | Est. | Dep | Acceptance check |
| :-: | :--- | :-: | :-: | :-: | :--- |
| R2-01-10 | Reminder config UI: per-order channel (SMS/email/phone), time, template (RIS-UI-17) | FE | 2.5 | E-RIS-05 | RIS-AC-P03-02 config case |
| R2-01-11 | Provider integrations (SMS/email/phone) with retry + exception queue | INT | 1.5 | S2-21/22 | 0 silent send failures |
| R2-01-12 | Opt-out registry honored across channels + templates | BE | 1.5 | R2-01-10 | RIS-AC-P03-02: opt-out honored |
| R2-01-13 | Send/receipt logging + ≤ 5-min failure alerting; no-show feed | BE | 1.0 | R2-01-11 | Every send logged (RIS-SL-60) |

**Epic exit contribution:** E-RIS2-02 (reminders — RVG-2).

### 3.5 Cross-cutting: E2E & gates
**Source:** RVG-1/RVG-2 pre-checks; RIS-SL-36.

| ID | Task | Owner | Est. | Dep | Acceptance check |
| :-: | :--- | :-: | :-: | :-: | :--- |
| R2-01-14 | E2E: order flagged → auth approved → book → expiry alert → override → reminder → opt-out | QA | 2.0 | R2-01-01…13 | RIS-AC-P03-02/03 pass; RVG-1/RVG-2 pre-checks |
| R2-01-15 | Prior-auth ≥ 95% pre-scan instrumentation (RIS-SL-36) + audit completeness | QA | 2.0 | R2-01-09 | RIS-SL-36 metric measurable |

---

## 4. Sprint Milestones

| Milestone | Target | Evidence |
| :--- | :--- | :--- |
| **Day 3** | Prior-auth schema + APIs scaffold; booking-rule design; payer sandbox wired | R2-01-01/02, R2-01-05, R2-01-04 started |
| **Day 5 (R2-S1)** | Booking block + override live; expiry alerts; reminder config scaffold | R2-01-03/05/06/07, R2-01-10 closed |
| **Day 8 (R2-S2)** | Claim linkage + dashboard; providers + opt-out + logging | R2-01-08/09, R2-01-11…13 closed |
| **Day 10 (R2-S2, demo)** | E2E green; demo: order → auth → book → reminder → opt-out; RIS-SL-36 metric | R2-01-14/15; RVG-1/RVG-2 pre-checks; sprint review |

---

## 5. Sprint Definition of Done (acceptance checks)

| # | Check | Verifies | Method |
| :-: | :--- | :--- | :--- |
| D1 | Prior-auth status tracked per order; booking blocked on missing/denied with audited override | RIS-AC-P03-03 | R2-01-01…06 tests |
| D2 | Payer integration live with fallback; expiry alerts ≤ 7 days | RIS-AC-P04-02 (v2), RIS-AC-P03-03 | R2-01-04/07 |
| D3 | Reminders configurable, opt-out honored, every send logged | RIS-AC-P03-02, RIS-SL-60 | R2-01-10…13 |
| D4 | RIS-SL-36 (≥ 95% pre-scan) instrumented; RVG-1/RVG-2 pre-checks green | RIS-SL-36 | R2-01-14/15 |
| D5 | Engineering DoD: `tsc --noEmit` + `vite build` clean; unit tests green; migrations reviewed | release-plan V2 §6 | CI gate |
| D6 | No P0/P1 open defects at sprint close | release-plan V2 §6 | Defect triage |

---

## 6. Risks & Watch Items (Sprint R2-01)

| Risk | Watch indicator | Mitigation |
| :--- | :--- | :--- |
| Payer API variance (auth statuses, latency) | RIS-SL-36 | Provider API + manual fallback; conformance corpus; booking block + audited override |
| Reminder provider reliability | Send failure rate | Retry + exception queue; ≤ 5-min alerting; provider redundancy |
| Override abuse (booking denied exams) | Override audit rate | Mandatory reason + audit; dashboard anomaly view (R2-01-09) |
| Scope creep into billing/denial domain | Non-goals | Denial rework is R2-02; prior-auth linkage only here |

---

## Traceability

| Source work item | Tasks |
| :--- | :--- |
| E-RIS2-01 #1 (status model) | R2-01-01…03 |
| E-RIS2-01 #2 (payer integration) | R2-01-04 |
| E-RIS2-01 #3 (booking rule) | R2-01-05/06 |
| E-RIS2-01 #4 (expiry alerts) | R2-01-07 |
| E-RIS2-01 #5 (claim linkage) | R2-01-08 |
| E-RIS2-01 #6 (dashboard) | R2-01-09 |
| E-RIS2-02 #1/2/3 (reminders) | R2-01-10…13 |
| RVG-1/RVG-2 pre-checks + E2E | R2-01-14/15 |
