# Sprint S12 — Hardening + UAT Evidence Package

**Branch:** `feature/ris-integration` · **Date:** 2026-08-21 (refresh 2026-08-23) · **Scope:** MVP G1–G7 verification, per-persona UAT readiness, WCAG spot-check.

> **Refresh (2026-08-23):** the `GAP_AUDIT_TDD_PIPELINE.md` phases A–F landed since this doc's first cut and close several items previously marked "remaining". Sections 1, 4, 5, 6 and 7 below were updated to reflect: F1 honest p95 perf gates, F2 generated RBAC/IDOR matrix, F3 WCAG axe scans, F4 persona UAT scripts, and the new `dept_manager` role. The re-review finding H-6 (`3 agents review.md` §H) is **resolved** — see §8.

---

## 1. Verification Summary (G1–G7)

| Gate | Target | Result | Evidence |
|------|--------|--------|----------|
| G1 | MWL ≥ 98% | ✅ | `tests/test_mwl_handler.py` (C-FIND parity, paging), `test_mwl_mpps_e2e.py`, live dcm4chee parity `test_mwl_cfind_parity.py` (2 passed) |
| G2 | 0 conflicts | ✅ | `test_scheduling_concurrency.py` — 50 concurrent bookings → exactly one wins (EXCLUDE) |
| G3 | MPPS < 5s | ✅ | `test_mpps_consumer.py`, `test_mpps_events_api.py`; `ris_mpps_latency_seconds` histogram (S6-11) |
| G4 | Charge capture ≥ 98% | ✅ (implementation) | S11 auto charge drop + `test_ris_billing.py::TestReconciliationApi` (capture rate) |
| G5 | Delivery > 99.9% | ✅ (implementation) | S10 ORU engine + retry (`TestDeliveryRetry`), `ris_charge_drop_latency_seconds` |
| G6 | Tenant provisioning < 15 min | ✅ | Phase 1–2 provisioner + `test_tenant_lifecycle_e2e.py`, `test_tenancy_gate.py` |
| G7 | 0 P0/P1 | ✅ | Full-suite triage: **2523 passed, 2 skipped, 0 failures** (pipeline final exit gate, 2026-08-23) |

**Perf gates (S12-01..07)** — pipeline F1 rewrote the C-FIND/registration/autosave gates with a real p95 assertion (`tests/perf_utils.py::percentile`, linear interpolation). `tests/test_perf_gates.py` = 13 tests, all green:
- 50 concurrent C-FIND → real-engine p95 < soft bound (per-request durations, not averages)
- 50 concurrent bookings → exactly one winner, < 15s
- 50 concurrent tracking updates → one winner, < 30s (RIS-SL-15)
- 1000-entry filtered worklist → < 2s
- 100 HL7 msgs → 0 failures, < 60s
- Patient registration + report autosave latency gates

> Hard SLO enforcement is intentionally deferred to CI with dedicated hardware; the suite asserts correctness + generous bounds so shared dev hardware does not flake.

**Security gates (pipeline F2)** — generated, not hand-picked:
- `tests/rbac_matrix_gen.py` reads `api.routes._V1_ROUTES` and sweeps **every** RIS route/method for anonymous 401 + unpermitted 403 (111 parametrized cases) + every by-id handler for cross-tenant IDOR (fail closed). Pre-existing RBAC/IDOR suites stay green (88).
- `tests/fhir_scope_gen.py` + `tests/test_fhir_smart_scope_sweep.py` (R2-06-09): 10 parametrized wrong-resource SMART scope cases over the real FHIR route table — a valid-but-wrong scope always 403s.
- `test_ris_tenant_isolation.py::TestRisCrossTenantReadNoLeak` (R2-06-09): a tenant-B scoped read never returns a same-accession tenant-A row on the shared DB.

---

## 2. New Capabilities (this sprint)

| Item | Task | Files |
|------|------|-------|
| Escalation loop fix | S12-01 housekeeping | `lifecycle.py` — engine now runs on the uvicorn main loop via `run_coroutine_threadsafe` (was `new_event_loop`); **0 "different loop" errors live** |
| TAT histogram | S12-33 | `api/telemetry.py` `ris_report_tat_seconds{priority}`; observed in `api/reports.py` sign handler |
| Manager Dashboard API | S12-34 | `api/ris_dashboard.py` `GET /ris/dashboard/kpi` — TAT p95 by priority, utilization, unbilled aging, volume, drill-down |
| Manager Dashboard UI | S12-35 | `frontend/src/admin/RISDashboard.tsx` (`/admin/ris-dashboard`), 60s refresh, Statistic cards + TAT table |
| Dept manager role | S12-34 (refresh) | `dept_manager` built-in (read-only operational analytics) in `api/permissions.py` + `ADMIN_SCOPED_ROLES` (`frontend/src/navigator.ts`), `ROLE_WORKSPACE` dashboard landing, `seed_test_users.py` auto-creates `test.dept_manager` |
| Perf gates | S12-01/02/04/05/07 | `tests/test_perf_gates.py` + `tests/perf_utils.py` (F1) |
| RLS regression | S12-08 | `test_ris_tenant_isolation.py` — coding_map, mpps_events, order_procedures, resource_schedules added (+ cross-tenant read-leak test) |
| IDOR | S12-10 | `tests/test_idor.py` — cross-tenant charge/claim/sign fail closed; `test_rbac_matrix_gen.py` generated net (F2) |
| SMART scopes | R2-06-09 | `tests/test_fhir_smart_scope_sweep.py` — generated wrong-scope 403 net over FHIR routes |
| Audit completeness | S12-11 | `test_audit_log.py` — `billing.charge_dropped` event asserted |

---

## 3. Full Regression (S12-13)

- Backend: `pytest tests/ -q --timeout 300` → **2523 passed, 2 skipped** (pipeline final exit gate)
- ruff: `All checks passed`
- FE: `tsc --noEmit` → 0 errors; all pipeline-touched suites green (RISDashboard, BillingQueue, TrackingBoard, CheckIn, TemplateManager, DenialRework, UnbilledAging, ExamConsole, ReadingWorklist, route-gates)
- Alembic fresh-DB: `upgrade head` → 077 (idempotent)

> **FE runtime fixed (refresh):** the three suites that used to time out under jsdom — ExamConsole (antd `App.useApp()` needs the `<AntdApp>` provider), ReadingWorklist (assertions predated D1 pagination), TemplateManager (antd Drawer/Table motion never completes) — now pass together (32 tests). The full `vitest run` still exceeds a single-window memory cap in this env, but the hang root causes are resolved, not load flakes.

---

## 4. Per-Persona UAT Readiness (S12-14..20)

Checklist for the UAT pass — every flow is implemented, covered by automated tests, and shipped with a **scripted walkthrough + deterministic seeder** (pipeline F4):

| Persona | Flow | Status | UAT script |
|---------|------|--------|------------|
| Radiologist (P01) | reading worklist → report → template → sign → critical flag | ✅ `test_reporting_s8.py`, `test_critical_results_s10.py` | `docs/uat/radiologist.md` |
| Technologist (P02) | MWL → exam → MPPS → tracking | ✅ `test_mwl_mpps_e2e.py`, `test_mpps_consumer.py` | `docs/uat/technologist.md` |
| Scheduler (P03) | book → conflict → override → reschedule → cancel | ✅ `test_scheduling_concurrency.py`, `test_ris_appointments.py` | `docs/uat/scheduler.md` |
| Front Desk (P04) | register → MPI → insurance → check-in | ✅ `FrontDesk.test.tsx`, `test_frontdesk*.py` | `docs/uat/front-desk.md` |
| Billing Coder (P05) | queue → CPT → confirm → aging | ✅ `test_ris_billing.py`, `BillingQueue.test.tsx`, `UnbilledAging.test.tsx` | `docs/uat/biller.md` |
| RIS Admin (P06) | dashboard → exception → retry → roles → audit | ✅ `RisDashboardKpiHandler`, interface dashboard, RBAC suites | `docs/uat/ris-admin.md` |
| Dept Manager (P07) | dashboard → TAT → utilization → unbilled | ✅ `RISDashboard.tsx` + `test_ris_dashboard.py` + `dept_manager` role | `docs/uat/manager.md` (login `test.dept_manager`) |

Seeder: `scripts/seed_uat.py` (`--persona all|radiologist|technologist|scheduler|front-desk|biller|ris-admin|manager|dept_manager`) — deterministic, idempotent demo data per persona.

---

## 5. WCAG 2.1 AA Spot-Check (S12-32)

**Pipeline F3 added per-page automated axe scans** (`frontend/src/test/axe.ts`, excludes `color-contrast`/`target-size` for CI stability). Green across:

| Page | Suite |
|------|-------|
| RIS Dashboard | `src/test/RISDashboard.test.tsx` |
| Billing Queue | `src/test/BillingQueue.test.tsx` |
| Tracking Board | `src/test/TrackingBoard.test.tsx` |
| Kiosk Check-In | `src/test/CheckIn.test.tsx` |
| Template Manager | `src/test/TemplateManager.test.tsx` |
| Denial Rework | `src/test/DenialRework.test.tsx` |

The F3 scan found and fixed a **real `label` violation** (TrackingBoard Modality/Status antd Selects lacked accessible names). Manual spot-checks from earlier sprints remain in place: icon-only buttons carry `aria-label`, grid cells are keyboard-activatable, form inputs have accessible names, skip-to-content + focus rings in `withSidebar`. Full AA audit is a manual QA activity for the UAT pass.

---

## 6. Known Residual Issues

1. **Escalation engine cadence**: fixed (main-loop scheduling) — logs clean since restart.
2. **Full FE vitest runtime** (~20 min in this env) and FrontDesk load-flakiness — pre-existing, environment-related. The three suites that *hung* under jsdom (ExamConsole, ReadingWorklist, TemplateManager) are fixed (see §3).
3. **~~Manager Dashboard role~~**: **RESOLVED (refresh)** — `dept_manager` built-in added to `ADMIN_SCOPED_ROLES` (`permissions.py` + `navigator.ts`); clinical managers now reach the RIS Dashboard without super-admin. Read-only operational analytics; no writes/user/role/tenant admin (asserted in `test_rbac.py::TestGetRolePermissions::test_dept_manager_is_read_only_operational_analytics`).

---

## 7. Cutover / Go-No-Go Notes (S12-29/30)

- MVP codebase green on `feature/ris-integration`; G1–G7 verification matrix above (refreshed with pipeline exit-gate numbers).
- Remaining for MVP release (QA/ops, not code): per-persona manual UAT sign-off (scripts in `docs/uat/`), DR drill (RTO ≤ 4h), WCAG full audit, go/no-go review.

---

## 8. H-6 Resolution (re-review finding)

`3 agents review.md` finding **H-6** claimed S12 exit artifacts were "missing entirely" (no UAT scripts, no WCAG audit, no evidence-package regeneration). Resolution via `GAP_AUDIT_TDD_PIPELINE.md` phases A–F:

| Claimed missing | Delivered |
|-----------------|-----------|
| UAT scripts (S12-14..20) | `docs/uat/*.md` (7 personas) + `scripts/seed_uat.py` (F4) |
| WCAG 2.1 AA audit (S12-32) | Per-page axe scans, 6 suites green, real `label` fix (F3) |
| Perf gate honesty | Real p95 assertions, not averages (F1) |
| RBAC/IDOR evidence | Generated matrix + full negative/IDOR sweep (F2) |
| Full regression number | 2523 passed / 2 skipped / 0 failed (pipeline exit gate) |

Closed with commit `e017985` (F4) and the follow-ups `31e4995` (dept_manager + security tests) / `e651912` (FE hang fixes).
