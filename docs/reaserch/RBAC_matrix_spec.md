# RBAC Matrix Specification — Roles, Permissions & Tenant Scoping

**Version:** 1.0 · **Date:** 2026-08-04 · **Status:** Engineering-ready (seeding + enforcement)
**Source:** converted from `requrements/{PACS,RIS,EMR}/01_persona_catalog.md` and `03_user_stories.md`; grounded in `research/pacs-ris-schema.sql` (§2 RBAC tables, §14 seed) and `docs/specs/roles_design.md`, `auth_design.md`.

---

## 1. Purpose & Scope

Turn the persona catalogs into a **directly implementable RBAC spec**. Engineering implements it via the existing data model:

| Artifact | Location | Purpose |
| :--- | :--- | :--- |
| `roles` (role_id, code, name, description) | schema §2, **no RLS** | Role catalog (§4) |
| `permissions` (permission_id, code, description) | schema §2, **no RLS** | Permission catalog (§3) |
| `role_permissions` (role_id, permission_id) | schema §2, **no RLS** | Role→permission matrix (§5) |
| `user_roles` (user_id, role_id, facility_id) | schema §2, **RLS-scoped** | Facility-scoped role grants |
| `@requires_permission("CODE")` | `api/rbac.py` | Endpoint enforcement (§7) |
| JWT `facility_id` + `app.facility_id` session | `api/tenant_middleware.py` | Tenant scoping (§6) |
| token_version | `db/users.py` | Force re-login on permission change |

> **Naming conventions used in this spec:** `SEED` = already in `pacs-ris-schema.sql` §14. `EXT` = already used by the frontend (docs/specs). `NEW` = must be added by migration (provided in §9).

---

## 2. Implementation Model (how roles resolve at runtime)

1. **Login/API call** → middleware resolves facility: **JWT `facility_id` wins** → validate `X-Tenant-ID`/subdomain if present → reject mismatch.
2. Middleware loads `user_roles` for (user, resolved facility) and computes the **effective permission set** = UNION of `role_permissions` for all held roles at that facility. No grant at the resolved facility → 403.
3. `SET app.facility_id = :id` (+ `app.user_id`, `app.client_ip`) for RLS and audit triggers.
4. **Endpoints enforce** with `@requires_permission("CODE")` (server is source of truth). Frontend gates UI with `hasPermission()`.
5. **Any role/permission change** bumps `token_version` for affected users → next request forces re-auth.
6. **Tenant lifecycle:** `SUSPENDED` → login/read gate in middleware (RLS still protects data); `CANCELLED` → retention/legal-hold governs purge.

---

## 3. Permission Catalog (canonical, 56 codes)

| Code | Origin | Description | Surface |
| :--- | :-: | :--- | :--- |
| **Platform / Identity** | | | |
| ADMIN | SEED | Master admin flag (system-level functions) | All |
| TENANT_READ | EXT | View tenant info, usage, quota | All |
| TENANT_ADMIN | EXT | Tenant config & lifecycle (suspend/reactivate/plan/quota) | All |
| USER_READ | NEW | View users & role assignments (tenant scope) | All |
| USER_WRITE | NEW | Create/update/deactivate users, assign roles | All |
| ROLE_READ | EXT | View roles & permissions | All |
| ROLE_WRITE | EXT | Create/update custom roles & permission grants | All |
| ROLE_DELETE | EXT | Delete custom roles (built-in protected) | All |
| SERVICE_KEY_READ | EXT | View API/service keys | All |
| SERVICE_KEY_WRITE | EXT | Create/update service keys | All |
| SERVICE_KEY_DELETE | EXT | Revoke service keys | All |
| AUDIT_READ | SEED | View audit log (frontend alias: `LOG_READ`) | All |
| INTERFACE_MONITOR | SEED | View interface/modality health dashboards | Ops |
| INTERFACE_ADMIN | NEW | Configure modalities (AE/IP), routing, endpoints | Ops |
| METERING_READ | NEW | View usage metering & tenant invoices | Ops |
| **Patient / MPI** | | | |
| PATIENT_READ | SEED | View patient demographics | All clinical |
| PATIENT_WRITE | SEED | Create/edit patients, insurance | RIS/EMR |
| PATIENT_MERGE | NEW | Merge MPI duplicate records | RIS/EMR |
| MPI_ADMIN | NEW | Maintain patient identifiers/issuers, MPI rules | RIS/EMR |
| **Orders & Scheduling** | | | |
| ORDER_READ | SEED | View orders (any status) | RIS/EMR |
| ORDER_WRITE | SEED | Enter/modify/cancel orders | RIS/EMR |
| SCHEDULE_READ | NEW | View schedules/appointments | All clinical |
| SCHEDULE_WRITE | SEED | Create/move/cancel appointments (conflict-checked) | RIS |
| PRIOR_AUTH_READ | NEW | View prior-authorization status | RIS |
| PRIOR_AUTH_WRITE | NEW | Request/update prior authorization | RIS |
| **Worklist** | | | |
| WORKLIST_READ | SEED | View modality/reading worklists | RIS/PACS |
| WORKLIST_WRITE | SEED | Update worklist entries, batch actions | RIS/PACS |
| **Reporting** | | | |
| REPORT_READ | SEED | View reports | All |
| REPORT_WRITE | SEED | Dictate/edit reports (drafts, preliminary) | RIS |
| REPORT_SIGN | SEED | Sign final reports | RIS |
| CRITICAL_RESULTS_WRITE | NEW | Flag critical findings & issue tracked notifications | RIS |
| REPORT_TEMPLATE_ADMIN | NEW | Manage report templates & hanging-protocol libraries | RIS/PACS |
| **Billing / Revenue** | | | |
| BILLING_READ | NEW | View charges, claims, unbilled aging | RIS/EMR |
| BILLING_WRITE | SEED | Capture charges, submit/manage claims, denials | RIS/EMR |
| CODING_WRITE | NEW | Assign ICD-10/CPT/HCPCS (incl. CAC confirm) | EMR |
| **PACS / Imaging** | | | |
| VIEWER_READ | SEED | Open the imaging viewer | All |
| STUDY_READ | NEW | Query/retrieve study metadata & pixels (DICOMweb read) | PACS/API |
| FILE_READ | EXT | View/download uploaded files & share links | PACS |
| FILE_WRITE | EXT | Upload/store files, DICOM ingest | PACS |
| STUDY_EXPORT | NEW | Export CD/DVD, XDS-I.b, anonymized (audited) | PACS |
| STORAGE_ADMIN | NEW | Retention policies, storage tiers, quotas, ILM | PACS |
| **EMR Clinical** | | | |
| CHART_READ | NEW | View full patient chart (problems, allergies, meds, results) | EMR |
| ENCOUNTER_WRITE | NEW | Create/edit encounter documentation & notes | EMR |
| NOTE_SIGN | NEW | Sign notes (attending) / cosign (resident) | EMR |
| MED_ORDER_READ | NEW | View medication orders & history | EMR |
| MED_ORDER_WRITE | NEW | Order medications | EMR |
| MED_VERIFY | NEW | Pharmacist verify/override with intervention docs | EMR |
| MAR_READ | NEW | View Medication Administration Record | EMR |
| MAR_WRITE | NEW | Chart administrations (BCMA) | EMR |
| RESULTS_READ | NEW | View lab/path/imaging results | EMR/All |
| RESULTS_RELEASE | NEW | Validate/release lab results, critical-value notify | EMR |
| LAB_SPECIMEN_WRITE | NEW | Specimen accessioning (barcode → order match) | EMR |
| CARE_PLAN_WRITE | NEW | Care plans, referral/follow-up tasks | EMR |
| HIM_WRITE | NEW | ROI, amendments, deficiency tracking | EMR |
| CDS_ADMIN | NEW | Order sets, CDS rules, templates config | EMR |
| PORTAL_READ | NEW | Patient portal self-service (own data, released per policy) | EMR |

---

## 4. Role Catalog (persona → role, 24 roles)

| Role code | Name | Source persona(s) | Type | Scope |
| :--- | :--- | :--- | :-: | :--- |
| SYSTEM_ADMIN | System Admin (a.k.a. `super_admin` UI role) | P20 all systems | SEED · built-in · immutable | Platform (BYPASSRLS ops) |
| TENANT_ADMIN | Tenant Admin | P19 all systems | NEW | Tenant |
| PATIENT | Patient (portal) | P12 EMR / H21 | NEW | Own data |
| RADIOLOGIST | Radiologist | PAC-P01, RIS-P01 | SEED | Facility |
| TELERADIOLOGIST | Teleradiologist | PAC-P03 | NEW | Cross-tenant (engagement-gated) |
| TECHNOLOGIST | Technologist | PAC-P02, RIS-P02 | SEED | Facility |
| SCHEDULER | Scheduler | RIS-P03 | SEED | Facility |
| RECEPTIONIST | Receptionist / Front Desk | RIS-P04, EMR-P06 | SEED | Facility |
| REFERRING_PHYSICIAN | Referring Physician | PAC-P06, RIS-P08 | SEED | Facility (view) |
| ED_PHYSICIAN | ED Physician | PAC-P07, RIS-P09, EMR-P10 | NEW | Facility (view+alert) |
| BILLER | Biller | RIS-P05 | SEED | Facility |
| MEDICAL_CODER | Medical Coder | EMR-P07 | NEW | Facility |
| DEPARTMENT_MANAGER | Department Manager | PAC-P08, RIS-P07 | NEW | Facility (analytics) |
| RADIOLOGY_ADMIN | Radiology Admin | RIS-P06 | SEED | Facility |
| PACS_ADMIN | PACS Administrator | PAC-P04 | NEW | Facility |
| IMAGING_INFORMATICS | Imaging Informatics (CIIP) | PAC-P05 | NEW | Facility |
| PHYSICIAN | Attending Physician | EMR-P01 | NEW | Facility |
| RESIDENT | Resident / Fellow | EMR-P02 | NEW | Facility (cosign) |
| NURSE | Nurse | EMR-P03 | NEW | Facility |
| PHARMACIST | Pharmacist | EMR-P04 | NEW | Facility |
| LAB_TECHNICIAN | Lab Technician / Pathologist | EMR-P05 | NEW | Facility |
| HIM_SPECIALIST | HIM / Medical Records | EMR-P08 | NEW | Facility |
| CARE_COORDINATOR | Care Coordinator | EMR-P09 | NEW | Facility |
| EMR_ADMIN | EMR/HIT Admin | EMR-P11 | NEW | Facility |

> **Unification note:** the frontend's built-in `super_admin` role ≡ schema `SYSTEM_ADMIN` (all permissions, immutable). `TENANT_ADMIN` **permission** ≠ `TENANT_ADMIN` **role** (the role includes that permission plus more). `LOG_READ` (frontend) ≡ `AUDIT_READ` (canonical).

---

## 5. Role → Permission Matrices

### Matrix A — Imaging roles (PACS/RIS)

`SYS` = SYSTEM_ADMIN (ALL) · `TEN` = TENANT_ADMIN · Roles: RAD=TEL=identical permission set (difference is scope, §6).

| Permission | RAD/TEL | TECH | SCHED | RECEPT | REF | ED | BILL | DMGR | RADADM | PACSADM | INFO |
| :--- | :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: |
| PATIENT_READ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| PATIENT_WRITE | | | ✓ | ✓ | | | | | ✓ | | |
| PATIENT_MERGE / MPI_ADMIN | | | | | | | | | ✓ | | |
| ORDER_READ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| ORDER_WRITE | | | | | | | | | ✓ | | |
| SCHEDULE_READ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | | ✓ | ✓ | ✓ | ✓ |
| SCHEDULE_WRITE | | | ✓ | | | | | | ✓ | | |
| PRIOR_AUTH_READ | ✓ | | ✓ | | | | | | ✓ | | |
| PRIOR_AUTH_WRITE | | | ✓ | | | | | | ✓ | | |
| WORKLIST_READ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | | ✓ | ✓ | ✓ | ✓ |
| WORKLIST_WRITE | ✓ | ✓ | | | | | | | ✓ | ✓ | |
| REPORT_READ | ✓ | | | | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| REPORT_WRITE | ✓ | | | | | | | | ✓ | | |
| REPORT_SIGN | ✓ | | | | | | | | | | |
| CRITICAL_RESULTS_WRITE | ✓ | ✓ | | | | ✓ | | | ✓ | | |
| REPORT_TEMPLATE_ADMIN | ✓ | | | | | | | | ✓ | ✓ | ✓ |
| BILLING_READ | | | | | | | ✓ | ✓ | ✓ | ✓ | ✓ |
| BILLING_WRITE | | | | | | | ✓ | | | | |
| VIEWER_READ | ✓ | ✓ | | | ✓ | ✓ | | | ✓ | ✓ | ✓ |
| STUDY_READ | ✓ | ✓ | | | ✓ | ✓ | | ✓ | ✓ | ✓ | ✓ |
| FILE_READ / FILE_WRITE | | ✓ | | | | | | | ✓ | ✓ | |
| STUDY_EXPORT | ✓ | | | | | | | | ✓ | ✓ | |
| STORAGE_ADMIN | | | | | | | | | ✓ | ✓ | |
| INTERFACE_MONITOR | | | | | | | | ✓ | ✓ | ✓ | ✓ |
| INTERFACE_ADMIN | | | | | | | | | ✓ | ✓ | |
| AUDIT_READ | | | | | | | | ✓ | ✓ | ✓ | ✓ |
| METERING_READ | | | | | | | | ✓ | ✓ | | ✓ |
| CHART_READ / RESULTS_READ | ✓ | ✓ | | | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| USER_READ / USER_WRITE | | | | | | | | | ✓ | ✓ | |
| ROLE_READ / ROLE_WRITE / ROLE_DELETE | | | | | | | | | ✓ | ✓ | |
| ENCOUNTER_WRITE | | | | | | ✓ | | | ✓ | | |
| NOTE_SIGN | | | | | | ✓ | | | | | |
| MED_ORDER_READ | ✓ | | | | | ✓ | | | ✓ | | |
| MED_ORDER_WRITE / ORDER_WRITE | | | | | | ✓ | | | ✓ | | |
| MAR_READ | | | | | | ✓ | | | | | |
| ADMIN | | | | | | | | | ✓ | | |

> **ED_PHYSICIAN scope note:** this role spans three personas — PACS-P07 / RIS-P09 (view + critical alerts) and **EMR-P10 (full ED scope: chart, STAT ordering, ED notes)** per `requrements/EMR/01_persona_catalog.md` §EMR-P10 and EMR-US-P10-01. The matrix above grants the **union** (view/alert + ENCOUNTER_WRITE, NOTE_SIGN, MED_ORDER_READ/WRITE, ORDER_WRITE, MAR_READ). Sites preferring separation may assign ED physicians the `PHYSICIAN` role in the EMR context instead, and keep `ED_PHYSICIAN` view-only.
>
> **PACSADM addendum (pacs_admin walk, 2026-08-28):** The facility PACS operator role additionally holds
> `DICOMWEB_READ`/`DICOMWEB_WRITE` (DICOMweb console + STOW), `HL7_READ` (HL7 console +
> Interface Health), `REPLICA_READ` (Replicas), `ROUTING_READ` (Routing) — code-level
> grants that enable the actual PACS-ops surfaces. `CRITICAL_RESULTS_WRITE` and
> `WORKLIST_WRITE` were trimmed (the exam console / MWL are clinical-scoped, hidden
> for this admin role).

### Matrix B — EMR roles

| Permission | PHYS | RES | NURSE | PHARM | LAB | CODER | HIM | COORD | EMRADM |
| :--- | :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: |
| CHART_READ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | |
| PATIENT_READ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | |
| ENCOUNTER_WRITE | ✓ | ✓ | ✓ | | | | | ✓ | |
| NOTE_SIGN | ✓ | | ✓ | | | | ✓ (amend) | | |
| MED_ORDER_READ | ✓ | ✓ | ✓ | ✓ | | | | ✓ | |
| MED_ORDER_WRITE | ✓ | ✓ | | ✓ | | | | | |
| MED_VERIFY | | | | ✓ | | | | | |
| MAR_READ | ✓ | ✓ | ✓ | ✓ | | | | | |
| MAR_WRITE | | | ✓ | | | | | | |
| ORDER_READ / ORDER_WRITE | ✓ | ✓ | | | ✓ | ✓ | | ✓ | |
| RESULTS_READ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | |
| RESULTS_RELEASE | | | | | ✓ | | | | |
| LAB_SPECIMEN_WRITE | | | | | ✓ | | | | |
| SCHEDULE_READ | ✓ | ✓ | ✓ | | | | | ✓ | |
| WORKLIST_READ | ✓ | ✓ | | | | | | ✓ | |
| PRIOR_AUTH_READ | ✓ | ✓ | | | | ✓ | | ✓ | |
| REPORT_READ / STUDY_READ / VIEWER_READ | ✓ | ✓ | ✓ | | | ✓ | ✓ | ✓ | |
| CODING_WRITE / BILLING_READ / BILLING_WRITE | | | | | | ✓ | | | |
| HIM_WRITE | | | | | | | ✓ | | |
| CARE_PLAN_WRITE | ✓ | ✓ | ✓ | | | | | ✓ | |
| AUDIT_READ | | | | | | | ✓ | | ✓ |
| USER_READ / USER_WRITE | | | | | | | | | ✓ |
| ROLE_READ / SERVICE_KEY_READ | | | | | | | | | ✓ |

> **EMR_ADMIN role scope:** role *creation/deletion* (`ROLE_WRITE`/`ROLE_DELETE`) is reserved for `TENANT_ADMIN`/`SYSTEM_ADMIN`; `EMR_ADMIN` covers user provisioning & role assignment via `USER_WRITE` (matches EMR-P11 "user/role management").
| INTERFACE_MONITOR / INTERFACE_ADMIN | | | | | | | | | ✓ |
| CDS_ADMIN / REPORT_TEMPLATE_ADMIN | | | | | | | | | ✓ |
| METERING_READ / TENANT_READ | | | | | | | | | ✓ |

> **PHYS addendum (physician walk, 2026-08-28):** code grants PHYS two legacy additions beyond the matrix row —
> `FILE_READ` (the always-visible Files page, held by every viewer role) and `DICOMWEB_READ` (intentional legacy reach,
> user decision 2026-08-27 — the DICOMweb console is open to clinical roles despite being an admin surface). Both are
> documented in `LEGACY_PHYSICIAN` (permissions.py).

### Matrix C — Platform roles

| Permission | SYSTEM_ADMIN | TENANT_ADMIN | PATIENT |
| :--- | :-: | :-: | :-: |
| ALL permissions (§3) | ✓ (immutable) | | |
| TENANT_READ, TENANT_ADMIN, METERING_READ | ✓ | ✓ | |
| USER_READ, USER_WRITE, ROLE_READ, ROLE_WRITE, SERVICE_KEY_* | ✓ | ✓ | |
| ROLE_DELETE | ✓ | ✓ | |
| AUDIT_READ, INTERFACE_MONITOR, INTERFACE_ADMIN | ✓ | ✓ | |
| STORAGE_ADMIN | ✓ | ✓ | |
| HL7_READ, ROUTING_READ, DICOMWEB_READ | ✓ | ✓ | |
| BILLING_READ, REPORT_TEMPLATE_ADMIN, CDS_ADMIN (roadmap-only) | ✓ | ✓ | |
| PATIENT_READ, ORDER_READ, WORKLIST_READ, REPORT_READ, STUDY_READ, VIEWER_READ, CHART_READ, RESULTS_READ | ✓ | ✓ | |
| PORTAL_READ, CHART_READ (own), RESULTS_READ (released), MED_ORDER_READ (own), SCHEDULE_READ (own), VIEWER_READ (share) | ✓ | | ✓ |
| **All clinical writes** (PATIENT_WRITE, ORDER_WRITE, REPORT_*, MAR_*, …) | ✓ | — (no clinical writes) | — |

---

## 6. Tenant Scoping & Cross-Tenant Policy

| Concern | Rule |
| :--- | :--- |
| Row-level isolation | Every clinical table carries `facility_id`; RLS policy `facility_id = app_current_facility_id()` (SELECT/INSERT/UPDATE/DELETE + `WITH CHECK`). Prod: `NOBYPASSRLS` + `FORCE ROW LEVEL SECURITY` on the app role. |
| Platform tables | `users`, `roles`, `permissions`, `role_permissions`, `tenant_plans` have **no RLS** (cross-tenant by nature). |
| Role grants | `user_roles` is facility-scoped: a user may be `RADIOLOGIST` at NGH and `TECHNOLOGIST` at the outreach clinic. Effective permissions computed per resolved facility (§2). |
| Cross-tenant priors / teleradiology | Never via default RLS. Two audited mechanisms: (1) an `XDS-I.b`/priors service running as the audited `BYPASSRLS` ops role; (2) **recommended v1**: `cross_tenant_grants` — explicit, time-boxed, read-only grants with scopes, enforced by an RLS OR-clause and audited with source+target facility. **Full DDL, RLS policies, audit policy & flows: `requrements/cross_tenant_grants_design.md`.** Access authorized < 1 s; `TELERADIOLOGIST` role activates only with a grant. |
| IDN enterprise scheduling | Cross-facility *schedule read* for schedulers with a `cross_tenant_grants` record; bookings still write to one facility. |
| Suspension | `SUSPENDED`/`CANCELLED` subscription → middleware login/read gate; RLS persists; legal hold honored before purge. |
| Password hashes | `users.password_hash` readable only by the auth service (column-level GRANT) — known gap, per schema §5.1. |
| Machine access | Modalities: AE-title + IP allow-list (no user roles). Service keys: permission-subset grants (AI: `STUDY_READ`, `RESULTS_READ`; ingestion: `FILE_WRITE`, `STUDY_READ`; integration: `INTERFACE_MONITOR`). |
| Token hygiene | Role/permission change → token_version bump → forced re-auth (frontend `super_admin` immutability enforced server-side too). |

---

## 7. Endpoint → Permission Map (enforcement)

| Endpoint group | Read | Write | Notes |
| :--- | :--- | :--- | :--- |
| `/api/worklist*` | WORKLIST_READ | WORKLIST_WRITE | existing (worklist_design.md) |
| `/api/files` (upload/list) | FILE_READ | FILE_WRITE | existing (uploads_design.md) |
| `/api/files/{id}/shares` | FILE_READ | FILE_WRITE | existing (share_design.md) |
| `/api/tenants*` | TENANT_READ | TENANT_ADMIN | existing (tenants_design.md) |
| `/api/roles*`, `/api/permissions` | ROLE_READ | ROLE_WRITE/ROLE_DELETE | existing (roles_design.md) |
| `/api/service-keys*` | SERVICE_KEY_READ | SERVICE_KEY_WRITE/DELETE | existing |
| `/api/logs*` | AUDIT_READ | — | existing (audit-logs_design.md) |
| `/account/profile`, `/change_password` | auth only (self) | auth only | existing (account_design.md) |
| `/api/patients*` | PATIENT_READ | PATIENT_WRITE / PATIENT_MERGE | NEW |
| `/api/orders*` | ORDER_READ | ORDER_WRITE | NEW |
| `/api/schedule*` | SCHEDULE_READ | SCHEDULE_WRITE | NEW |
| `/api/prior-auth*` | PRIOR_AUTH_READ | PRIOR_AUTH_WRITE | NEW |
| `/api/reports*` | REPORT_READ | REPORT_WRITE; `/sign` → REPORT_SIGN; `/critical` → CRITICAL_RESULTS_WRITE | NEW |
| `/api/billing*` | BILLING_READ | BILLING_WRITE / CODING_WRITE | NEW |
| `/dicomweb/studies*` (QIDO/WADO) | STUDY_READ / VIEWER_READ | STOW-RS → FILE_WRITE | NEW |
| `/api/export*` | — | STUDY_EXPORT | NEW |
| `/api/emr/encounter*` | CHART_READ | ENCOUNTER_WRITE / NOTE_SIGN | NEW |
| `/api/emr/mar*` | MAR_READ | MAR_WRITE | NEW |
| `/api/emr/meds*` | MED_ORDER_READ | MED_ORDER_WRITE / MED_VERIFY | NEW |
| `/api/emr/lab*` | RESULTS_READ | RESULTS_RELEASE / LAB_SPECIMEN_WRITE | NEW |
| `/api/emr/him*` | CHART_READ | HIM_WRITE | NEW |
| `/api/portal/*` | PORTAL_READ | — | NEW |
| `/api/cross-tenant-grants` (list/detail) | TENANT_ADMIN | — | NEW (contract: `requrements/cross_tenant_grants_api_contract.md`) |
| `/api/cross-tenant-grants` (create) + `/{id}/revoke` | — | ADMIN | NEW (contract: `requrements/cross_tenant_grants_api_contract.md`) |

---

## 8. Seeding SQL (migration; idempotent)

```sql
-- 8.1 New permissions
INSERT INTO permissions (code, description) VALUES
  ('TENANT_READ','View tenant info, usage, quota'),
  ('TENANT_ADMIN','Tenant config & lifecycle'),
  ('USER_READ','View users & role assignments'),
  ('USER_WRITE','Create/update/deactivate users, assign roles'),
  ('ROLE_READ','View roles & permissions'),
  ('ROLE_WRITE','Create/update custom roles & grants'),
  ('ROLE_DELETE','Delete custom roles'),
  ('SERVICE_KEY_READ','View service keys'),
  ('SERVICE_KEY_WRITE','Create/update service keys'),
  ('SERVICE_KEY_DELETE','Revoke service keys'),
  ('METERING_READ','View usage metering & invoices'),
  ('INTERFACE_ADMIN','Configure modalities, routing, endpoints'),
  ('PATIENT_MERGE','Merge MPI duplicate records'),
  ('MPI_ADMIN','Maintain patient identifiers/issuers'),
  ('SCHEDULE_READ','View schedules/appointments'),
  ('PRIOR_AUTH_READ','View prior-authorization status'),
  ('PRIOR_AUTH_WRITE','Request/update prior authorization'),
  ('CRITICAL_RESULTS_WRITE','Flag critical findings & tracked notifications'),
  ('REPORT_TEMPLATE_ADMIN','Manage report templates & hanging protocols'),
  ('BILLING_READ','View charges, claims, unbilled aging'),
  ('CODING_WRITE','Assign ICD-10/CPT/HCPCS'),
  ('STUDY_READ','Query/retrieve study metadata & pixels'),
  ('STUDY_EXPORT','Export studies (CD/XDS-I.b/anonymized)'),
  ('STORAGE_ADMIN','Retention, tiers, quotas, ILM'),
  ('CHART_READ','View full patient chart'),
  ('ENCOUNTER_WRITE','Encounter documentation & notes'),
  ('NOTE_SIGN','Sign/cosign notes'),
  ('MED_ORDER_READ','View medication orders'),
  ('MED_ORDER_WRITE','Order medications'),
  ('MED_VERIFY','Pharmacist verify/override'),
  ('MAR_READ','View MAR'),
  ('MAR_WRITE','Chart administrations (BCMA)'),
  ('RESULTS_READ','View lab/path/imaging results'),
  ('RESULTS_RELEASE','Release lab results, critical-value notify'),
  ('LAB_SPECIMEN_WRITE','Specimen accessioning'),
  ('CARE_PLAN_WRITE','Care plans & follow-up tasks'),
  ('HIM_WRITE','ROI, amendments, deficiency tracking'),
  ('CDS_ADMIN','Order sets & CDS rules'),
  ('PORTAL_READ','Patient portal self-service')
ON CONFLICT (code) DO NOTHING;

-- 8.2 New roles
INSERT INTO roles (code, name, description) VALUES
  ('TENANT_ADMIN','Tenant Admin','Tenant-scoped administrator'),
  ('PATIENT','Patient','Patient portal user'),
  ('TELERADIOLOGIST','Teleradiologist','Remote reader, engagement-gated scope'),
  ('ED_PHYSICIAN','ED Physician','Emergency view + critical alerts'),
  ('DEPARTMENT_MANAGER','Department Manager','Operational analytics'),
  ('PACS_ADMIN','PACS Administrator','Archive, routing, retention'),
  ('IMAGING_INFORMATICS','Imaging Informatics','Workflow & interoperability lead'),
  ('MEDICAL_CODER','Medical Coder','Coding & claims'),
  ('PHYSICIAN','Attending Physician','EMR clinical'),
  ('RESIDENT','Resident','EMR trainee (cosign)'),
  ('NURSE','Nurse','EMR nursing'),
  ('PHARMACIST','Pharmacist','EMR pharmacy'),
  ('LAB_TECHNICIAN','Lab Technician','EMR lab'),
  ('HIM_SPECIALIST','HIM Specialist','Medical records'),
  ('CARE_COORDINATOR','Care Coordinator','Care plans & transitions'),
  ('EMR_ADMIN','EMR/HIT Admin','EMR configuration')
ON CONFLICT (code) DO NOTHING;

-- 8.3 Grants (pattern per role; codes reference §3/§4). Example for two roles:
INSERT INTO role_permissions (role_id, permission_id)
SELECT r.role_id, p.permission_id
FROM roles r, permissions p
WHERE (r.code = 'RADIOLOGIST' AND p.code IN
         ('PATIENT_READ','ORDER_READ','WORKLIST_READ','REPORT_READ','REPORT_WRITE',
          'REPORT_SIGN','VIEWER_READ','STUDY_READ','CRITICAL_RESULTS_WRITE',
          'RESULTS_READ','CHART_READ','SCHEDULE_READ'))
   OR (r.code = 'NURSE' AND p.code IN
         ('CHART_READ','PATIENT_READ','ENCOUNTER_WRITE','NOTE_SIGN','MED_ORDER_READ',
          'MAR_READ','MAR_WRITE','RESULTS_READ','SCHEDULE_READ','CARE_PLAN_WRITE'));
-- Full per-role grant lists: §5 matrices (single source of truth); add remaining OR branches per matrix row.
```

---

## 9. Verification Checklist (tests to write)

- [ ] Every permission in §3 is granted to ≥1 non-SYSTEM_ADMIN role (no dead permissions).
- [ ] Every role has ≥1 permission; SYSTEM_ADMIN holds all 56.
- [ ] Endpoint→permission map (§7) covered by `@requires_permission` unit tests; unauthenticated/unauthorized → 401/403.
- [ ] Cross-facility access without a `cross_tenant_grants` record → denied + audited.
- [ ] user_roles facility-scoping: user with RADIOLOGIST@NGH + TECHNOLOGIST@Clinic sees NGH as radiologist, clinic as technologist.
- [ ] Permission change bumps token_version → next request re-authenticates.
- [ ] Tenant `SUSPENDED` blocks reads; `CANCELLED` respects legal hold.
- [ ] Matrices A/B/C match seed data after migration (write an assertion test against `role_permissions`).

---

## 10. Traceability (persona → role → requirement doc)

| Persona catalog entry | Role(s) | Requirements source |
| :--- | :--- | :--- |
| PAC-P01 / RIS-P01 | RADIOLOGIST | PACS/RIS `03_user_stories.md` P01 |
| PAC-P02 / RIS-P02 | TECHNOLOGIST | PACS/RIS P02 |
| PAC-P03 | TELERADIOLOGIST | PACS P03 |
| PAC-P04 | PACS_ADMIN | PACS P04 |
| PAC-P05 | IMAGING_INFORMATICS | PACS P05 |
| PAC-P06 / RIS-P08 | REFERRING_PHYSICIAN | PACS P06 / RIS P08 |
| PAC-P07 / RIS-P09 / EMR-P10 | ED_PHYSICIAN | PACS P07 / RIS P09 / EMR P10 |
| PAC-P08 / RIS-P07 | DEPARTMENT_MANAGER | PACS P08 / RIS P07 |
| RIS-P03 | SCHEDULER | RIS P03 |
| RIS-P04 / EMR-P06 | RECEPTIONIST | RIS P04 / EMR P06 |
| RIS-P05 | BILLER | RIS P05 |
| RIS-P06 | RADIOLOGY_ADMIN | RIS P06 |
| EMR-P01 | PHYSICIAN | EMR P01 |
| EMR-P02 | RESIDENT | EMR P02 |
| EMR-P03 | NURSE | EMR P03 |
| EMR-P04 | PHARMACIST | EMR P04 |
| EMR-P05 | LAB_TECHNICIAN | EMR P05 |
| EMR-P07 | MEDICAL_CODER | EMR P07 |
| EMR-P08 | HIM_SPECIALIST | EMR P08 |
| EMR-P09 | CARE_COORDINATOR | EMR P09 |
| EMR-P11 | EMR_ADMIN | EMR P11 |
| EMR-P12 | PATIENT | EMR P12 |
| P19 (all) | TENANT_ADMIN | PACS/RIS/EMR P19 |
| P20 (all) | SYSTEM_ADMIN | PACS/RIS/EMR P20 |
