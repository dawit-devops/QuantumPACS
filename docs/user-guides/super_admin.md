# Super Admin User Guide — QuantumPACS

Version: `feature/ris-integration` @ `cc297a2` | Role: `super_admin` | Applies to: platform owner (multi-tenant)

## 1. About this role

The platform **super_admin** is the top-level operator account for the entire
QuantumPACS installation. It is a *platform-owner* role: it can see and manage the
tenant registry (every tenant), the user directory, roles/permissions, DICOM routing,
integrations, and system settings, and it is the only built-in role with
`SYSTEM_ADMIN`.

It is **not** a clinical role: by design it is excluded from the clinical
workspaces (Reading, Acquisition, QA, Coordination, Front Desk, Portal). Those
surfaces belong to radiologist/technologist/coordinator/front-desk/patient roles.
Since the user decision recorded in the role-walk, **Billing is open to admin
roles**, so super_admin can operate the full billing capture flow.

- Landing page after sign-in: **Dashboard** (`/admin`)
- Tenant model: platform owner — sees all tenants in the registry; data-plane
  reads stay scoped to the active tenant.

## 2. Signing in

1. Go to the QuantumPACS URL (e.g. `http://localhost:5173`).
2. Enter username `acme.super_admin` (or the deployed super-admin login) and the
   password, then pick the tenant **acme**.
3. You land on the Admin Dashboard.

> Security note: this role holds every permission. It should be used for
> administration only, never for routine daily viewing. Known gaps tracked in the
> role-walk: no MFA yet (HIGH), access token stored in `localStorage` (HIGH), and
> the token is sent in the login request body (MEDIUM) — see `GAP-ANALYSIS.md`.

## 3. Getting around

The sidebar (Admin section + Metrics + Files + Account) is what this role sees:

| Section | Items |
|---|---|
| **Admin** | Report Templates, Dashboard, RIS Dashboard, Staff Schedule, Replicas, Users, Tenants, Roles, Logs, Service Keys, Routing, FHIR (config/monitoring/docs), Integrations, HL7, Interface Health, Maintenance, Backups, Settings, DICOMweb (Server/Store/Study Browser) |
| **Billing** | Billing Queue, Claims, Revenue, Unbilled Aging, Denial Rework, Fee Schedule, Reconciliation |
| **Metrics** | Metrics |
| **Files** | Files (study/file browser) |
| **Account** | Account, Notifications (bell), Dark Mode, Logout |

## 4. Surface-by-surface guide

### 4.1 Admin Dashboard  (`/admin`)
- Purpose: operational home — platform health (DB/Elasticsearch/Redis/auth),
  storage totals, user/study counts, ingestion + modality charts, interface
  status, replica sync, recent activity.
- How to: sign in; the dashboard is the landing page. Use Refresh to reload.
- Status: **PASS**. (Note: Elasticsearch is not running in dev — search surfaces
  degrade gracefully; 1 cosmetic Chart.js warning.)

### 4.2 RIS Dashboard  (`/admin/ris-dashboard`)
- Purpose: department KPIs — turnaround time (TAT), staff/utilization, volume,
  unbilled aging.
- How to: open from the Admin menu; drill into workload / TAT / equipment tables.
- Status: **PASS**. Seed limitation: worklist dates are future-dated (Sep/Oct), so
  "today" volume reads 0 until real exams flow.

### 4.3 Staff Schedule  (`/admin/staff-schedule`)
- Purpose: staff shift assignments, time-off requests, coverage-gap detection.
- How to: Scheduled Exams tab shows the day's exams (tenant-scoped); Time Off tab
  lists requests and computed coverage gaps.
- Status: **PASS** (cross-tenant leak fixed — only the active tenant's rows show).

### 4.4 Report Templates  (`/admin/report-templates`)
- Purpose: manage the report template library radiologists use for dictation.
- How to: create a template, edit, publish, rollback; version history per template.
- Status: **PASS**.

### 4.5 Replicas  (`/replicas`)
- Purpose: replica node registry + sync state.
- How to: view nodes and their sync status.
- Status: **PASS**.

### 4.6 Users  (`/users`)
- Purpose: platform user directory.
- How to: search users; create a user; assign role + tenant; reset password;
  deactivate; delete. Bulk import supported.
- Status: **PASS**. (Gap G1 tracked: a parallel `users.admin` super-admin path
  should converge on `SYSTEM_ADMIN`.)

### 4.7 Tenants  (`/tenants`)
- Purpose: the multi-tenant registry — every tenant's DB, usage, storage quota,
  and lifecycle.
- How to: list tenants; **Provision** a new tenant; edit storage/quota;
  **Suspend / Quarantine / Decommission**. Health/usage per tenant.
- Status: **PASS**. Dev limitation: `acme` and `default` share one DB (not true
  database-per-tenant) — real provisioning is per-tenant in production (G6).

### 4.8 Roles  (`/roles`)
- Purpose: permission matrix + role grants.
- How to: view built-in roles; create/edit role grants; delete unused roles.
- Status: **PASS**.

### 4.9 Logs  (`/logs`)
- Purpose: audit + application log stream.
- How to: browse logs by page/offset; filter by actor. (The `event-types` filter
  is a tracked refinement — see FRONTEND-INVENTORY C1.)
- Status: **PASS** (minor refinement deferred).

### 4.10 Service Keys  (`/service-keys`)
- Purpose: platform API keys for SI/integration clients.
- How to: create a key, copy it, revoke/rotate.
- Status: **PASS**.

### 4.11 Routing  (`/routing`)
- Purpose: AE-title / DICOM routing rules.
- How to: list rules, add a routing rule, edit/delete.
- Status: **PASS**.

### 4.12 FHIR  (`/fhir/config`, `/fhir/monitoring`, `/fhir/docs`)
- Purpose: FHIR server configuration, monitoring, and API docs.
- How to: enable/configure the FHIR endpoint, view client registry, monitor
  request volume, read the docs.
- Status: **PASS**.

### 4.13 Integrations  (`/integrations`)
- Purpose: integration registry (webhooks, connectors).
- How to: list and manage integrations.
- Status: **PASS**.

### 4.14 HL7  (`/hl7`)
- Purpose: HL7 interface console (ADT/ORM/ORU messages).
- How to: view inbound message status, config, and endpoints.
- Status: **PASS**.

### 4.15 Interface Health  (`/admin/interfaces`)
- Purpose: per-endpoint interface monitor (RIS interfaces, HL7, DICOMweb).
- How to: view endpoint health and message throughput; retry exceptions.
- Status: **PASS**.

### 4.16 Maintenance  (`/admin/maintenance`)
- Purpose: platform maintenance mode / system tasks.
- How to: toggle maintenance mode (POST-only — a GET on the endpoint is expected
  to return 405).
- Status: **PASS**.

### 4.17 Backups  (`/admin/backups`)
- Purpose: backup registry, trigger restore, retention.
- How to: list backups, trigger a backup, restore an artifact, download.
- Status: **PASS**.

### 4.18 Settings  (`/admin/settings`)
- Purpose: whitelisted platform config overrides.
- How to: view/edit supported config keys (env/backend).
- Status: **PASS**.

### 4.19 DICOMweb  (`/dicomweb`, `/dicomweb/store`, `/dicomweb/browser`)
- Purpose: DICOMweb server console, STOW-RS store, and study browser.
- How to: Server = admin/metrics/requests; Store = upload DICOM via STOW-RS;
  Browser = QIDO-RS study/series/instance browsing.
- Status: **PASS**.

### 4.20 Metrics  (`/metrics`)
- Purpose: platform analytics dashboards (METRICS_READ / ANALYTICS_READ).
- How to: browse metric tiles/dashboards.
- Status: **PASS**.

### 4.21 Files  (`/`)
- Purpose: file/study browser (also the DICOM viewer entry).
- How to: search studies, open a study, download selection (zip/csv), share.
- Status: **PASS**.

### 4.22 Billing Queue  (`/billing/queue`)
- Purpose: signed-but-unbilled charges the coder reviews and drops.
- How to: confirm CPT/ICD-10 suggestions, drop single or batch, submit claims.
- Status: **PASS** (opened to admin roles by user decision).

### 4.23 Claims  (`/billing/claims`)
- Purpose: full claim lifecycle dashboard.
- How to: view claims, filter by status/payer, batch-submit.
- Status: **PASS**.

### 4.24 Revenue  (`/billing/revenue`)
- Purpose: revenue trends + AR aging (dollars).
- How to: view collections trend, payer/modality breakdown, aging buckets.
- Status: **PASS**.

### 4.25 Unbilled Aging  (`/billing/unbilled`)
- Purpose: unbilled charges grouped by date/site/payer.
- How to: group by dimension, export groups for reconciliation.
- Status: **PASS**.

### 4.26 Denial Rework  (`/billing/denials`)
- Purpose: denied/resubmitted claims queue; coder corrects and resubmits.
- How to: **Import Denial** (record a 835-style denial on a claim by ID),
  **Rework** a single claim (with audit note), **Rework all** a reason-code
  group, view claim **History** timeline.
- Status: **PASS** (Import Denial added during the walk; malformed IDs return a
  clean 404; explicit reasons are stored verbatim).

### 4.27 Fee Schedule  (`/billing/fee-schedule`)
- Purpose: procedure fee catalog + payer contract rates.
- How to: edit list price/description, bulk import, version history; manage
  payer contracts and view charge-vs-contract comparison.
- Status: **PASS**.

### 4.28 Reconciliation  (`/billing/reconciliation`)
- Purpose: signed-reports vs charged-reports capture-rate snapshot.
- How to: open the page; three tiles — Signed Reports, Charged Reports, Capture
  Rate (%). Refresh to reload.
- Status: **PASS** (new page, built during the walk).

### 4.29 Account  (`/account`) & Notifications (bell)
- Purpose: profile, password change, notification preferences; in-app feed.
- Status: **PASS**.

## 5. Common workflows (walkthroughs)

### 5.1 Provision a new tenant
1. Admin → **Tenants**.
2. Click **Provision / New Tenant**; enter the tenant name/slug.
3. Review the assigned storage quota; adjust if needed.
4. Confirm. The tenant appears in the registry (production provisions a
   per-tenant DB; dev shares the configured DB).
5. Then create the tenant's first admin user (5.2).

### 5.2 Create a user and assign a role + tenant
1. Admin → **Users** → **New User**.
2. Fill username/display name/email and a temporary password.
3. Pick the **role** (e.g. `radiologist`) and the **tenant** (e.g. `acme`).
4. Save. Give the user their credentials; they can change the password at first
   sign-in (or you reset it later).

### 5.3 Reset a user password / deactivate
1. Admin → **Users** → search the user.
2. **Reset password** (generates/lets you set a new one) or **Deactivate**
   (blocks sign-in without deleting history).

### 5.4 Issue a Service Key (for an SI/integration)
1. Admin → **Service Keys** → **Create Key**.
2. Copy the key immediately (shown once) and hand it to the integration owner.
3. Revoke or rotate from the same list when compromised/expired.

### 5.5 Record a payer denial (Denial Import)
1. Billing → **Denial Rework** → **Import Denial**.
2. Enter the **Claim ID** (required) and an optional payer **reason**.
3. **Record denial**. The claim enters the queue with the reason and can be
   reworked like any denial.
4. To correct + resubmit: **Rework** on the row, add a correction note, submit.

### 5.6 Review billing capture rate
1. Billing → **Reconciliation**.
2. Read **Capture Rate** = Charged / Signed × 100. Below ~90% (amber) suggests
   signed reports are not being dropped to billing — drill into the **Billing
   Queue** to drop them.

### 5.7 Put the platform into maintenance
1. Admin → **Maintenance** → toggle maintenance mode on (with a reason).
2. Repeat to turn it off. (The endpoint is POST-only.)

### 5.8 Manage the report template library
1. Admin → **Report Templates**.
2. Create/edit a template; **Publish** makes a version live; **Rollback** restores
   a prior version. Version history is retained per template.

## 6. Permissions summary

- `super_admin` holds **every** `Permission` (`SUPER_ADMIN_PERMISSIONS`) and
  `admin: true`, so it bypasses all permission gates.
- It is the **only** built-in role with `SYSTEM_ADMIN` (FHIR, Integrations,
  Maintenance, Backups, Settings).
- It additionally holds `TENANT_ADMIN` + `CROSS_TENANT_READ` (platform owner) and
  `EQUIPMENT_READ/WRITE` (equipment backend exists; no UI yet — backlog).
- It is **excluded from clinical workspaces** by `ClinicalRoute` (`excludedRoles`)
  and the `NON_ADMIN_WORKSPACES` sidebar filter — even though it has the
  permissions, it cannot open those pages (by design).
- **Billing** was opened to admin roles by user decision (`bf792dd`).

## 7. Troubleshooting & known limits

- **Elasticsearch offline (dev)**: search surfaces degrade gracefully; no
  functional impact on the walk surfaces.
- **Shared dev DB**: `acme` + `default` tenants share one database in dev — usage
  stats look identical; production uses database-per-tenant (ADR-016).
- **Staff schedule shows only one tenant**: correct — the cross-tenant leak was
  fixed; data-plane reads are tenant-scoped.
- **Reconciliation shows 0/0/100%**: expected with no signed/charged seed rows.
- **Maintenance GET returns 405**: expected — the endpoint is POST-only.
- **Chart.js "Filler" warning**: cosmetic, safe to ignore.
- **Known gaps (role-walk GAP-ANALYSIS)**: no MFA (HIGH), access token in
  `localStorage` (HIGH), token in login body (MEDIUM), `users.admin` parallel
  super-admin path (MEDIUM) — tracked as open items.
- **Backlog surfaces**: equipment management (backend only), billing
  reconciliation import, patient merge, reviewer pickers, duplicate
  corrective-actions/protocols registries (see BACKEND-INVENTORY.md).

---

*Generated by the supervised-role-walk skill (Phase 6) from SCOPE/PLAN/LEDGER +
backend/frontend inventories, 2026-08-27.*
