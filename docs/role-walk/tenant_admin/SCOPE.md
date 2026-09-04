# tenant_admin — Intended Scope (Phase 1)
Date: 2026-08-28
Sources: navigator.ts, permissions.py, Sidebar.tsx (commits 0f1ff97)

## Role Profile

| Field | Value |
|---|---|
| Role slug | `tenant_admin` |
| Workspace | `platform` (from ROLE_WORKSPACE) |
| Scope class | admin-scoped (ADMIN_SCOPED_ROLES) |
| Landing route | `/admin` (Dashboard via DASHBOARD_STEP) |
| Grant set | `TENANT_ADMIN_PERMISSIONS = LEGACY_TENANT_ADMIN \| MATRIX_C_TENANT_ADMIN` |
| Excluded from | clinical workspaces (Reading, Acquisition, QA, Coordination, Front Desk, Portal) via NON_ADMIN_WORKSPACES |
| Tenant model | platform-side (tenant-scoped data access via grants, but user is platform-level) |
| Credential | `acme.tenant_admin` / `Test@123456` (seed_uat.py) |
| Relevant skills | iam-audit, multi-tenant-saas, postgres |

### Grant set (permissions.py:349-394)
```
LEGACY_TENANT_ADMIN = {
  FILE_READ, FILE_WRITE, REPLICA_READ, REPLICA_WRITE,
  LOG_READ, METRICS_READ,
}
MATRIX_C_TENANT_ADMIN = {
  TENANT_READ, TENANT_ADMIN, METERING_READ,
  USER_READ, USER_WRITE, ROLE_READ, ROLE_WRITE, ROLE_DELETE,
  SERVICE_KEY_READ, SERVICE_KEY_WRITE, SERVICE_KEY_DELETE,
  AUDIT_READ, INTERFACE_MONITOR, INTERFACE_ADMIN,
  STORAGE_ADMIN, BILLING_READ, REPORT_TEMPLATE_ADMIN, CDS_ADMIN,
  PATIENT_READ, ORDER_READ, WORKLIST_READ, REPORT_READ,
  STUDY_READ, VIEWER_READ, CHART_READ, RESULTS_READ,
  HL7_READ, ROUTING_READ, DICOMWEB_READ,
}
```
Note: no SYSTEM_ADMIN, no REPORT_WRITE, no SCHEDULE_READ, no EXAM_READ.

## Reachable Surfaces

| # | Section | UI Function | Route | Gate (permissions) | Intended (one line) |
|---|---|---|---|---|---|
| 1 | Admin | Dashboard | `/admin` | ADMIN_DASHBOARD_PERMISSIONS + adminOnly | Operational overview (widgets, recent activity, admin links) |
| 2 | Admin | RIS Dashboard | `/admin/ris-dashboard` | REPORT_READ + adminOnly | TAT, utilization, revenue, volume |
| 3 | Admin | Replicas | `/replicas` | REPLICA_READ | Storage replica management |
| 4 | Admin | Users | `/users` | USER_READ | User management CRUD |
| 5 | Admin | Tenants | `/tenants` | TENANT_READ | Tenant registry (manage tenants) |
| 6 | Admin | Roles | `/roles` | ROLE_READ | Role management CRUD |
| 7 | Admin | Logs | `/logs` | LOG_READ / AUDIT_READ | Audit log viewer |
| 8 | Admin | Service Keys | `/service-keys` | SERVICE_KEY_READ | API service key management |
| 9 | Admin | Routing | `/routing` | ROUTING_READ | HL7/interface routing rules |
| 10 | Admin | HL7 | `/hl7` | HL7_READ | HL7 message console |
| 11 | Admin | Interface Health | `/admin/interfaces` | HL7_READ + adminOnly | Interface monitoring dashboard |
| 12 | Admin | DICOMweb Server | `/dicomweb` | DICOMWEB_READ | DICOMweb server admin console |
| 13 | Admin | DICOMweb Store | `/dicomweb/store` | DICOMWEB_READ | STOW-RS upload console |
| 14 | Admin | DICOMweb Study Browser | `/dicomweb/browser` | DICOMWEB_READ | QIDO-RS study browser |
| 15 | Billing | Billing Queue | `/billing/queue` | BILLING_READ | Unbilled charges queue |
| 16 | Billing | Claims | `/billing/claims` | BILLING_READ | Claim lifecycle tracking |
| 17 | Billing | Revenue | `/billing/revenue` | BILLING_READ | Revenue trends + AR aging |
| 18 | Billing | Unbilled Aging | `/billing/unbilled` | BILLING_READ | Unbilled aging report |
| 19 | Billing | Denial Rework | `/billing/denials` | BILLING_READ | Denial management |
| 20 | Billing | Fee Schedule | `/billing/fee-schedule` | BILLING_READ | CPT fee schedule master data |
| 21 | Billing | Reconciliation | `/billing/reconciliation` | BILLING_READ | Signed-vs-charged reconciliation |
| 22 | Analytics | Metrics | `/metrics` | METRICS_READ/ANALYTICS_READ | System metrics dashboard |
| 23 | Files | File Browser | `/` | VIEWER_ROUTE_PERMISSIONS (FILE_READ/STUDY_READ/VIEWER_READ) | DICOM file browser |
| 24 | Files | Detail Viewer | `/files/:id` | VIEWER_ROUTE_PERMISSIONS | Cornerstone3D viewer |

## Not reachable (by design)
- **Report Templates** (`/admin/report-templates`): REPORT_WRITE not granted (has REPORT_TEMPLATE_ADMIN only)
- **Staff Schedule** (`/admin/staff-schedule`): SCHEDULE_READ not granted
- **FHIR** (`/fhir/*`): SYSTEM_ADMIN not granted
- **Integrations** (`/integrations`): SYSTEM_ADMIN not granted
- **Maintenance/Backups/Settings**: SYSTEM_ADMIN not granted
- **Clinical workspaces** (Reading, Acquisition, QA, Coordination, Front Desk, Portal): admin-scoped role excluded (NON_ADMIN_WORKSPACES)

## Skills invoked
Phase 1: `iam-audit` (file-fallback), `multi-tenant-saas` (file-fallback), `postgres` (file-fallback).