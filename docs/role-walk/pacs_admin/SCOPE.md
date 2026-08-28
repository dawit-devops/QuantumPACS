# pacs_admin — Intended Scope (Phase 1)
Date: 2026-08-28
Sources: navigator.ts, permissions.py (MATRIX_A_PACSADM), Sidebar.tsx, RBAC_matrix_spec.md §5 (Matrix A)
Skills invoked: iam-audit, multi-tenant-saas, postgres

## Role Profile

| Field | Value |
|---|---|
| Role slug | `pacs_admin` |
| Workspace | `admin` (from ROLE_WORKSPACE) |
| Scope class | admin-scoped (`ADMIN_SCOPED_ROLES`) |
| Landing route | `/admin` (dashboard — has USER_READ/AUDIT_READ/INTERFACE_MONITOR from ADMIN_DASHBOARD_PERMISSIONS) |
| Grant set | MATRIX_A_PACSADM (24 permissions) |
| Excluded from | All clinical surfaces (Reading/Acquisition/QA/Coordination/FrontDesk/Portal) via `NON_ADMIN_WORKSPACES` |
| Tenant model | platform-side (tenant=NULL for test.pacs_admin) |
| Credential used | `test.pacs_admin` / `Test@123456` (platform-side, no tenant scope) |
| Relevant skills | iam-audit, multi-tenant-saas, postgres |

## Reachable Surfaces (sidebar-visible, 15 surfaces)

| # | Section | UI Function | Route | Gate (permissions) | Intended (one line) |
|---|---|---|---|---|---|
| 1 | — | Files | `/` | FILE_READ, STUDY_READ, VIEWER_READ | Browse/upload/view DICOM files and studies |
| 2 | Admin | Dashboard | `/admin` | ADMIN_DASHBOARD_PERMISSIONS | Platform health, KPI cards, charts, replicas, activity, quick links |
| 3 | Admin | RIS Dashboard | `/admin/ris-dashboard` | REPORT_READ | TAT, utilization, volume, workload drill-down |
| 4 | Admin | Staff Schedule | `/admin/staff-schedule` | SCHEDULE_READ | View shift assignments, time-off, coverage |
| 5 | Admin | Report Templates | `/admin/report-templates` | REPORT_WRITE, REPORT_TEMPLATE_ADMIN | List templates, versions, publish, rollback |
| 6 | Admin | Users | `/users` | USER_READ | List/create/deactivate users, assign roles, reset passwords |
| 7 | Admin | Roles | `/roles` | ROLE_READ | List roles, permissions, create/edit/delete custom roles (R2-16) |
| 8 | Admin | Logs | `/logs` | LOG_READ, AUDIT_READ | Audit log with filters, cursor pagination, CSV export |
| 9 | Billing | Billing Queue | `/billing/queue` | BILLING_READ | Paginated queue, CPT suggestions, patient responsibility |
| 10 | Billing | Claims | `/billing/claims` | BILLING_READ | Claim list, history drawer |
| 11 | Billing | Revenue | `/billing/revenue` | BILLING_READ | Collections trend, payer/modality breakdown |
| 12 | Billing | Unbilled Aging | `/billing/unbilled` | BILLING_READ | Aging report with grouping |
| 13 | Billing | Denial Rework | `/billing/denials` | BILLING_READ | Denial list, history |
| 14 | Billing | Fee Schedule | `/billing/fee-schedule` | BILLING_READ | Fee schedule list, payer contracts, comparison |
| 15 | Billing | Reconciliation | `/billing/reconciliation` | BILLING_READ | Signed-vs-charged snapshot |

## Not reachable (by design — admin-scoped hides clinical)

| Surface | Reason |
|---|---|
| Reading worklist, Teaching Library, Peer Review, Critical Results | Admin-scoped → clinical workspace hidden |
| Exams, Modality Worklist, Tracking Board, Schedule Board, Calendar, Resources | Admin-scoped → acquisition workspace hidden |
| QA Queue, Protocols, Incidents, Corrective Actions, Analytics | Admin-scoped → QA workspace hidden |
| Orders, Prior Auth, Reminders, Care Plans, Communications, Nursing Prep | Admin-scoped → coordination workspace hidden |
| Front Desk (Registration, Schedule, Queue, Patient Search) | Admin-scoped → frontdesk workspace hidden |
| Portal (Records, Appointments, Results, Follow-ups) | Admin-scoped → portal workspace hidden |

## Not reachable (permission denied — no route gate grant)

| Surface | Route | Required | pacs_admin has? |
|---|---|---|---|
| Replicas | `/replicas` | REPLICA_READ | No |
| Tenants | `/tenants` | TENANT_READ | No |
| Service Keys | `/service-keys` | SERVICE_KEY_READ | No |
| Routing | `/routing` | ROUTING_READ | No |
| FHIR | `/fhir/*` | SYSTEM_ADMIN | No |
| Integrations | `/integrations` | SYSTEM_ADMIN, TENANT_ADMIN | No |
| HL7 | `/hl7` | HL7_READ | No |
| Interface Health | `/admin/interfaces` | HL7_READ | No |
| DICOMweb (Server/Store/Browser) | `/dicomweb*` | DICOMWEB_READ | No |
| Maintenance/Backups/Settings | `/admin/maintenance` etc. | SYSTEM_ADMIN | No |
| Metrics | `/metrics` | METRICS_READ, ANALYTICS_READ | No |

## Key observations (Phase 2 candidates)

1. **pacs_admin holds STORAGE_ADMIN, INTERFACE_ADMIN, INTERFACE_MONITOR — but these gate zero backend endpoints** (dead grants). The DICOMweb console, HL7 console, Interface Health, Replicas, and Routing — the actual PACS-ops surfaces — all gate on DICOMWEB_READ/HL7_READ/REPLICA_READ/ROUTING_READ which pacs_admin lacks. Same dead-grant pattern as tenant_admin's O2 (STORAGE_ADMIN/CDS_ADMIN).

2. **pacs_admin has CRITICAL_RESULTS_WRITE** — RBAC spec Matrix A PACSADM row shows blank for this, but code MATRIX_A_PACSADM includes it. Spec drift.

3. **pacs_admin has BILLING_READ** — sees all 7 billing surfaces. This is per spec Matrix A (BILLING_READ ✓). Whether a PACS administrator should be a billing-reader is a product question.

4. **pacs_admin has SCHEDULE_READ, REPORT_READ, WORKLIST_READ** — but the clinical surfaces are hidden (admin-scoped), so these are also dead grants for the nav sidebar. They may be used by backend endpoints called from the admin surfaces (e.g., RIS Dashboard REPORT_READ).

5. **pacs_admin has no METRICS_READ/ANALYTICS_READ** — Metrics page (/metrics) is unreachable. Spec shows PACSADM with no METRICS either.

## Completion criteria
- [x] Role profile card filled from source of truth.
- [x] SCOPE.md lists every reachable route with gate + intended behavior.
- [x] Key observations noted for Phase 2 gap analysis.