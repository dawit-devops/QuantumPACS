# Tenant Admin User Guide — QuantumPACS

Version: `feature/ris-integration` @ `964d21a` | Role: `tenant_admin` | Applies to: tenant-level operator

## 1. About this role

The **tenant_admin** is the operator account for a single tenant in a multi-tenant
QuantumPACS installation. It is a *tenant-scoped* role: it can manage users, roles,
service keys, DICOMweb, HL7 interfaces, billing, and logging within its own tenant
but cannot see or modify other tenants, system-level settings, or platform
infrastructure.

It is **not** a clinical role: by design it is excluded from the clinical workspaces
(Reading, Acquisition, QA, Coordination, Front Desk, Portal). Those surfaces belong
to radiologist/technologist/coordinator/front-desk/patient roles.

- **Landing page after sign-in**: **Dashboard** (`/admin`)
- **Tenant model**: scoped to a single tenant — the user sees only their own
  tenant's data in every surface.

## 2. Signing in

1. Go to the QuantumPACS URL (e.g. `http://localhost:5173`).
2. Enter username `test.tenant_admin` (or the deployed tenant-admin login) and the
   password, then pick the tenant (e.g. **acme** or **default**).
3. You land on the Admin Dashboard.

## 3. Getting around

The sidebar (Admin section + Billing + Metrics + Files + Account) is what this role sees:

| Section | Items |
|---|---|
| **Admin** | Report Templates, Dashboard, RIS Dashboard, Replicas, Users, Tenants, Roles, Logs, Service Keys, Routing, Integrations, HL7, Interface Health, DICOMweb (Server/Store/Study Browser) |
| **Billing** | Billing Queue, Claims, Revenue, Unbilled Aging, Denial Rework, Fee Schedule, Reconciliation |
| **Metrics** | Metrics |
| **Files** | Files (study/file browser) |
| **Account** | Account, Notifications (bell), Dark Mode, Logout |

## 4. Surface-by-surface guide

### 4.1 Admin Dashboard (`/admin`)
- **Purpose**: operational home — database/Redis/auth health, storage totals,
  patient/study/series counts, ingestion + modality charts, interface status,
  replica sync status, recent activity log.
- **How to**: sign in; the dashboard is the landing page. Use Refresh to reload.
- **Note**: Elasticsearch is not running in dev — search surfaces degrade gracefully.

### 4.2 RIS Dashboard (`/admin/ris-dashboard`)
- **Purpose**: department KPIs — turnaround time (TAT), provider workload, room
  activity, equipment utilization.
- **How to**: open from the Admin menu; 4 tabs: Overview (TAT by priority),
  Workload (by provider/modality/room), TAT Drill-Down, Equipment (requires
  EQUIPMENT_READ — not granted to tenant_admin; degrades gracefully).
- **Note**: Equipment tab shows "Missing permission: EQUIPMENT_READ" — this is
  expected graceful degradation.

### 4.3 Report Templates (`/admin/report-templates`)
- **Purpose**: manage structured report templates by modality (CR, CT, MR, etc.).
- **How to**: list all templates, click Edit to modify, click History to view
  versions. Paginated (11 pages of templates).
- **Actions**: edit, publish new version, rollback.

### 4.4 Replicas (`/replicas`)
- **Purpose**: view archive replica nodes and their sync status.
- **How to**: see active replicas with health, delay, and file count. The page
  auto-refreshes every 10 seconds.
- **Note**: Add/Update/Delete require REPLICA_WRITE/REPLICA_DELETE (not granted);
  buttons are conditionally hidden by `RequirePermission`.

### 4.5 Users (`/users`)
- **Purpose**: manage user accounts within the tenant.
- **How to**: list users with pagination, change roles via dropdown, reset
  passwords, deactivate/reactivate accounts, bulk import. Add User button
  creates new accounts.
- **Actions**: USER_WRITE granted — full CRUD available.

### 4.6 Tenants (`/tenants`)
- **Purpose**: view tenant details, health, and usage metrics.
- **How to**: see tenant card with user/study counts, last activity. Edit
  button opens tenant settings. Usage button shows metering panel.
- **Note**: Provision/Decommission are platform-only (super_admin). Suspend
  and Quarantine buttons are visible but 403 on write paths.

### 4.7 Roles (`/roles`)
- **Purpose**: manage permission sets (built-in and custom roles).
- **How to**: list all roles with permission summaries and user counts. Create
  Role button defines custom roles. Edit is available for non-built-in roles.
  Built-in roles (locked icon) are read-only.

### 4.8 Logs (`/logs`)
- **Purpose**: audit log of all platform events.
- **How to**: filter by event type (87+ event types), date range, tenant, actor.
  Live toggle auto-refreshes. Export button downloads all events as CSV.
  Pagination (25 pages, 87 total events).

### 4.9 Service Keys (`/service-keys`)
- **Purpose**: issue and revoke API credentials for external integrations
  (RIS, EMR, modalities).
- **How to**: Generate Key creates a new key with a one-time raw key display.
  Revoke removes active keys. Show Revoked toggle lists revoked keys.
- **Note**: SERVICE_KEY_WRITE and SERVICE_KEY_DELETE are granted.

### 4.10 Routing (`/routing`)
- **Purpose**: configure DICOM routing rules for incoming studies.
- **How to**: list rules with pagination. Create/Edit/Delete are visible but
  require ROUTING_WRITE (not granted) — read-only view.

### 4.11 Integrations (`/integrations`)
- **Purpose**: manage OAuth 2.0/OIDC providers for SSO and webhook event
  notifications.
- **How to**: OAuth Providers tab — list, add, edit, test, or delete OIDC
  providers. The Webhooks tab is hidden for tenant_admin (requires SYSTEM_ADMIN).
- **Note**: OIDC test-connection (ADM-16) is available via the Test button.

### 4.12 HL7 (`/hl7`)
- **Purpose**: monitor HL7v2 message traffic (ADT, ORM, etc.).
- **How to**: 3 tabs — Messages (filter by type/status/patient/facility, 1108
  messages), Analytics (metrics), Configuration (read-only; save requires
  HL7_WRITE which is not granted — 403 on save attempt).

### 4.13 Interface Health (`/admin/interfaces`)
- **Purpose**: monitor per-interface message counts, failures, latency, and
  the exception queue.
- **How to**: 2 tabs — Interfaces (2 active interfaces: HIS_FACILITY HL7_ADT
  and SENDING_FACILITY HL7_ORM with message counts and failure rates),
  Exception Queue (50 messages awaiting retry with Retry button — Retry
  requires HL7_WRITE, returns 403 for tenant_admin).

### 4.14 DICOMweb Server (`/dicomweb`)
- **Purpose**: view DICOMweb server capabilities and metrics.
- **How to**: 6 tabs — Endpoints (QIDO/WADO/STOW-RS), Search Parameters,
  Modalities (50 allowed), Metrics, Requests, Missing Features.

### 4.15 DICOMweb Store (`/dicomweb/store`)
- **Purpose**: upload DICOM files via STOW-RS.
- **How to**: upload form available; backend returns 403 (DICOMWEB_WRITE not
  granted to tenant_admin). Interface is read-only.

### 4.16 DICOMweb Study Browser (`/dicomweb/browser`)
- **Purpose**: search and retrieve DICOM studies.
- **How to**: search by patient name, date, modality, etc. Expand series and
  instances. WADO-RS renders images in the Cornerstone3D viewer. Download
  archive (ZIP). Weasis launch button.

### 4.17 Billing Queue (`/billing/queue`)
- **Purpose**: view pending billing charges.
- **How to**: paginated queue with CPT code suggestions and patient
  responsibility. Drop/Submit buttons visible but return 403
  (BILLING_WRITE not granted).

### 4.18 Claims (`/billing/claims`)
- **Purpose**: view submitted claims.
- **How to**: claim list with search, history drawer. Submit buttons return
  403.

### 4.19 Revenue (`/billing/revenue`)
- **Purpose**: collections trend, payer breakdown, modality breakdown.
- **How to**: 30-day summary cards (collected, AR aging), daily collections
  chart, paid-by-payer table, billed-by-modality table.

### 4.20 Unbilled Aging (`/billing/unbilled`)
- **Purpose**: aging report of unbilled charges.
- **How to**: group by date, site, or payer. Read-only view.

### 4.21 Denial Rework (`/billing/denials`)
- **Purpose**: denied claims queue.
- **How to**: denial list with history drawer. Import/Resubmit buttons return
  403.

### 4.22 Fee Schedule (`/billing/fee-schedule`)
- **Purpose**: fee schedule codes and payer contracts.
- **How to**: search by code, view payer contracts, comparison view.
  Edit/Import/Contract CRUD buttons return 403.

### 4.23 Reconciliation (`/billing/reconciliation`)
- **Purpose**: signed-vs-charged snapshot.
- **How to**: read-only view of reconciliation data.

### 4.24 Metrics (`/metrics`)
- **Purpose**: platform metrics summary.
- **How to**: totals cards, ingestion chart, modality distribution, system
  health.

### 4.25 Files (`/`)
- **Purpose**: browse and view DICOM studies.
- **How to**: search by patient name, date, modality. Click a study to open
  the viewer. Annotation and reading tools are hidden for admin-scoped roles
  (reduced-feature mode).

## 5. Common workflows (walkthroughs)

### 5.1 Create a user and assign a role
1. Navigate to **Users** (`/users`).
2. Click **Add user**.
3. Fill in username, display name, password, and select a role from the dropdown.
4. Click Save. The user appears in the list.
5. To change a role later, use the role dropdown in the users table.

### 5.2 Create an API service key
1. Navigate to **Service Keys** (`/service-keys`).
2. Click **Generate Key**.
3. Enter a name, service name, and optional permissions/per-expiry.
4. Copy the raw key shown (it will not be displayed again).
5. To revoke, click the **Revoke** button next to the key.

### 5.3 Configure an OIDC provider
1. Navigate to **Integrations** (`/integrations`).
2. Click the **OAuth Providers** tab.
3. Click **Add Provider**.
4. Enter the Issuer URL, Client ID, Client Secret, and optionally JWKS URI,
   Token URL, and Redirect URI.
5. Click Save. Use the **Test** button to verify the connection.
6. Toggle **Enabled** to activate SSO for the tenant.

### 5.4 Search DICOM studies
1. Navigate to **DICOMweb Study Browser** (`/dicomweb/browser`).
2. Enter a patient name, date range, or modality.
3. The results table shows matching studies. Click a row to expand series/instances.
4. Click **View** on an instance to open the Cornerstone3D viewer.

### 5.5 Export audit logs
1. Navigate to **Logs** (`/logs`).
2. Optionally filter by event type, date range, or actor.
3. Click **Export** to download all events as CSV.

## 6. Permissions summary

The tenant_admin role holds 35 permissions covering tenant-scoped administration:

| Permission | Surface | Write access? |
|---|---|---|
| AUDIT_READ | Logs | Read-only |
| BILLING_READ | Billing (all 7 surfaces) | Read-only (no BILLING_WRITE) |
| DICOMWEB_READ | DICOMweb (server, browser) | Read-only (no DICOMWEB_WRITE) |
| FILE_READ, FILE_WRITE | Files | Read + write |
| HL7_READ | HL7, Interface Health | Read-only (no HL7_WRITE) |
| INTERFACE_ADMIN, INTERFACE_MONITOR | Interface Health | Monitor-only |
| LOG_READ | Logs | Read-only |
| METERING_READ | Tenants (usage panel), Platform Usage | Read-only |
| METRICS_READ, ANALYTICS_READ | Metrics, Dashboard | Read-only |
| ORDER_READ | Orders (redirected) | Read-only (clinical route excluded) |
| PATIENT_READ | Patients (redirected) | Read-only (clinical route excluded) |
| REPLICA_READ | Replicas | Read-only (no REPLICA_WRITE) |
| REPORT_READ, REPORT_TEMPLATE_ADMIN | Report Templates, RIS Dashboard | Read + write |
| RESULT_READ | Results (redirected) | Read-only (clinical route excluded) |
| ROLE_READ, ROLE_WRITE, ROLE_DELETE | Roles | Full CRUD |
| ROUTING_READ | Routing | Read-only (no ROUTING_WRITE) |
| SERVICE_KEY_READ, SERVICE_KEY_WRITE, SERVICE_KEY_DELETE | Service Keys | Full CRUD |
| STUDY_READ | Study browser | Read-only |
| TENANT_ADMIN | OAuth Providers | Full CRUD |
| TENANT_READ | Tenants | Read-only (no TENANT_WRITE/DELETE) |
| USER_READ, USER_WRITE | Users | Full CRUD |
| VIEWER_READ | Files viewer | Read-only |
| WORKLIST_READ | Worklist (redirected) | Read-only (clinical route excluded) |

## 7. Troubleshooting & known limits

| Issue | Explanation |
|---|---|
| Equipment tab shows "Missing permission" | EQUIPMENT_READ not granted to tenant_admin — expected graceful degradation |
| HL7 config save fails with 403 | Config write requires HL7_WRITE (SYSTEM_ADMIN only) |
| Exception retry fails with 403 | Retry requires HL7_WRITE (SYSTEM_ADMIN only) — see walk finding F4 |
| Billing write buttons (Drop/Submit) return 403 | All billing mutations require BILLING_WRITE (not granted) |
| Provision/Decommission tenant returns 403 | Tenant lifecycle is platform-only (super_admin) |
| DICOMweb Store upload returns 403 | STOW-RS requires DICOMWEB_WRITE (not granted) |
| Maintenance/Backups/Settings pages redirect to /admin | SYSTEM_ADMIN-only surfaces |
| Clinical routes (reading, worklist, exams, etc.) redirect to /admin | Admin-scoped roles are excluded from clinical workspaces |
| Elasticsearch shows 0ms / degraded | ES not running in dev — no impact on core functionality |