# Sprint MVP-07 Detail — Billing Capture + Auto Charge Drop (E-RIS-11)

**Version:** 1.0 · **Date:** 2026-08-18 · **Source:** `ris-integration-spec.md` §9.1; `RELEASE_PLAN.md` E-RIS-11; `02_end_to_end_workflows.md` RIS-WF6; `04_uiux_requirements.md` RIS-UI-30…33
**Cadence:** one 2-week sprint (S11) · **Squads:** RIS-MVP — two backend, one frontend, part-time integration engineer, QA

---

## 1. Sprint Goal

> **"A signed report automatically generates a billable charge with CPT/ICD-10 suggested from the procedure and report; the billing coder confirms and drops the charge; unbilled aging is visible daily; and charge capture ≥ 98% with $0 actionable > 5 business days."**

**Scope in:** CPT/ICD-10 suggestion from procedure + signed report, auto charge drop on sign-off (replacing S5-13 stub), billing queue (signed-but-unbilled), unbilled aging view (daily reconcile), 837/835 export/import stub.

**Scope out:** Denial rework (v1.1), AI-assisted coding (v2.0).

---

## 2. Team Capacity (one 10-day sprint)

| Role | FTE | Available dev-days | Notes |
| :--- | :-: | :-: | :--- |
| Backend engineer ×2 | 2.0 | 20 | Auto charge drop, CPT suggestion engine, unbilled aging API, 837/835 stub |
| Frontend engineer ×1 | 1.0 | 10 | Billing queue UI, unbilled aging dashboard, CPT suggestion display |
| Integration engineer | 0.5 | 5 | 837/835 format validation, CPT/ICD-10 mapping conformance |
| QA | 1.0 | 10 | Billing E2E, charge capture rate, unbilled aging, RLS |
| **Total** | **4.5** | **~45** | Total task estimate below: **~28 dev-days** (BE 10.0 · FE 6.0 · INT 3.0 · QA 7.0) — ~17 days slack |

---

## 3. Task Board

### 3.1 CPT/ICD-10 Suggestion + Auto Charge Drop — E-RIS-11 #1/2
**Source:** `RELEASE_PLAN.md` E-RIS-11 #1/2; `ris-integration-spec.md` §3.2 Migration 4; `06_acceptance_criteria.md` RIS-AC-P05-01/03.

| ID | Task | Owner | Est. | Dep | Acceptance check |
| :-: | :--- | :-: | :-: | :-: | :--- |
| S7-01 | `ris_charges` table + Alembic migration (Migration 4 from spec §3.2); CPT code, description, ICD-10, amount, status, prior_auth linkage | BE | 1.0 | — | Table created |
| S7-02 | CPT/ICD-10 suggestion engine: map order procedure_code → CPT code (from `procedure_pricing_catalog`); suggest ICD-10 from clinical_indication; confidence score | BE | 2.0 | S7-01 | RIS-AC-P05-01; coding accuracy ≥ 95% (RIS-SL-43) |
| S7-03 | Auto charge drop: on report sign-off (replacing S5-13 stub), create `ris_charges` row with suggested CPT/ICD-10; status=PENDING; audit event | BE | 2.0 | S5-11, S7-02 | RIS-AC-P05-03; charge capture ≥ 98% (RIS-SL-40) |
| S7-04 | Billing queue API: `GET /api/ris/billing/queue` — signed-but-unbilled exams with suggested CPT/ICD-10; coder confirms/adjusts | BE | 1.5 | S7-03 | RIS-UI-30 parity |
| S7-05 | Charge drop API: `POST /api/ris/billing/charges/{id}/drop` — coder confirms charge; status → BILLED; audit logged | BE | 1.0 | S7-04 | Charge dropped; audited |
| S7-06 | CPT suggestions API: `GET /api/ris/billing/cpt-suggestions` — suggestions from procedure + report content; coder can override | BE | 0.5 | S7-02 | Suggestions returned; override works |

**Epic exit contribution:** E-RIS-11 #1/2 (CPT suggestion + auto charge drop).

### 3.2 Unbilled Aging — E-RIS-11 #3
**Source:** `RELEASE_PLAN.md` E-RIS-11 #3; `05_metrics_and_slas.md` RIS-SL-41; `04_uiux_requirements.md` RIS-UI-31.

| ID | Task | Owner | Est. | Dep | Acceptance check |
| :-: | :--- | :-: | :-: | :-: | :--- |
| S7-07 | Unbilled aging API: `GET /api/ris/billing/unbilled` — unbilled charges grouped by date/site/payer; aging buckets (0-5 days, 5-10, 10+); daily reconcile | BE | 2.0 | S7-03 | RIS-SL-41; $0 actionable > 5 days |
| S7-08 | Unbilled aging dashboard UI: extend existing `frontend/src/billing/` — unbilled aging chart with drill-down by date, site, payer; daily reconcile indicator | FE | 3.0 | S7-07 | RIS-UI-31 parity; WCAG 2.1 AA |

**Epic exit contribution:** E-RIS-11 #3 (unbilled aging).

### 3.3 837/835 Export/Import Stub — E-RIS-11 #4
**Source:** `RELEASE_PLAN.md` E-RIS-11 #4 (D item).

| ID | Task | Owner | Est. | Dep | Acceptance check |
| :-: | :--- | :-: | :-: | :-: | :--- |
| S7-09 | 837 export stub: `ris_charges` (status=BILLED) → mock X12 837 claim file; real 837 in v1.1; for now, generate JSON representation | INT | 1.5 | S7-05 | Claim file generated (JSON); format validated |
| S7-10 | 835 import stub: mock 835 denial response → `ris_claims` row with rejection_code/reason; real 835 in v1.1 | INT | 1.0 | S7-09 | Denial record created; S11-ready |

**Epic exit contribution:** E-RIS-11 #4 (837/835 stubs).

### 3.4 Billing UI — E-RIS-11 #1/2
**Source:** `04_uiux_requirements.md` RIS-UI-30.

| ID | Task | Owner | Est. | Dep | Acceptance check |
| :-: | :--- | :-: | :-: | :-: | :--- |
| S7-11 | Billing queue UI: extend `frontend/src/billing/BillingQueue.tsx` — signed-but-unbilled exams with suggested CPT/ICD-10; coder confirms/adjusts; charge drop action | FE | 3.0 | S7-04 | RIS-UI-30 parity; WCAG 2.1 AA |

**Epic exit contribution:** E-RIS-11 billing UI.

### 3.5 Cross-cutting: E2E & Reconciliation

| ID | Task | Owner | Est. | Dep | Acceptance check |
| :-: | :--- | :-: | :-: | :-: | :--- |
| S7-12 | Billing E2E: sign report → auto charge drop → billing queue shows charge → coder confirms → CPT/ICD-10 correct → charge dropped → unbilled aging shows 0 for that exam | QA | 2.0 | S7-01…11 | RIS-AC-P05-01/03; RIS-SL-40 |
| S7-13 | Unbilled reconciliation: generate 20 signed exams → verify all have charges → verify unbilled aging shows correct counts → $0 actionable > 5 days | QA | 1.5 | S7-07 | RIS-SL-41 |
| S7-14 | Charge capture rate: verify ≥ 98% of signed exams have charges; daily reconciliation assertion | QA | 1.0 | S7-03 | RIS-SL-40 |
| S7-15 | RLS on charges: cross-facility charge reads denied | QA | 0.5 | S7-01 | PAC-SL-61 |

---

## 4. Sprint Milestones

| Milestone | Target | Evidence |
| :--- | :--- | :--- |
| **Day 3** | Charges table + CPT suggestion engine; auto charge drop | S7-01/02/03 started |
| **Day 5** | Billing queue API + UI; charge drop API; unbilled aging API | S7-04/05/07, S7-08, S7-11 started |
| **Day 8** | 837/835 stubs; unbilled aging dashboard; CPT suggestion display | S7-09/10, S7-08, S7-06 closed |
| **Day 10 (demo)** | Billing E2E green; reconciliation; demo: sign → charge → billing queue → confirm → unbilled aging | S7-12…15; sprint review |

---

## 5. Sprint Definition of Done

| # | Check | Verifies | Method |
| :-: | :--- | :--- | :--- |
| D1 | Auto charge drop on sign-off; charge capture ≥ 98%; RIS-SL-40 | RIS-AC-P05-03 | S7-12/14 |
| D2 | CPT/ICD-10 suggestion from procedure + report; coding accuracy ≥ 95%; RIS-SL-43 | RIS-AC-P05-01 | S7-12 |
| D3 | Unbilled aging $0 actionable > 5 days; daily reconcile; RIS-SL-41 | RIS-SL-41 | S7-13 |
| D4 | Billing queue UI: coder confirms/adjusts; charge drop action | RIS-UI-30 | S7-12 |
| D5 | Engineering DoD: `tsc --noEmit` + `vite build` clean; unit tests green; migrations reviewed | release-plan §6 | CI gate |
| D6 | No P0/P1 open defects | release-plan §6 | Defect triage |

---

## 6. Risks & Watch Items

| Risk | Watch indicator | Mitigation |
| :--- | :--- | :--- |
| CPT suggestion accuracy < 95% | S7-12 coding test | Procedure→CPT mapping from existing `procedure_pricing_catalog`; manual override always available |
| Auto charge drop misses (charge not created on sign-off) | S7-14 capture rate | Hook on report sign event; daily reconciliation alerts on any gap |
| 837 format complexity (real X12 vs. stub) | S7-09 | JSON stub in MVP; real X12 encoder in v1.1; format validated |
| Billing queue performance with high volume | S7-08 | Server-side pagination; date range filter; indexed on status + created_at |

---

## Traceability

| Source work item | Tasks |
| :--- | :--- |
| E-RIS-11 #1 (CPT suggestion) | S7-02/06 |
| E-RIS-11 #2 (auto charge drop) | S7-03/05 |
| E-RIS-11 #3 (unbilled aging) | S7-07/08 |
| E-RIS-11 #4 (837/835 stubs) | S7-09/10 |
| Billing UI | S7-11 |
| Cross-cutting (billing E2E, reconciliation, capture rate, RLS) | S7-12…15 |
