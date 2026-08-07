# Sprint 1 Detail — Platform Foundation (E-PAC-01 · E-RIS-01)

**Version:** 1.0 · **Date:** 2026-08-04 · **Source:** `requrements/RIS/RELEASE_PLAN.md` E-RIS-01, `requrements/PACS/RELEASE_PLAN.md` E-PAC-01
**Cadence:** 2-week sprint (10 working days) · **Squad:** Platform (2 backend · 1 frontend · part-time QA; integration engineer on standby)

> This document decomposes the shared **Platform Foundation** epic — E-RIS-01 and E-PAC-01 (the latter inherits/reuses E-RIS-01) — into task-level backlog items with owners, dev-day estimates, dependencies, and acceptance checks. It is the executable refinement of those two epics for **Sprint 1** only; E-PAC-02+ / E-RIS-02+ are separate sprints.

---

## 1. Sprint Goal

> **"A new tenant can be provisioned atomically (PACS + RIS seed data), a user at that tenant can log in with facility-scoped roles, every action is audited, and usage/quota are metered — end to end, verified in staging."**

**Scope in:** RBAC seed + endpoint wiring, tenant middleware, atomic provisioning with PACS/RIS seed, audit pipeline + structured viewer, user/role management UI, tenant-prefixed object keys, metering hooks + quota alerts + invoice view, tenant-lifecycle gating, service-key scopes for machine actors. **Auth (E-RIS-01 #1): verify-only** — the backend (login, token pair, refresh rotation, blocklist, rate limiting) is already complete per `auth_design.md`; Sprint 1 smoke-verifies it (folded into D7) and wires `token_version` (S1-27).

**Scope out (later sprints):** ingestion gateway (E-PAC-02), MWL/MPPS (E-PAC-03), archive/SC (E-PAC-04), DICOMweb (E-PAC-05), viewer (E-PAC-06), admin console (E-PAC-07), interface monitoring (E-PAC-08), dashboards (E-PAC-09), DR (E-PAC-10); RIS domain epics E-RIS-02…11.

---

## 2. Team Capacity (10 working days)

| Role | FTE | Available dev-days | Notes |
| :--- | :-: | :-: | :--- |
| Backend engineer ×2 | 2.0 | 20 | Schema, migrations, APIs, `@requires_permission` |
| Frontend engineer ×1 | 1.0 | 10 | Ant Design, design tokens, WCAG 2.1 AA |
| QA | 0.5 | 5 | Acceptance-check automation, isolation & rollback tests |
| Integration engineer | 0.25 | 2.5 | DICOM/service-key conformance only (standby, not load-bearing) |
| **Total** | **3.75** | **~37.5** | Total task estimate below: **~37 dev-days** (BE 22.5 · FE 10.0 · QA 4.5) — at full capacity with a ~2-day BE overhang, handled per §6 |

---

## 3. Task Board (grouped by source work item)

> Estimates in dev-days (0.5 = half-day). `Owner:` BE = backend, FE = frontend, QA = test. `Check:` the acceptance check (maps to AC/SL IDs where applicable).

### 3.1 RBAC seed & endpoint wiring — E-RIS-01 #2 · E-PAC-01 #1
**Source:** `RBAC_matrix_spec.md` §2/§3/§4/§7/§8; `pacs-ris-schema.sql` §14 (seed), §15 (RBAC); `auth_design.md` (RBAC ✅).

| ID | Task | Owner | Est. | Dep | Acceptance check |
| :-: | :--- | :-: | :-: | :-: | :--- |
| S1-01 | Diff current permissions table vs. §3 catalog (56 codes) — classify SEED / EXT / NEW | BE | 0.5 | — | Drift report matches §3 tags |
| S1-02 | Migration: insert **NEW** permission codes idempotently (`ON CONFLICT (code) DO NOTHING`) | BE | 0.5 | S1-01 | Re-run = 0 rows changed; catalog count = 56 |
| S1-03 | Seed roles (24, incl. RADIOLOGIST, TELERADIOLOGIST, TECHNOLOGIST, PACS_ADMIN, IMAGING_INFORMATICS, DEPARTMENT_MANAGER, REFERRING_PHYSICIAN, ED_PHYSICIAN, SCHEDULER, BILLER, …) + `role_permissions` per matrices A/B/C | BE | 1.0 | S1-02 | `role_permissions` counts match §5 matrices |
| S1-04 | Seed verification tests: every matrix cell present; role codes from §4 only | QA | 1.0 | S1-03 | Tests green; counts match spec |
| S1-05 | Wire `@requires_permission` on existing endpoints per §7 endpoint map (worklist, files/uploads, shares, tenants, roles, service keys, logs) | BE | 2.0 | S1-02 | Endpoint→permission map tests pass; 403 on missing permission |

**Epic exit contribution:** E-RIS-01 #2 / E-PAC-01 #1 "Seed matches `RBAC_matrix_spec.md` §8; unit tests".

### 3.2 Tenant middleware & effective permissions — E-RIS-01 #3
**Source:** `RBAC_matrix_spec.md` §2 (runtime model); `pacs-ris-schema.sql` §2 (`users`/`roles`/`user_roles`); `pacs-ris-multitenancy.md` §3–4.

| ID | Task | Owner | Est. | Dep | Acceptance check |
| :-: | :--- | :-: | :-: | :-: | :--- |
| S1-06 | Facility resolution: **JWT `facility_id` wins** → validate `X-Tenant-ID`/subdomain if present → reject mismatch (400) | BE | 1.0 | — | Mismatched header + JWT → 400 + audit |
| S1-07 | Set `app.facility_id` / `app.user_id` / `app.client_ip` per request; effective permission = **union of facility-scoped `user_roles` grants** | BE | 1.5 | S1-06 | Union resolves across roles at same facility |
| S1-08 | Isolation test suite: user with role at NGH sees 0 rows at CLINIC; cross-facility query returns empty, never errors | QA | 1.5 | S1-07 | `PAC-SL-61`-style isolation assertion green |

**Epic exit contribution:** E-RIS-01 #3 "Cross-facility isolation test passes".

### 3.3 Atomic provisioning with PACS/RIS seed — E-RIS-01 #4 · E-PAC-01 #5
**Source:** `pacs-ris-schema.sql` §16 (`provision_tenant()`); `tenants_design.md` (spinner, statuses); `RBAC_matrix_spec.md` §2.6 (lifecycle).

| ID | Task | Owner | Est. | Dep | Acceptance check |
| :-: | :--- | :-: | :-: | :-: | :--- |
| S1-09 | `provision_tenant()`: single transaction — facility + TRIAL subscription + seed data + RLS scope; stages PROVISIONING→SEEDING→READY | BE | 2.0 | S1-07 | **RIS-AC-P20-01 / PAC-AC-P20-01**: READY < 15 min |
| S1-10 | RIS seed: sites, rooms, modalities, retention defaults, report templates | BE | 1.0 | S1-09 | Seeded rows exist per facility, RLS-scoped |
| S1-11 | PACS seed: modalities + AE registry, retention defaults, storage tier policy | BE | 1.0 | S1-09 | AE registry rows scoped to facility |
| S1-12 | Tenant-ops console wiring: create → provisioning progress card (actions disabled until READY) | FE | 1.5 | S1-09 | `tenants_design.md` parity; spinner visible |
| S1-13 | Rollback test: inject failure mid-seed → **no partial tenant** (facility/subscription/seed all absent) | QA | 1.0 | S1-09 | Atomicity assertion green |

**Epic exit contribution:** E-RIS-01 #4 / E-PAC-01 #5 (atomic provisioning, rollback leaves no partial tenant).

### 3.4 Audit pipeline & structured viewer — E-RIS-01 #5 · E-PAC-01 #6
**Source:** `pacs-ris-schema.sql` §10 (`audit_log`, partitioned); `audit-logs_design.md` (target state); `RBAC_matrix_spec.md` §7 (`AUDIT_READ`).

| ID | Task | Owner | Est. | Dep | Acceptance check |
| :-: | :--- | :-: | :-: | :-: | :--- |
| S1-14 | Trigger-based `audit_log` capture (`before`/`after` JSONB) on tenant-scoped clinical tables | BE | 1.5 | S1-07 | INSERT/UPDATE/DELETE/LOGIN/EXPORT rows written |
| S1-15 | Structured audit API: `event_type`, `actor`, `resource_type/id`, `description`, `tenant`, filters, cursor pagination; `/logs/event-types`, `/logs/actors` | BE | 1.5 | S1-14 | Response = `{data, next_cursor, has_more, total}` |
| S1-16 | Structured audit viewer (multi-select event-type chips, date range ≤ 90 d, actor filter, tenant dropdown for super-admin, live toggle, CSV export) | FE | 2.5 | S1-15 | `audit-logs_design.md` parity; WCAG AA |
| S1-17 | PACS event coverage: view / retrieve / export / delete / share / access events all logged | BE | 1.5 | S1-14 | **PAC-SL-60** completeness test = 100% of sampled events |
| S1-18 | Audit completeness test: scripted actions → assert 1:1 event rows; meta-audit (viewing logs) optional | QA | 1.0 | S1-16 | 0 missing events in test scenario |

**Epic exit contribution:** E-RIS-01 #5 / E-PAC-01 #6 (100% events; RIS-SL-60 / PAC-SL-60).

### 3.5 User/role management UI + PACS permission surface — E-RIS-01 #6 · E-PAC-01 #2
**Source:** `roles_design.md` (gaps list); `RBAC_matrix_spec.md` §7 (endpoint map); `RIS/04` RIS-UI-39; `PAC/06` PAC-AC-P19-02.

| ID | Task | Owner | Est. | Dep | Acceptance check |
| :-: | :--- | :-: | :-: | :-: | :--- |
| S1-19 | Backend: roles `description` column + `user_count` subquery; `GET /api/permissions`; `GET /api/roles/{id}/users` | BE | 1.0 | S1-03 | Endpoints return grouped permissions + counts |
| S1-20 | Roles page rewrite: description + user-count columns, built-in lock, permission search, group select-all, expandable permissions | FE | 2.0 | S1-19 | `roles_design.md` parity; super_admin immutable |
| S1-21 | Users page: assign **facility-scoped** role grants (`user_roles` insert per facility), active toggle | FE | 1.5 | S1-19 | PAC-AC-P19-02: change → effective immediately + audited |
| S1-22 | PACS endpoint→permission wiring: `VIEWER_READ`, `STUDY_READ`, `FILE_READ/WRITE`, `STUDY_EXPORT`, `STORAGE_ADMIN` on planned endpoints (stub-gated) | BE | 1.5 | S1-05 | §7 map test: each endpoint requires its permission |

**Epic exit contribution:** E-RIS-01 #6 (`roles_design.md` parity) / E-PAC-01 #2 (endpoint map verified by tests).

### 3.6 Object-key policy, metering, quota & invoice — E-PAC-01 #3/4 · E-RIS-01 #7
**Source:** `pacs-ris-multitenancy.md` §4 (tenant-prefixed keys); `pacs-ris-schema.sql` §17 (`usage_metering`, `tenant_invoices`); `PAC/06` PAC-AC-P20-02; `RIS/06` RIS-AC-P19-02; `tenants_design.md` (storage quota).

| ID | Task | Owner | Est. | Dep | Acceptance check |
| :-: | :--- | :-: | :-: | :-: | :--- |
| S1-23 | Object-key policy enforced: upload path derives key `s3://vna/{tenant_code}/{facility_id}/…`; reject hand-built keys | BE | 1.0 | S1-07 | Cross-tenant key write attempt → 403 + audit |
| S1-24 | Metering hooks → `usage_metering`: `API_CALLS`, `MWL_QUERIES`, `STUDIES_STORED`, `WADO_BYTES`, `DICOM_TX` (partitioned) | BE | 1.5 | S1-23 | Meter rows match instrumentation counts |
| S1-25 | Quota tracking + 75/90% alerts via notification subsystem; optional hard-stop config | BE | 1.0 | S1-24 | Alert fires at threshold in staging |
| S1-26 | Invoice view (plan + base + overage lines, period, drill to usage) + metering-accuracy test | FE | 1.5 | S1-24 | PAC-AC-P20-02 / RIS-AC-P19-02: line items match metering |

**Epic exit contribution:** E-PAC-01 #3/4 / E-RIS-01 #7 (metering matches usage).

### 3.7 Cross-cutting platform plumbing — RBAC §2.6 · auth §1
**Source:** `RBAC_matrix_spec.md` §2 (token_version, lifecycle); `auth_design.md`; `service-keys_design.md`.

| ID | Task | Owner | Est. | Dep | Acceptance check |
| :-: | :--- | :-: | :-: | :-: | :--- |
| S1-27 | `token_version` bump on role/permission change → affected users forced to re-auth on next request | BE | 0.5 | S1-03 | PAC-AC-P19-02: re-login reflects new permissions |
| S1-28 | Tenant lifecycle gate: `SUSPENDED` → login/read gate in middleware (RLS still protects data); `CANCELLED` → retention governs | BE | 1.0 | S1-09 | Suspended tenant login → 403 + audit |
| S1-29 | Service keys for machine actors: verify scopes incl. `STUDY_READ`/`RESULTS_READ` (least privilege); UI polish (permissions, expiry badges, last-used, show/hide revoked) | FE | 1.0 | S1-02 | `service-keys_design.md` parity; scope check tests |

---

## 4. Sprint Milestones

| Milestone | Target | Evidence |
| :--- | :--- | :--- |
| **Day 3** | RBAC drift report + NEW-permission migration merged; role seeds landed | S1-01…S1-03 closed; `role_permissions` counts match §5 |
| **Day 5** | Facility middleware + effective-permission union; `provision_tenant()` atomic green with rollback test | S1-06…S1-09, S1-13 closed; isolation + rollback suites green |
| **Day 8** | Audit triggers + structured API + viewer; roles/users UI; metering + quota hooks | S1-14…S1-26 closed; PAC-SL-60 completeness + PAC-AC-P20-02 accuracy tests green |
| **Day 10 (demo)** | Full loop: provision tenant (PACS+RIS seed) → admin login → assign facility roles → trigger + view audit → view metered usage vs. quota | Sprint review demo; G6 pre-checks pass in staging tenant |

---

## 5. Sprint Definition of Done (acceptance checks)

| # | Check | Verifies | Method |
| :-: | :--- | :--- | :--- |
| D1 | Seed matches `RBAC_matrix_spec.md` §8 (permissions = 56; roles = 24; role_permissions = matrix) | E-RIS-01 #2 / E-PAC-01 #1 | Automated seed test (S1-04) |
| D2 | Cross-facility isolation: user at NGH sees 0 CLINIC rows; mismatch → 400 | E-RIS-01 #3 | S1-08 suite |
| D3 | Atomic provisioning: PACS + RIS seed, READY < 15 min, rollback leaves nothing | RIS-AC-P20-01, PAC-AC-P20-01 | S1-13 rollback test + timer assertion |
| D4 | 100% audit: every scripted view/retrieve/export/delete/share/access produces an event row | PAC-SL-60, RIS-SL-60 | S1-18 completeness test |
| D5 | Metering accuracy: invoice line items == metered usage | PAC-AC-P20-02, RIS-AC-P19-02 | S1-26 test |
| D6 | Cross-tenant denial without grants: attempted read → denied + `cross_tenant.denied`-style audit | PAC-AC-P20-03 | S1-08 + audit-row assertion |
| D7 | Engineering DoD: `tsc --noEmit` + `vite build` clean; unit tests green; migrations reviewed; audit events on all state-changing endpoints | release-plan §6 | CI gate |
| D8 | No P0/P1 open defects at sprint close | release-plan §6 | Defect triage |

---

## 6. Risks & Watch Items (Sprint 1)

| Risk | Watch indicator | Mitigation |
| :--- | :--- | :--- |
| Seed drift vs. §8 spec (permission/role counts) | S1-04 test red | Freeze catalog §3 before S1-01; diff first, then migrate |
| **BE capacity at/over budget (22.5 vs 20 dev-days)** | Velocity vs. 20 BE-days | Slip S1-22 (PACS stub-gating) to Sprint 2 start; integration engineer assists with schema work; re-estimate S1-05/S1-09 at stand-up |
| FE capacity at full budget (10.0 exactly) | Velocity vs. 10 FE-days | Sequence FE tasks after their BE deps; pull S1-16 viewer to day-5 if behind |
| Provisioning transaction grows large (PACS+RIS seed) | `provision_tenant()` runtime | Stage seed inserts; benchmark in staging; keep single-transaction guarantee |
| token_version churn breaking existing sessions | Login retest failures | Bump only affected users; test suite covers re-auth path |
| RLS owner-bypass risk on new tables | Isolation suite extension | Follow `FORCE ROW LEVEL SECURITY` + `NOBYPASSRLS` convention from `pacs-ris-multitenancy.md` §3 |

---

## Traceability

| Source work item | Tasks |
| :--- | :--- |
| E-RIS-01 #1 (auth) — backend complete per `auth_design.md` | Verify-only (D7 smoke + S1-27 token_version); no new build task |
| E-RIS-01 #2 / E-PAC-01 #1 (RBAC seed) | S1-01…S1-05 |
| E-RIS-01 #3 (tenant middleware) | S1-06…S1-08 |
| E-RIS-01 #4 / E-PAC-01 #5 (provisioning + seed) | S1-09…S1-13 |
| E-RIS-01 #5 / E-PAC-01 #6 (audit) | S1-14…S1-18 |
| E-RIS-01 #6 / E-PAC-01 #2 (roles UI + permission surface) | S1-19…S1-22 |
| E-PAC-01 #3/4 / E-RIS-01 #7 (keys, metering, quota, invoice) | S1-23…S1-26 |
| RBAC §2.6 / auth / service keys (cross-cutting) | S1-27…S1-29 |
