# Sprint MVP-01 Detail — Auth, RBAC, Tenant Isolation & Audit (E-RIS-01)

**Version:** 1.0 · **Date:** 2026-08-18 · **Source:** `ris-integration-spec.md` §9.1; `RELEASE_PLAN.md` E-RIS-01; `01_persona_catalog.md`; `06_acceptance_criteria.md`
**Cadence:** two 2-week sprints (S1–S2) · **Squads:** Platform — two backend, one frontend, part-time integration engineer, QA
> **Sprint numbering:** MVP sprints **S1–S2**. Merged because platform foundation (auth + RBAC + tenant isolation + audit) is one continuous program; each component depends on the previous.

---

## 1. Sprint Goal

> **"Every RIS endpoint is behind a permission-gated JWT with facility-scoped RLS; every write is audit-logged; tenant provisioning completes atomically in < 15 min; and the foundation is green — all existing PACS tests still pass."**

**Scope in:** JWT auth + refresh rotation + rate limiting, RBAC seed (permissions, roles, role_permissions including RIS roles), tenant middleware (resolve facility, set `app.facility_id`, effective permissions), `provision_tenant()` wiring, audit pipeline (trigger-based `audit_log` + structured viewer), user/role management UI, metering hooks.

**Scope out (later sprints):** HL7 interface engine (S3), registration (S3), order intake (S4), scheduling (S5), MWL/MPPS (S6).

**Prior program handoff (required to start):** Existing auth system (backend/api/auth.py, tokens.py), RBAC (backend/api/rbac.py, permissions.py), tenant middleware (backend/api/tenant_middleware.py), audit_log table (migration 008). These already exist and must continue working.

---

## 2. Team Capacity (two 10-day sprints)

| Role | FTE | Available dev-days (×2) | Notes |
| :--- | :-: | :-: | :--- |
| Backend engineer ×2 | 2.0 | 40 | RBAC seed, tenant provisioning, audit pipeline, metering |
| Frontend engineer ×1 | 1.0 | 20 | User/role management UI, audit viewer |
| Integration engineer | 0.5 | 10 | Auth/permission conformance, rate limiting |
| QA | 1.0 | 20 | RLS regression, auth flow, tenant provisioning, UAT |
| **Total** | **4.5** | **~90** | Total task estimate below: **~42 dev-days** (BE 18.0 · FE 12.0 · INT 4.0 · QA 8.0) — ~48 days slack, absorbed per note below |

> **Slack absorption (not committed):** (a) RLS regression expansion on all existing tables; (b) auth edge cases (expired tokens, refresh rotation); (c) forward-pull of **E-RIS-02 #1** (HL7 listener scaffold) if platform lands early. Nothing past E-RIS-01 scope is committed.

---

## 3. Task Board (grouped by source work item)

> Estimates in dev-days. `Owner:` BE = backend, FE = frontend, INT = integration engineer, QA = test. `Check:` acceptance check.

### 3.1 Auth + JWT Refresh + Rate Limiting — E-RIS-01 #1
**Source:** `ris-integration-spec.md` §4.3; `RELEASE_PLAN.md` E-RIS-01 #1; existing `api/auth.py`, `api/tokens.py`.

| ID | Task | Owner | Est. | Dep | Acceptance check |
| :-: | :--- | :-: | :-: | :-: | :--- |
| S1-01 | Audit existing auth: verify JWT create/verify, refresh rotation, login flow in `api/auth.py` + `api/tokens.py` — document current state vs. spec requirements | BE | 1.0 | — | Audit report produced; gaps identified |
| S1-02 | Add RIS-specific permission claims to JWT payload (`ORDER_READ`, `SCHEDULE_READ`, etc.) — extend existing token creation in `api/tokens.py` | BE | 1.5 | S1-01 | Token contains RIS permissions; existing PACS permissions unaffected |
| S1-03 | RBAC seed: add RIS permissions to `permissions` table, RIS roles to `roles` table, map via `role_permissions` (seed script) | BE | 2.0 | S1-02 | Seed matches `01_persona_catalog.md` §4 permission matrix; unit tests pass |
| S1-04 | Rate limiting: extend existing `api/ratelimit.py` with RIS-specific limits (MWL queries, order creation, billing actions) — per-permission, per-tenant | BE | 1.5 | S1-01 | Rate limits enforced; 429 on excess; existing PACS limits unchanged |
| S1-05 | `@requires_permission` decorator: verify existing `api/rbac.py` guard works with new RIS permissions; add any missing permission checks to existing endpoints that RIS will call | BE | 1.0 | S1-03 | All RIS endpoints gated; existing endpoints unaffected |
| S1-06 | Auth E2E: login → token with RIS perms → access RIS endpoint → 403 without perm → refresh → re-access | QA | 1.5 | S1-05 | Auth flow green; no regression |

**Epic exit contribution:** E-RIS-01 #1 (auth + RBAC — foundation for all).

### 3.2 Tenant Middleware & Facility Isolation — E-RIS-01 #2
**Source:** `ris-integration-spec.md` §3.3; `RELEASE_PLAN.md` E-RIS-01 #3; existing `api/tenant_middleware.py`.

| ID | Task | Owner | Est. | Dep | Acceptance check |
| :-: | :--- | :-: | :-: | :-: | :--- |
| S1-07 | Audit existing tenant middleware: verify `app.facility_id` resolution, RLS enforcement, cross-tenant isolation in `api/tenant_middleware.py` | BE | 1.0 | — | Audit report; gaps vs. spec |
| S1-08 | Extend RLS policies: add `facility_id` RLS to any new RIS tables (created in later sprints); verify existing PACS tables have correct RLS | BE | 2.0 | S1-07 | RLS on all clinical tables; cross-facility query returns 0 rows |
| S1-09 | `app_cross_accessible_facilities()` helper: verify existing `cross_tenant_grants` helper works for IDN scheduling (shared with PACS V2-03) | BE | 1.5 | S1-08 | CTG-AC-01/02 smoke: granted reads return; denied without grant |
| S1-10 | Middleware caching: per-request facility-array cache for cross-tenant path (performance: auth < 1s for cross-facility) | BE | 1.0 | S1-09 | PAC-SL-25: cross-facility auth < 1s p95 |
| S1-11 | Tenant isolation E2E: create two test tenants; verify Facility A cannot read Facility B data; cross-tenant grants work for IDN path | QA | 1.5 | S1-10 | PAC-SL-61: 0 cross-tenant PHI incidents |

**Epic exit contribution:** E-RIS-01 #3 (tenant isolation).

### 3.3 Provision Tenant — E-RIS-01 #4
**Source:** `RELEASE_PLAN.md` E-RIS-01 #4; `06_acceptance_criteria.md` RIS-AC-P20-01; existing `db/tenant_provisioner.py`.

| ID | Task | Owner | Est. | Dep | Acceptance check |
| :-: | :--- | :-: | :-: | :-: | :--- |
| S1-12 | Audit existing `provision_tenant()` in `db/tenant_provisioner.py`: verify atomic create (facility + TRIAL subscription + seed + RLS scope) | BE | 1.0 | — | Audit report; verify RIS seed tables are included |
| S1-13 | Extend `provision_tenant()` to seed RIS defaults: rooms, modalities, report templates, procedure/CPT maps for new tenant | BE | 2.0 | S1-12 | New tenant has RIS defaults; RIS-AC-P20-01 |
| S1-14 | Rollback on failure: verify `provision_tenant()` rolls back all changes on error (no partial tenant) | BE | 1.5 | S1-13 | Rollback test: error at any step → no partial data |
| S1-15 | Provisioning performance: measure time to READY; ensure < 15 min for new tenant | BE | 1.0 | S1-14 | PAC-SL-51: READY < 15 min |
| S1-16 | Provisioning E2E: create tenant → seed RIS defaults → verify RLS → verify all tables exist → READY | QA | 1.5 | S1-15 | RIS-AC-P20-01 green |

**Epic exit contribution:** E-RIS-01 #4 (atomic provisioning).

### 3.4 Audit Pipeline — E-RIS-01 #5
**Source:** `RELEASE_PLAN.md` E-RIS-01 #5; `05_metrics_and_slas.md` RIS-SL-60; existing `db/audit_log.py`.

| ID | Task | Owner | Est. | Dep | Acceptance check |
| :-: | :--- | :-: | :-: | :-: | :--- |
| S1-17 | Audit existing `audit_log` table (migration 008): verify structure, triggers, completeness | BE | 1.0 | — | Audit report; verify 100% of existing write events logged |
| S1-18 | Add RIS audit events: order create/transition, appointment book/cancel, report sign, critical result flag/ack, charge drop, interface message | BE | 2.0 | S1-17 | 100% of scripted RIS events logged; RIS-SL-60 |
| S1-19 | Structured audit viewer: API endpoint for querying audit log by event type, actor, facility, date range (permission-gated `AUDIT_READ`) | BE | 1.5 | S1-18 | Viewer returns filtered results; `AUDIT_READ` enforced |
| S1-20 | Audit viewer UI: tenant admin console page for viewing audit log with filters (event type, actor, date range) | FE | 3.0 | S1-19 | WCAG 2.1 AA; filters work; data matches API |
| S1-21 | Audit completeness: verify audit triggers fire on all RIS tables (orders, appointments, reports, charges, critical_results) | QA | 1.5 | S1-18 | RIS-SL-60: 100% events logged; trigger coverage test |

**Epic exit contribution:** E-RIS-01 #5 (audit pipeline).

### 3.5 User/Role Management UI — E-RIS-01 #6
**Source:** `RELEASE_PLAN.md` E-RIS-01 #6; existing `frontend/src/roles/`, `frontend/src/users/`.

| ID | Task | Owner | Est. | Dep | Acceptance check |
| :-: | :--- | :-: | :-: | :-: | :--- |
| S1-22 | Audit existing roles/users UI: verify role CRUD, user assignment, permission matrix display | FE | 1.0 | — | Audit report; verify RIS roles display correctly |
| S1-23 | Extend roles UI with RIS permissions: add RIS permission categories (ORDER_*, SCHEDULE_*, REPORT_*, etc.) to permission matrix | FE | 2.5 | S1-22 | RIS permissions visible and assignable in UI |
| S1-24 | Extend users UI with RIS roles: add RIS-specific roles (Radiologist, Technologist, Scheduler, Front Desk, Billing Coder, etc.) to role assignment | FE | 1.5 | S1-23 | RIS roles assignable; existing PACS roles unaffected |
| S1-25 | User/role E2E: create user → assign RIS role → login → verify permissions → access RIS endpoint | QA | 1.0 | S1-24 | Permissions enforced end-to-end |

**Epic exit contribution:** E-RIS-01 #6 (user/role management).

### 3.6 Metering Hooks — E-RIS-01 #7
**Source:** `RELEASE_PLAN.md` E-RIS-01 #7; existing `db/metering.py`, `api/metering.py`.

| ID | Task | Owner | Est. | Dep | Acceptance check |
| :-: | :--- | :-: | :-: | :-: | :--- |
| S2-01 | Audit existing metering: verify `usage.events` table, event emission, invoice generation | BE | 1.0 | — | Audit report; verify existing metering works |
| S2-02 | Add RIS metering events: `MWL_QUERIES`, `API_CALLS` (RIS endpoints), `NOTIFICATIONS_SENT` (critical results, reminders) | BE | 2.0 | S2-01 | RIS events emitted; metering matches usage |
| S2-03 | Extend tenant usage view: add RIS usage breakdown (MWL queries, API calls, notifications) to tenant stats | BE | 1.5 | S2-02 | Tenant admin sees RIS usage; invoice drill-down |
| S2-04 | Metering E2E: generate RIS traffic → verify metering counts → verify tenant usage view → verify invoice | QA | 1.0 | S2-03 | Metering accuracy; RIS-SL-50 |

**Epic exit contribution:** E-RIS-01 #7 (metering).

### 3.7 Cross-cutting: RLS Regression & E2E — VG-1 Prerequisite

| ID | Task | Owner | Est. | Dep | Acceptance check |
| :-: | :--- | :-: | :-: | :-: | :--- |
| S2-05 | Full RLS regression: verify every existing PACS table has correct RLS policies; no regression from RIS foundation changes | QA | 2.0 | S1-08 | PAC-SL-61: all existing RLS policies intact |
| S2-06 | Auth regression: verify existing PACS login, token refresh, OAuth flows still work after RIS permission changes | QA | 1.5 | S1-05 | Existing auth flow green; no 403/401 regressions |
| S2-07 | Platform foundation E2E: login → RBAC → tenant isolation → provisioning → audit → metering (full platform smoke) | QA | 1.5 | S2-05/06 | G6 passes in staging; all platform foundations green |
| S2-08 | UAT prep: platform admin script (provision tenant, assign roles, verify audit, check metering) | QA | 1.0 | S2-07 | Scripts trace to RIS-AC-P20-01, RIS-SL-60/61 |

---

## 4. Sprint Milestones

| Milestone | Target | Evidence |
| :--- | :--- | :--- |
| **Day 3 (S1)** | Auth audit + RIS perms in JWT; RBAC seed started; tenant middleware audit | S1-01/02/07 closed; S1-03 started |
| **Day 8 (S1)** | RBAC seed green; tenant provisioning extended; audit pipeline live; RLS on new tables | S1-03/08/13/18 closed |
| **Day 5 (S2)** | Provisioning rollback verified; audit viewer UI; metering events; user/role UI extended | S1-14, S1-20, S2-02, S1-23 closed |
| **Day 10 (S2, demo)** | Full RLS regression; auth regression; platform foundation E2E green; UAT prep | S2-05/06/07/08; G6 pre-check; sprint review |

---

## 5. Sprint Definition of Done (acceptance checks)

| # | Check | Verifies | Method |
| :-: | :--- | :--- | :--- |
| D1 | JWT contains RIS permissions; `@requires_permission` gates all RIS endpoints | E-RIS-01 #1 | S1-06 E2E |
| D2 | Tenant isolation: cross-facility query returns 0; cross-tenant grants work for IDN | PAC-SL-61 | S1-11 RLS suite |
| D3 | `provision_tenant()` atomic; RIS defaults seeded; READY < 15 min; rollback verified | RIS-AC-P20-01, PAC-SL-51 | S1-16 |
| D4 | 100% audit on RIS events; structured viewer works; RIS-SL-60 | RIS-SL-60 | S1-21 |
| D5 | User/role UI shows RIS permissions and roles; assignable; permission-enforced | E-RIS-01 #6 | S1-25 |
| D6 | RIS metering events emitted; tenant usage view accurate; RIS-SL-50 | RIS-SL-50 | S2-04 |
| D7 | Full RLS regression; auth regression; platform foundation E2E green | G6 | S2-05/06/07 |
| D8 | Engineering DoD: `tsc --noEmit` + `vite build` clean; unit tests green; migrations reviewed | release-plan §6 | CI gate |
| D9 | No P0/P1 open defects at sprint close | release-plan §6 | Defect triage |

---

## 6. Risks & Watch Items

| Risk | Watch indicator | Mitigation |
| :--- | :--- | :--- |
| RLS regression on existing PACS tables | S2-05 regression suite | Full isolation regression on every policy change; `NOBYPASSRLS` convention |
| Auth token size bloat from RIS permissions | JWT payload size | Permission lazy-loading (only on `@requires_permission` check); token size monitored |
| Tenant provisioning RIS seed fails | S1-14 rollback test | Atomic transaction; every seed step wrapped; failure at any step → full rollback |
| Metering event miss (silent) | S2-04 count mismatch | Daily reconcile; event count vs. API count assertion |

---

## Traceability

| Source work item | Tasks |
| :--- | :--- |
| E-RIS-01 #1 (auth + rate limiting) | S1-01…06 |
| E-RIS-01 #2 (RBAC seed) | S1-03 |
| E-RIS-01 #3 (tenant middleware) | S1-07…11 |
| E-RIS-01 #4 (provisioning) | S1-12…16 |
| E-RIS-01 #5 (audit pipeline) | S1-17…21 |
| E-RIS-01 #6 (user/role UI) | S1-22…25 |
| E-RIS-01 #7 (metering) | S2-01…04 |
| Cross-cutting (RLS regression, auth regression, platform E2E) | S2-05…08 |
