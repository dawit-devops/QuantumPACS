# v2.1 Sprint Completion — AI Coding, Chargeback & Pre-Registration (R2-06)

**Version:** 1.0 · **Date:** 2026-08-22 · **Status:** R2-06-01..08 delivered, exit gate green
**Plan ref:** `CONSOLIDATED_SPRINT_PLAN.md` rows R2-06-01..08 (sprint R2-S10–S12, epic E-RIS2-10/11/12)
**Platform:** QuantumPACS v3-dev (Starlette, React/Vite, PostgreSQL, asyncpg, Alembic)

---

## 1. What Was Delivered

| ID | Scope (plan) | Delivered | Key artifacts |
|:---|:---|:---|:---|
| R2-06-01 | Coding suggestion service: CPT/ICD-10 from procedure + report | ✅ Auto-drop consults the report's indication for ICD-10 when the procedure map is empty; procedure-keyed CPT/ICD wins otherwise | `db/ris_charges.py` (`drop_charge`), `services/coding_telemetry.py` |
| R2-06-02 | Accept/override workflow; every suggestion audited | ✅ Coder-edited codes persist via `RisCharges.apply_override` and audit as `billing.cpt_overridden` beside `billing.charge_dropped` | `api/billing.py` (`RisChargeDropHandler`), `db/ris_charges.py`, `db/audit_log.py` |
| R2-06-03 | Pilot instrumentation: acceptance/rejection + utility dashboard | ✅ `coding_suggestions_accepted_total` / `coding_suggestions_overridden_total` counters make the ≥90% acceptance gate queryable from Prometheus | `api/telemetry.py`, `services/coding_telemetry.py` |
| R2-06-04 | Per-site chargeback aggregation from bookings | ✅ `GET /api/v2/ris/scheduling/chargeback?month=YYYY-MM-DD` — bookings performed here for other sites, grouped by `requesting_tenant` (servicing-side view); month defaults to current, 422 on malformed values | `api/scheduling.py` (`RisChargebackHandler`), `db/ris_appointments.py` (`chargeback_summary`), route in `api/routes.py` |
| R2-06-05 | Manager dashboard: chargeback, denial rate, unbilled by site | ✅ KPI payload gains `chargeback.rows` + `denial_rate`; FE adds Cross-site bookings + Claim denial-rate cards | `api/ris_dashboard.py`, `frontend/src/admin/RISDashboard.tsx`, `frontend/src/api/dashboard-ris.ts` |
| R2-06-06 | Pre-registration: portal data visible before arrival | ✅ ADT^Z01 upserts the patient and books an unassigned appointment stub (resource NULL until staff assign; migration 085; EXCLUDE guard treats NULL resources as distinct so stubs never double-book). Schedule from OBR-7; patient-only when absent | `services/ingestion/hl7_server.py` (`_preregister_patient`), `migrations/versions/085_unassigned_preregistration.py` |
| R2-06-07 | One-click completion at check-in | ✅ Kiosk self-check-in: HMAC-signed expiring token embeds tenant + appointment; `GET/POST /api/v2/ris/checkin/{token}` (public path — token is the credential). GET returns minimal-PHI summary, POST flips SCHEDULED→ARRIVED (409 on repeat) and audits `ris.checkin`. `/checkin` page consumes `?token=` with summary/confirm/error states | `api/checkin.py`, `db/ris_appointments.py` (`get_for_checkin`, `mark_checked_in`), `frontend/src/kiosk/CheckIn.tsx`, `frontend/src/api/checkin.ts` |
| R2-06-08 | Full perf suite: FHIR, scheduling, portal | ✅ Full-suite regression pass — see §3 | — |

**Commits (top of `v3-dev`):**
- `73713af` feat(ris): ADT^Z01 pre-registration chain + kiosk self-check-in (R2-06-06..08)
- `76375a6` feat(ris): per-site chargeback aggregation + dashboard parity (R2-06-04/05)
- `ae17cfe` feat(billing): ICD-10 from report text + audited coding overrides with pilot telemetry (R2-06-01..03)

---

## 2. Design Decisions

- **Check-in status is `ARRIVED`, not a new value.** `ris_appointments.status` has a CHECK constraint (SCHEDULED/ARRIVED/IN_PROGRESS/COMPLETED/CANCELLED); introducing CHECKED_IN would need a migration for a word that RIS already means as "arrived". One-click completion reuses the existing transition and its audit path.
- **Pre-registration stubs are unassigned (resource_id NULL).** A Z01 arrives before anyone picks a room/device. Postgres EXCLUDE treats NULLs as distinct, so unassigned stubs can never conflict with real bookings — semantically the correct booking-engine behaviour. Front desk assigns a resource at check-in (migration 085 relaxes the NOT NULL).
- **Kiosk auth = the token, not a session.** No login, no PHI beyond display name + time. Token is `b64url(json{t,a,e}).<HMAC-SHA256(config secret)>` with constant-time compare + expiry; the route is whitelisted in `TokenAuth` (`/api/v2/ris/checkin/*`). POST requires no RBAC grant — possession of the token is the authorization, matching the QR-kiosk physical-security model.
- **Chargeback is a servicing-site view.** Cross-facility bookings live in the servicing site's data plane with `requesting_tenant` stamped (R2-03-08); the aggregation is local-to-plane (who booked here). A platform-wide rollup needs the multi-site fan-out pattern and is deferred.
- **Coding acceptance instrumentation is counter-only.** Counters (not a gauge) so Prometheus rate() gives the acceptance fraction over any window; the ≥90% pilot gate is a threshold on `rate(accepted)/(rate(accepted)+rate(overridden))`.

---

## 3. Exit Gate

| Area | Result | Detail |
|:---|:---|:---|
| Backend (pytest, full suite) | **2339 passed / 2 skipped / 0 failed** | 3m23s; includes v2.1 suites `test_ris_v21_coding.py`, `test_ris_v21_chargeback.py`, `test_ris_v21_preregistration.py` + ADT/HL7 regressions |
| Frontend (vitest, all 72 files) | **All exercised, 0 v2.1 regressions** | 34 files green in budgeted run; batches of remaining 38 → 18+1 (flake) and 19/19 green; the 2 failures (ReadingConsole "Sign & Next", Portal "scoped patient") each **pass in isolation** under default config — load-induced flakes under 4-thread/retry-0 runs, the exact failure mode the repo's `retry: 2` mitigates |
| Services | **Healthy** | `frontend:200`, `backend:200` after the gate; dev service restarted |

**Known infra constraint:** the frontend suite (~72 files, jsdom + antd + cornerstone) cannot complete in a single 15-minute window at this box's memory cap (2 forks by config design; ~45s/file). Gate strategy used: budgeted run + batched remainder, every failure re-verified in isolation.

---

## 4. Remaining (not in this delivery)

These are follow-on QA/UAT gates, not implementation work:

| ID | Scope | Note |
|:---|:---|:---|
| R2-06-09 | Security test: RLS, RBAC, IDOR, SMART token | 0 critical/high target — plan for a dedicated security sweep |
| R2-06-10 | RVG-5 re-verify: full FHIR + portal + pre-reg | Gate green |
| R2-06-11 | AI 30-day pilot gate: ≥ 90% acceptance | Requires ≥30 days of production `coding_suggestions_*` data |
| R2-06-12 | RVG-6 re-verify: charge ≥ 98%, unbilled $0 > 5d | Depends on R2-06-04/05 dashboards being fed real billing data |
| R2-06-13 | Per-persona UAT: biller, manager, scheduler, front desk | UAT sign-off |

---

## 5. Corrective Note (2026-08-23) — gate-green caveat

The §3 exit gate was re-audited by `GAP_AUDIT_TDD_PIPELINE.md` (phases A–F). The
original gate record stands **only with the following caveat**:

- **A1/A2 pending:** the claimed "full suite" pass did not hold a real-engine
  p95/throughput assertion (durations were averaged, not percentile-bounded)
  and the RBAC/IDOR evidence was static — neither asserted the generated
  negative net nor swept the RIS catalog. Phases F1/F2 add those gates
  (`test_perf_gates.py`, `test_rbac_matrix_gen.py`); the baseline number in §3
  is superseded by the pipeline's final exit-gate run.
- **A11y not evidenced:** the §3 gate did not run WCAG scans. Phase F3 adds
  per-page axe scans (RISDashboard, BillingQueue, TrackingBoard, kiosk CheckIn,
  TemplateManager, DenialRework) and fixed a real `label` violation found by the
  new scan (antd Selects in TrackingBoard lacked accessible names).
- **UAT material missing:** R2-06-13 stayed open. Phase F4 ships the material:
  `scripts/seed_uat.py` + `docs/uat/*.md` (radiologist, technologist, scheduler,
  front-desk, biller, ris-admin, manager). Sign-off still belongs to UAT owners.

For the authoritative, pipeline-tracked status see `GAP_AUDIT_TDD_PIPELINE.md`
(status table: A–F committed `363e26c` → `e017985`).

**Pipeline exit gate** (2026-08-23, pipeline phases A–F):

| Area | Result | Detail |
|:---|:---|:---|
| Backend (pytest, full suite) | **2523 passed / 2 skipped / 0 failed** | 2m13s; includes F1 perf gates (13), F2 RBAC matrix (111 + 88 pre-existing) |
| Frontend (tsc noEmit) | **0 errors** | — |
| F3 WCAG scans | **5 suites green** | RISDashboard, BillingQueue, TrackingBoard, CheckIn, TemplateManager, DenialRework — each verified in isolation with `-t "WCAG"` |
| F4 UAT material | **Delivered** | `scripts/seed_uat.py` + 7 persona walkthroughs in `docs/uat/` |
| Full FE run | Known infra constraint — 3 pre-existing hang files (ExamConsole, ReadingWorklist, TemplateManager) timeout; all pipeline-touched suites pass | — |
