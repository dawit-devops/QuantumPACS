# Backend Requirements: R01 Super Admin (PACS Admin)

## Context

The Super Admin owns the entire QuantumPACS instance and all tenants. Works from
an ops/IT office, reacts to incidents, and rarely uses the clinical viewer. Full
`SYSTEM_ADMIN` access across every tenant, plus DICOM infrastructure,
integrations, storage, RBAC, and audit. Everything this role touches is
permission-gated — the frontend must hide or disable anything the user cannot do.

**Screens (all exist in the frontend)**: Tenants, Users, Roles, Routing Rules,
Service Keys, Integrations (webhooks/OAuth), Replicas, Logs, Metrics/Dashboard,
DICOMweb Admin, FHIR Admin, HL7 Admin, Notifications. Most map to existing
feature docs — see `tenants/`, `users/`, `roles/`, `routing-rules/`,
`service-keys/`, `replicas/`, `audit-logs/`, `metrics/`, `dicomweb/`,
`fhir-r4-api/`, `hl7-adt-orm/`, `notifications/`.

**Personas**: P4 (PACS Admin). **Access tier**: System + all tenants.

## Screens/Components

### Tenants

**Purpose**: Provision, monitor, and decommission tenant installations.

**Data I need to display**: tenant name, slug, custom domain, lifecycle status
(provisioning/active/quarantined/decommissioned), storage used vs. quota (with
percentage bar), user count, study count.

**Actions**: provision a tenant (name, slug, optional domain, optional quota),
edit (name, domain, quota), decommission (with 90-day retention warning).

**States to handle**: provisioning spinner (no polling today — see
Uncertainties), quarantined read-only banner, decommissioned dimmed card.

**Business rules affecting UI**: status enum drives colors/actions; edit disabled
while provisioning/quarantined; decommission disabled while provisioning.

### Users / Roles

**Purpose**: Manage who can use the system and what they can do.

**Data I need**: paginated user list (id, username, role, admin flag, status),
role permission lists, permission catalog grouped by domain, role user counts.

**Actions**: create user (returns one-time password), deactivate, reset password
(one-time), inline role change, bulk CSV import, role CRUD, delete-protected
built-in roles, `super_admin` fully locked.

**States**: loading/empty/error with retry; one-time-password modal; per-row bulk
import status.

**Business rules affecting UI**: only active users have actions; built-in roles
immutable (super_admin fully locked); permissions grouped by domain render as-is
(new groups should appear without a frontend change).

### Routing Rules / Service Keys / Integrations

**Purpose**: Configure DICOM auto-routing and external system access.

**Data I need**: routing rules with condition trees (eq/ne/contains/gt/gte/lt/lte
and OR-groups), priority ordering, match counts, test results; API keys with
permission scopes and last-used timestamps; webhook/OAuth provider configs.

**Actions**: CRUD routing rules, run a test match, create/revoke API keys, CRUD
webhooks and OAuth providers, fire a test webhook.

**Business rules affecting UI**: routing semantics "all matching rules apply";
service-key secrets shown only at creation.

### Replicas

**Purpose**: Manage storage replicas (local/S3/B2).

**Data I need**: replica list, type, master designation, sync delay/progress,
health status, active/repair states.

**Actions**: add/remove replica, designate master, trigger health check,
failover, repair/delete.

### Logs / Metrics / Admin dashboards

**Purpose**: Observe system health and audit activity.

**Data I need**: paginated audit log events with event types and actor filters;
metrics aggregates (patients/studies/series/files/users/storage), system health,
modality distribution, ingestion trend, component latency, latest files; HL7 /
FHIR / DICOMweb admin metrics; station AE list.

**Actions**: filter/sort/export logs, apply time range + auto-refresh on
dashboards, drill into metric detail.

**Business rules affecting UI**: tenant-scoped vs. cross-tenant log views
(gated); dashboard data is aggregate-first with drill-through.

### Notifications

**Purpose**: In-app notification bell.

**Data I need**: notification list, read/unread state, badge counts, per-event
types.

**Actions**: mark read/unread, navigate to the related item.

## Uncertainties
- [ ] No system-wide health/uptime aggregate endpoint exists — dashboards are
  per-area. Is a single aggregate planned?
- [ ] Storage quota is accepted at provision but there is no usage dashboard
  beyond the tenant cards — is a quota/usage aggregate available?
- [ ] Backup & restore of full system state is a roadmap item — nothing to build
  against yet.
- [ ] Global notification-preference administration is missing (only the
  per-user bell exists).
- [ ] List pagination contracts are inconsistent across screens (some read a
  `meta` block, some guess totals from page length) — needs one convention.

## Questions for Backend
- Can we standardize one list-response shape (items + true total) across
  tenants, users, roles, logs, and API keys?
- Is tenant provisioning completion something the UI can subscribe to, or should
  it poll?
- For decommission: is the 90-day retention window backend-enforced or just
  informational in the UI?

## Discussion Log

_(pending backend review)_
