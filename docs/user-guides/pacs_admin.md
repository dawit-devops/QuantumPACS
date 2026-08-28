# PACS Administrator (pacs_admin) User Guide — QuantumPACS
Version: 19012b3 | Role: pacs_admin | Applies to: facility/tenant scope

## 1. About this role

The **PACS Administrator** operates the imaging archive and interface
infrastructure for the facility. You manage who can access the system (users,
roles, operational staff), monitor the DICOM and HL7 interfaces, watch storage
replication, and keep the archive healthy — but you do **not** perform clinical
work (no reading, no QA, no exam acquisition).

You land on the **Operations Dashboard** (`/admin`) when you sign in.

Key responsibility split:
- **You own:** users, roles, logs, report templates, staff schedules, DICOMweb
  server/STOW/browser, HL7 console, interface health, replicas, routing, and
  read-only billing views.
- **Platform admin (super_admin) owns:** tenants, service keys, FHIR config,
  maintenance/backups/settings, platform-wide provisioning.
- **Clinical staff own:** reading, exams, QA, scheduling, front desk, portal.

## 2. Signing in

1. Go to the QuantumPACS login page.
2. Enter your username (e.g. `test.pacs_admin` in dev) and password.
3. Sign in. You land on the **Operations Dashboard**.
4. If you see a **Tenant** selector, choose your facility (if you are a
   platform-side account you won't see one).

If you forget your password, an administrator with `USER_WRITE` can reset it.

## 3. Getting around

The sidebar (dark, left) shows the sections you can reach:

| Section | What you can do there |
|---|---|
| **Files** | Browse, view, and upload DICOM studies and files |
| **Admin** | Dashboard, RIS Dashboard, Staff Schedule, Report Templates, Replicas, Users, Roles, Logs, Routing, HL7, Interface Health, DICOMweb |
| **Billing** | Queue, Claims, Revenue, Unbilled Aging, Denial Rework, Fee Schedule, Reconciliation (read-only) |
| **Metrics** | System metrics and analytics (via the Metrics menu) |
| **Account** | Your profile and preferences |

The Admin section is open by default (it owns your landing page).

## 4. Surface-by-surface guide

### 4.1 Operations Dashboard (`/admin`)
- **Purpose:** live system health, storage totals, recent platform activity.
- **How to:** view the health strip (Database/Elasticsearch/Redis/FHIR/Auth
  latency), KPI cards (patients, studies, series, files, storage, users,
  DICOMweb requests), ingestion and modality charts, interface status,
  replicas, and recent activity. Toggle **Auto-refresh** or press **Refresh**.
- **Status:** PASS
- **Notes:** KPI numbers reflect your tenant scope; a platform-side account
  sees platform totals.

### 4.2 RIS Dashboard (`/admin/ris-dashboard`)
- **Purpose:** department analytics — TAT by priority, workload, utilization,
  volume.
- **How to:** use the tabs **Overview**, **Workload**, **TAT Drill-Down**,
  **Equipment**. Overview shows KPI cards (today's volume, utilization,
  unbilled, prior-auth status, claim denial rate, STAT p95 TAT) and a report
  TAT-by-priority table.
- **Status:** PASS
- **Notes:** Equipment tab degrades gracefully if you lack `EQUIPMENT_READ`
  (or you hold it via the operational grants — check your grants).

### 4.3 Staff Schedule (`/admin/staff-schedule`)
- **Purpose:** view shift assignments, time-off requests, and coverage gaps.
- **Status:** PASS (read-only for you unless you hold `SCHEDULE_WRITE`).

### 4.4 Report Templates (`/admin/report-templates`)
- **Purpose:** manage the report template library used by radiologists.
- **How to:** list templates, view version history, publish a new version,
  roll back.
- **Status:** PASS
- **Notes:** You hold `REPORT_TEMPLATE_ADMIN`, so publish/rollback work.

### 4.5 Replicas (`/replicas`)
- **Purpose:** monitor archive replication nodes and sync status.
- **How to:** view the replica table (ID, type, role, health, location, delay,
  files, sync progress).
- **Status:** PASS
- **Notes:** You hold `REPLICA_READ`. Creating/deleting replicas requires
  `REPLICA_WRITE` (not granted) — those actions return 403.

### 4.6 Users (`/users`)
- **Purpose:** manage user accounts and role assignments.
- **How to:** list users with filters/pagination, create users, assign roles,
  deactivate, reset passwords, batch status updates.
- **Status:** PASS
- **Notes:** You hold `USER_READ` + `USER_WRITE`. You can assign the
  **operational built-in roles** (technologist, receptionist, cashier,
  care_coordinator, dept_manager) and the pacs_admin role. You **cannot**
  assign clinical readers/EMR writers (radiologist, physician) — those grants
  exceed your own. You cannot create admin-flagged users (platform-only).

### 4.7 Roles (`/roles`)
- **Purpose:** view the role/permission matrix, create/edit/delete custom roles
  (built-in roles are protected from deletion).
- **How to:** list roles, view permission groups, create a custom role, edit
  non-built-in roles, view a role's users.
- **Status:** PASS
- **Notes:** You hold `ROLE_READ/WRITE/DELETE`.

### 4.8 Logs (`/logs`)
- **Purpose:** audit and application logs.
- **How to:** filter by event type, actor, date range; cursor pagination; CSV
  export.
- **Status:** PASS

### 4.9 DICOMweb Server (`/dicomweb`)
- **Purpose:** DICOMweb server configuration and status.
- **How to:** view the Endpoints / Search Parameters / Modalities / Metrics /
  Requests / Missing Features tabs. QIDO-RS, WADO-RS, and STOW-RS status,
  formats, and transfer syntaxes are shown.
- **Status:** PASS (you hold `DICOMWEB_READ`)

### 4.10 DICOMweb Store / STOW-RS (`/dicomweb/store`)
- **Purpose:** upload DICOM instances to the archive via STOW-RS.
- **Status:** PASS (you hold `DICOMWEB_WRITE`)

### 4.11 DICOMweb Study Browser (`/dicomweb/browser`)
- **Purpose:** search studies, expand series/instances, WADO-RS render, archive
  download, Weasis launch.
- **Status:** PASS

### 4.12 HL7 (`/hl7`)
- **Purpose:** HL7 interface console — messages, analytics, configuration.
- **How to:** Messages tab lists HL7 messages (filter by type/status, search by
  patient ID/facility, view details). Analytics shows message metrics.
  Configuration is **read-only** for you (saving requires `HL7_WRITE`, not
  granted → 403).
- **Status:** PASS

### 4.13 Interface Health (`/admin/interfaces`)
- **Purpose:** per-interface health — list, message browser, metrics,
  exception queue.
- **Status:** PASS (you hold `HL7_READ` via the console grant)
- **Notes:** Replaying a failed exception requires `HL7_WRITE` (not granted).

### 4.14 Routing (`/routing`)
- **Purpose:** DICOM AE routing table.
- **Status:** PASS (read-only — you hold `ROUTING_READ`; edits need
  `ROUTING_WRITE`).

### 4.15 Billing (read-only) — Queue / Claims / Revenue / Unbilled / Denials / Fee Schedule / Reconciliation
- **Purpose:** monitor the billing workflow.
- **How to:** Billing Queue lists unbilled charges (CPT suggestions, patient
  responsibility); Claims shows claim lifecycle; Revenue shows collections;
  Unbilled shows aging; Denials shows rework; Fee Schedule shows CPT codes and
  payer contracts; Reconciliation shows signed-vs-charged snapshot.
- **Status:** PASS
- **Notes:** You hold `BILLING_READ` only. Drop/submit/import/edit actions
  return 403 (need `BILLING_WRITE`).

### 4.16 Files (`/`)
- **Purpose:** browse/upload/view DICOM files and studies.
- **Status:** PASS

## 5. Common workflows (walkthroughs)

### 5.1 Create a technologist user
1. Go to **Users** (`/users`).
2. Click **Create user**.
3. Enter username + password; choose role **technologist** (or receptionist /
   cashier / care_coordinator / dept_manager / pacs_admin).
4. Save — the password is shown once; share it securely with the user.
5. Deactivate via the user row if the person leaves.

### 5.2 Check archive + interface health daily
1. Land on **Operations Dashboard** (`/admin`): review the health strip and
   replicas panel.
2. Open **Interface Health** (`/admin/interfaces`): confirm each interface is
   green; open the exception queue and note any failed messages (a facility
   admin with `HL7_WRITE` replays them).
3. Open **HL7** (`/hl7`): review recent message status for parse failures.
4. Open **DICOMweb Server** (`/dicomweb`): check the Requests tab for failed
   QIDO/STOW/WADO calls.

### 5.3 Publish a new report template
1. Go to **Report Templates** (`/admin/report-templates`).
2. Select the template; open its versions.
3. Click **Publish** to snapshot + activate a new version (or **Rollback** to
   revert).
4. Confirm radiologists see the new version.

### 5.4 Verify a DICOM study was stored
1. Open **DICOMweb Study Browser** (`/dicomweb/browser`).
2. Search by patient name / study date.
3. Expand the study → series → instances; render a WADO-RS preview, download
   the archive ZIP, or launch Weasis.

### 5.5 Monitor billing capture (read-only)
1. Open **Billing Queue** (`/billing/queue`): confirm no large unbilled
   backlog.
2. Open **Unbilled Aging** (`/billing/unbilled`): review aging groups.
3. Open **Revenue** (`/billing/revenue`): review collections trend.
4. Flag issues to a billing user (only `BILLING_WRITE` holders can act).

## 6. Permissions summary

You can (selected):
- **Users/Roles:** USER_READ, USER_WRITE, ROLE_READ, ROLE_WRITE, ROLE_DELETE
- **Ops surfaces:** DICOMWEB_READ, DICOMWEB_WRITE, HL7_READ, REPLICA_READ,
  ROUTING_READ, INTERFACE_MONITOR, INTERFACE_ADMIN, STORAGE_ADMIN, METRICS_READ
- **Operational role grants (to assign those roles):** PATIENT_WRITE,
  EXAM_READ/WRITE, BILLING_WRITE, WORKLIST_WRITE, CRITICAL_RESULTS_WRITE,
  REGISTRATION_READ/WRITE, QUEUE_READ, SCHEDULE_WRITE, NURSING_READ/WRITE,
  ORDER_WRITE, CARE_PLAN_WRITE, ENCOUNTER_WRITE, MED_ORDER_READ,
  PRIOR_AUTH_READ/WRITE, ANALYTICS_READ, EQUIPMENT_READ
- **Read-only:** BILLING_READ, AUDIT_READ, LOG_READ, REPORT_READ, REPORT
  TEMPLATE_ADMIN, SCHEDULE_READ, FILE_READ, FILE_WRITE, STUDY_READ,
  STUDY_EXPORT, VIEWER_READ, PATIENT_READ, ORDER_READ, CHART_READ, RESULTS_READ

You **cannot**:
- Perform clinical work (report writing/signing, exam acquisition, QA)
- Manage tenants, service keys, FHIR config, maintenance/backups/settings
  (platform-only)
- Assign clinical reader / EMR writer roles (radiologist, physician, etc.)
- Create admin-flagged users
- Write to billing (drop/submit/import), HL7 config, routing, replicas

## 7. Troubleshooting & known limits

- **"Target role exceeds your own grants" when creating a user:** the role you
  picked is a clinical reader or EMR writer (e.g. radiologist, physician) that
  you cannot assign. Use an operational role (technologist, receptionist,
  cashier, care_coordinator, dept_manager, pacs_admin).
- **Billing action buttons error with 403:** you are read-only on billing.
  Contact a `BILLING_WRITE` holder.
- **HL7 config save 403:** configuration is read-only for your role.
- **Empty dashboard KPI cards:** platform-side accounts may see "—" where a
  tenant-scoped user would see numbers — check your tenant selection.
- **Elasticsearch offline:** search degrades gracefully; archive is still
  browsable.
- **Interface Health shows no status:** no interfaces are configured/reporting
  in this environment.