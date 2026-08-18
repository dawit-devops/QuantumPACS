# 00 — Super Admin Surface Inventory

Role: `super_admin` — every permission (`SUPER_ADMIN_PERMISSIONS = {p.value for p in Permission}`, backend/api/permissions.py:351) + legacy `admin` JWT flag
Landing: `/admin` (Operations Dashboard — navigator.ts `DASHBOARD_STEP`, admin-scoped roles)
Workspace: `platform` (ROLE_WORKSPACE) → dashboard workspace (sidebar auto-opens Admin)
Login: `test.super_admin` / `Test@123456` (seed_test_users.py; `admin=true`, id 36)
Scope: admin-scoped (`ADMIN_SCOPED_ROLES`); clinical/front-desk/portal surfaces are hidden by `ClinicalRoute` exclusion + `NON_ADMIN_WORKSPACES` sidebar filter

## Reachable surfaces (walked live, 2026-08-14, headless Chromium 1440×900)

| # | Route | Page | Permission gate | Walkthrough result |
|---|-------|------|-----------------|--------------------|
| 1 | `/admin` | AdminDashboard (frontend/src/dashboard/AdminDashboard.tsx) | ADMIN_DASHBOARD_PERMISSIONS + adminOnly | Loads. Health strip (Database/ES/Redis/Storage/DICOM Listener/Ingestion/HL7/FHIR/Auth — all OK), KPI cards (Patients 17, Studies 17, Series 18, Files 20, Users 23, Storage 9.4 MB, DICOMweb Requests), Ingestion-30d + Modality charts, Interfaces panel, Replicas panel, Recent Activity (audit), Quick Links, auto-refresh toggle. Evidence: `02-admin-dashboard.png` |
| 2 | `/users` | Users (frontend/src/users/Users.tsx) | USER_READ | Loads. Search, table, Create User modal (validated), Edit role, Reset password, Deactivate, Bulk import. Evidence: `03-users.png`, `22-users-create.png` |
| 3 | `/roles` | Roles (frontend/src/roles/Roles.tsx) | ROLE_READ | Loads. 14 built-in roles + permission-chip summary (+N more), Create Role, Edit per role with R2-16 immutability tiers — System Admin row Edit disabled with tooltip "Cannot modify immutable built-in role". Evidence: `04-roles.png` |
| 4 | `/tenants` | Tenants (frontend/src/tenants/Tenants.tsx) | TENANT_READ | Loads. 2 tenants (`default`, `hf` — free plan, Active, storage 0 B / 500.0 GB @ 0%). Per-tenant Edit/Usage/Suspend/Quarantine/Decommission (destructive actions behind Popconfirm). Provision Tenant button. Evidence: `05-tenants.png` |
| 5 | `/replicas` | Replicas (frontend/src/replicas/Replicas.tsx) | REPLICA_READ | Loads. "No replicas configured" empty state, Add replica. Evidence: `06-replicas.png` |
| 6 | `/logs` | Logs (frontend/src/logs/Logs.tsx) | LOG_READ / AUDIT_READ | Loads. 2280 total events. Event-type filter chips (grouped), date range, tenant filter (TENANT_READ-gated), actor autocomplete, Live tail (5s poll, row highlight), CSV export, expandable rows with full JSON payload. Evidence: `07-logs.png` |
| 7 | `/service-keys` | ServiceKeys (frontend/src/servicekeys/ServiceKeys.tsx) | SERVICE_KEY_READ | Loads. Generate Key modal (validated name/service name, permission checkbox groups, expiry), one-time key Alert with Copy + "will not be shown again", Revoke behind Popconfirm, expiry/status tags, Show-revoked switch. Evidence: `08-service-keys.png` |
| 8 | `/routing` | RoutingRules (frontend/src/routing/RoutingRules.tsx) | ROUTING_READ | Loads. Routing rules list + rule editor/condition builder. Evidence: `09-routing.png` |
| 9 | `/fhir/config` | FhirConfig (frontend/src/fhir/FhirConfig.tsx) | SYSTEM_ADMIN | Loads. FHIR R4 server config (Base URL, Publisher, Max Search Results, Log Retention), Save + Test Connection, SMART-on-FHIR client registry ("No clients configured" empty state, Register). Evidence: `10-fhir-config.png` |
| 10 | `/fhir/monitoring` | FhirMonitoring (frontend/src/fhir/FhirMonitoring.tsx) | SYSTEM_ADMIN | Loads. 62 requests/24h, 0% error rate, p50 11ms / p99 710ms, request volume by resource+method, status families, recent-requests table, Export CSV. Evidence: `11-fhir-monitoring.png` |
| 11 | `/fhir/docs` | FhirDocs (frontend/src/fhir/FhirDocs.tsx) | SYSTEM_ADMIN | Loads. Capability Statement (FHIR 4.0.1, Patient/ImagingStudy/DocumentReference), Copy, "Try It" Patient read. Evidence: `12-fhir-docs.png` |
| 12 | `/integrations` | Integrations (frontend/src/integrations/Integrations.tsx) | SYSTEM_ADMIN | Loads. Webhooks tab (0 configured, Add Webhook, test endpoint) + OAuth Providers tab. Evidence: `13-integrations.png` |
| 13 | `/hl7` | Hl7Dashboard (frontend/src/hl7/Hl7Dashboard.tsx) | HL7_READ | Loads. Tabs Messages / Analytics / Configuration. 1 real ORM-O01 message (Parsed), type/status filters, Refresh, View detail. Evidence: `14-hl7.png` |
| 14 | `/dicomweb` | DicomWebAdmin (frontend/src/dicomweb/DicomWebAdmin.tsx) | DICOMWEB_READ (admin console) | Loads. QIDO/WADO/STOW service cards (Enabled, formats, pagination, 50 valid modalities), tabs Endpoints / Search Parameters / Modalities / Metrics / Requests / Missing Features. Evidence: `15-dicomweb.png` |
| 15 | `/dicomweb/store` | StowUpload (frontend/src/dicomweb/StowUpload.tsx) | DICOMWEB_READ | Loads. Drag-drop .dcm zone (client-side extension validation with warning), Store to PACS, Result summary (stored/failed). Evidence: `16-dicomweb-store.png` |
| 16 | `/dicomweb/browser` | StudyBrowser (frontend/src/dicomweb/StudyBrowser.tsx) | DICOMWEB_READ | Loads. Patient ID search, Clear, study table. Evidence: `17-dicomweb-browser.png` |
| 17 | `/metrics` | Metrics (frontend/src/metrics/Metrics.tsx) | METRICS_READ / ANALYTICS_READ | Loads. System health (all OK), 24h/7d/30d/90d ranges, KPI cards, modality distribution, component latency, ingestion chart, Latest Files. Evidence: `18-metrics.png` |
| 18 | `/` | Files (frontend/src/files/Files.tsx) | VIEWER_ROUTE_PERMISSIONS | Loads. Search/Advanced/Upload, 11 rows real studies, pagination, Download files / Download data. Evidence: `19-files.png` |
| 19 | `/account` | Account (frontend/src/account/Account.tsx) | auth | Loads. Profile, Edit, Change Password (current/new/confirm). Evidence: `20-account.png` |
| 20 | Notifications bell | NotificationBell (frontend/src/notifications/NotificationBell.tsx) | — | Drawer opens; **49 unread `study.arrived`** notifications ("Study arrived for E2E^MOBILE/…"), Read all / Dismiss all. Evidence: `21-notifications.png` |

## Admin-scope denial probes (must bounce an admin-scoped role)

All 8 clinical/front-desk/portal surfaces redirect to `/admin` — the role-scope gates work end to end:
`/reading`, `/exams`, `/qa/queue`, `/frontdesk/registration`, `/portal`, `/worklist`, `/schedule-board`, `/peer-review`.

## Sidebar visible to super_admin

`Files`, `Account`, **Admin** (Dashboard, Replicas, Users, Tenants, Roles, Logs, Service Keys, Routing, FHIR ▸ Config/Monitoring/Docs, Integrations, HL7, DICOMweb ▸ Server/Store/Browser), **Metrics**, Notifications, theme toggle, Logout. Clinical sections (Reading/Acquisition/QA), Front Desk and My Records are correctly hidden. Evidence: `01-sidebar.png`.

## API calls observed (network)

All surfaces load with **zero 4xx/5xx and zero failed requests**. Representative calls: `GET /api/v2/dashboard/health|metrics`, `GET /api/users`, `GET /api/roles`, `GET /api/permissions`, `GET /api/tenants`, `GET /api/tenants/health`, `GET /api/logs`, `GET /api/logs/actors`, `GET /api/api-keys`, `GET /api/routing`, `GET /api/fhir/admin/config|clients|metrics|requests`, `GET /api/webhooks`, `GET /api/oauth/providers`, `GET /api/hl7/admin/config|messages|metrics|status`, `GET /api/dicomweb/admin*`, `GET /api/notifications*`.

## Console issues

- `Warning: [antd: Statistic] \`valueStyle\` is deprecated. Please use \`styles.content\` instead.` (DICOMweb metrics tab, metrics page)
- `Warning: [antd: Table] \`index\` parameter of \`rowKey\` function is deprecated.`
- `Each child in a list should have a unique "key" prop … Check the render method of \`tbody\`.` (a table render — Files/metrics "Latest Files")
- No JS page errors on any surface.
