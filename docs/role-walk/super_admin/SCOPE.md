# super_admin — Intended Scope (Phase 1)

Date: 2026-08-27
Sources: `frontend/src/navigator.ts`, `backend/api/permissions.py`, `frontend/src/common/Sidebar.tsx`

## Role Profile

| Field | Value |
|---|---|
| Role slug | `super_admin` |
| Workspace | `platform` (ROLE_WORKSPACE: `super_admin: "platform"`) |
| Scope class | admin-scoped (`ADMIN_SCOPED_ROLES` includes `super_admin`) |
| Landing route | `/admin` (DASHBOARD_STEP for admin-scoped roles; `ADMIN_DASHBOARD_PERMISSIONS` gate) |
| Grant set | ALL permissions — `SUPER_ADMIN_PERMISSIONS = {p.value for p in Permission}`; `admin: true` bypasses every gate; only role with `SYSTEM_ADMIN` |
| Excluded from | clinical workspaces (Reading/Acquisition/QA/Coordination/FrontDesk/Portal) via `ClinicalRoute` excludedRoles + `NON_ADMIN_WORKSPACES` sidebar filter |
| Tenant model | Platform owner: `TENANT_ADMIN` + `CROSS_TENANT_READ` — sees all tenant registry rows; data-plane calls remain tenant-scoped via `X-Tenant-ID`/tenant pool |
| Seeded login | `acme.super_admin` / `Test@123456` |

## Reachable Surfaces (sidebar order, Admin section then Metrics)

| # | Section | UI Function | Route | Gate (permissions) | Intended (operational, wearing the role) |
|---|---|---|---|---|---|
| 1 | Admin | Report Templates | `/admin/report-templates` | `REPORT_WRITE` | Manage report template library (create/edit/delete templates used by radiologists) |
| 2 | Admin | Dashboard | `/admin` | `ADMIN_DASHBOARD_PERMISSIONS` (adminOnly) | Operational home: platform health (DB/ES/Redis/auth), storage totals, users, DICOMweb reqs, ingestion charts, interface status, replicas, recent activity |
| 3 | Admin | RIS Dashboard | `/admin/ris-dashboard` | `REPORT_READ` (adminOnly) | RIS operational oversight: TAT, utilization, volume, unbilled aging |
| 4 | Admin | Staff Schedule | `/admin/staff-schedule` | `SCHEDULE_READ` (adminOnly) | Staff shift assignments, time-off requests, coverage-gap detection (DM-07) |
| 5 | Admin | Replicas | `/replicas` | `REPLICA_READ` | Replica node registry + sync state (LISTEN/NOTIFY driven) |
| 6 | Admin | Users | `/users` | `USER_READ` | Platform user management: list/search, create, assign role + tenant, reset PW, deactivate, delete |
| 7 | Admin | Tenants | `/tenants` | `TENANT_READ` | Core multi-tenant SaaS surface: list all tenants, create (DB provisioning), edit storage/quota, deactivate; shows storage_used_bytes etc. |
| 8 | Admin | Roles | `/roles` | `ROLE_READ` | View permission matrix, create/edit role grants, delete unused roles |
| 9 | Admin | Logs | `/logs` | `LOG_READ` / `AUDIT_READ` | Audit + app log stream |
| 10 | Admin | Service Keys | `/service-keys` | `SERVICE_KEY_READ` | Platform API keys for SI/integrations: create/revoke/rotate |
| 11 | Admin | Routing | `/routing` | `ROUTING_READ` | AE title / DICOM routing table |
| 12 | Admin | FHIR | `/fhir/config`, `/fhir/monitoring`, `/fhir/docs` | `SYSTEM_ADMIN` | FHIR server config, monitoring, docs |
| 13 | Admin | Integrations | `/integrations` | `SYSTEM_ADMIN` | Integration registry (webhooks, connectors) |
| 14 | Admin | HL7 | `/hl7` | `HL7_READ` | HL7 interface console |
| 15 | Admin | Interface Health | `/admin/interfaces` | `HL7_READ` (adminOnly) | Endpoint/interface monitor |
| 16 | Admin | Maintenance | `/admin/maintenance` | `SYSTEM_ADMIN` | Platform maintenance mode, system tasks |
| 17 | Admin | Backups | `/admin/backups` | `SYSTEM_ADMIN` | Backup registry, trigger/restore, retention |
| 18 | Admin | Settings | `/admin/settings` | `SYSTEM_ADMIN` | Whitelisted platform config overrides (P2-3) |
| 19 | Admin | DICOMweb | `/dicomweb` (Server), `/dicomweb/store` (STOW-RS), `/dicomweb/browser` (Study Browser) | `DICOMWEB_READ` (adminOnly) | DICOMweb server console, STOW-RS store, study browser |
| 20 | Metrics | Metrics | `/metrics` | `METRICS_READ` / `ANALYTICS_READ` | Platform metrics dashboards |
| 21 | Files | Files | `/` | `FILE_READ` / `STUDY_READ` | File/study browser (always-visible entry) |
| 22 | Account | Account | `/account` | — | Profile, password change, session |
| 23 | Notifications | Notifications bell | — | — | In-app notification feed |

## Not reachable (by design)

- Clinical workspaces: Reading (`/reading*`, `/teaching`, `/peer-review`, `/critical`), Acquisition (`/exams`, `/worklist`, `/tracking`, `/schedule*`), QA (`/qa/*`), Coordination (`/orders`, `/prior-auth`, `/reminders`, `/care-plans`, `/communications`, `/nursing`), Front Desk (`/frontdesk/*`), Portal (`/portal*`) — excluded via `NON_ADMIN_WORKSPACES` sidebar filter + `ClinicalRoute` excludedRoles, even though super_admin holds every permission.
- **Billing was opened to admin roles by user decision (`bf792dd`)** — the 7 billing surfaces (Queue/Claims/Revenue/Unbilled/Denials/Fee-Schedule/Reconciliation) are now reachable; this section predates that decision.

## Notes for the walk

- The dashboard gate is `ADMIN_DASHBOARD_PERMISSIONS` (union of read perms) — super_admin passes trivially.
- `SYSTEM_ADMIN`-gated items (FHIR, Integrations, Maintenance, Backups, Settings) are super_admin-only in practice (the only built-in role holding SYSTEM_ADMIN).
- Tenant data-plane isolation is the critical correctness property for this role: it can see all tenants in the registry but must stay scoped to the active tenant on data-plane reads.
