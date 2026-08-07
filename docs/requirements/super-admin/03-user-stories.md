# User Stories — Super Admin (R01)

Priority: Must | Should | Could | Won't. Every story carries acceptance criteria,
accessibility, and performance requirements per the skill's frontend-developer lens.

---

## US-R01-01: Provision a New Tenant
**Story**: As a super admin, I want to provision a new tenant with database, admin user, and storage quota in one step, so that a new hospital/department can start operating without manual DB work.
**Priority**: Must

### Acceptance Criteria
- **Given** I am a super admin on the Tenants screen, **when** I click "New Tenant", **then** a provisioning dialog opens with fields: slug, name, domain, db_name, db_host, db_port, db_user, db_password, storage_quota_bytes, admin_email.
- **Given** I submit a valid form, **when** the API returns 201, **then** I see the tenant in the list and a one-time admin password panel that requires explicit "I saved the password" confirmation before closing.
- **Given** the slug already exists, **when** I submit, **then** an inline 409 conflict error appears on the slug field and the form is preserved.
- **Given** provisioning fails (DB error), **when** the API returns an error, **then** a failure banner with step-level detail is shown and no partial tenant appears in the list.
- **Accessibility**: dialog is focus-trapped, ESC closes only after password confirmation, all fields have labels.
- **Performance**: dialog open → form render ≤ 1s; provisioning round-trip shows progress state after 30s.

### Dependencies
- `POST /api/v2/tenants` (TenantProvisioner), `AuditLog` `tenant.provisioned`
- Related: `IMPLEMENTATION_PLAN-v3` F6.2 provisioning dialog

---

## US-R01-02: Switch Tenant Context
**Story**: As a super admin, I want to switch my active tenant from a switcher, so that all admin views show the selected tenant's data.
**Priority**: Must

### Acceptance Criteria
- **Given** I am a super admin with access to multiple tenants, **when** I select a tenant in the switcher, **then** all admin screens refetch scoped data within 1s and the current tenant is shown persistently in the header.
- **Given** I navigate to a view I lack permission for in the new tenant, **when** the view loads, **then** I see an "Access denied" state, not a broken page.
- **Given** the switch target is unavailable, **when** I switch, **then** an error state with retry appears and the previous context is preserved.
- **Accessibility**: switcher is a labelled combobox with keyboard support.
- **Performance**: NFR-R01-09 ≤ 1s scoped-view load.

### Dependencies
- `tenant_middleware.py` tenant scoping; Tenant Switcher (F6.2)

---

## US-R01-03: Create User with Role
**Story**: As a super admin, I want to create a user with a role and temporary password, so that staff get access appropriate to their job.
**Priority**: Must

### Acceptance Criteria
- **Given** I am on the Users screen, **when** I click "Add user", **then** a form opens for username, name, email, role, and temp password policy.
- **Given** I submit, **when** creation succeeds, **then** the user appears in the list and the action is audit-logged.
- **Given** the username exists, **when** I submit, **then** an inline error is shown.
- **Accessibility**: form labels + error summary for screen readers.
- **Performance**: create round-trip ≤ 2s p90.

### Dependencies
- `POST /api/v2/users`, `POST /users/role`, audit log

---

## US-R01-04: Bulk Import Users
**Story**: As a super admin, I want to bulk-import users from CSV with a validation report, so that onboarding whole departments is fast and safe.
**Priority**: Should

### Acceptance Criteria
- **Given** I upload a CSV, **when** validation completes, **then** I see per-row results (valid / errors) and can commit only valid rows.
- **Given** the file has malformed rows, **when** I preview, **then** errors are listed with row numbers and reasons, and nothing is imported until I confirm.
- **Given** import completes, **when** the report is shown, **then** counts of created/skipped/failed are displayed.
- **Accessibility**: report is a real table (not image/text blob) for screen readers.
- **Performance**: 1,000-row file validates ≤ 10s.

### Dependencies
- Existing `BulkImport.tsx`; `POST /api/v2/users` loop or batch endpoint (verify)

---

## US-R01-05: Manage RBAC Roles with Permission Catalog
**Story**: As a super admin, I want to create roles from a grouped permission catalog, so that least-privilege access is easy to configure.
**Priority**: Must

### Acceptance Criteria
- **Given** I open Roles, **when** I create a role, **then** permissions are presented grouped by module with select-all-per-module and a visible count of selected permissions.
- **Given** a role includes `SYSTEM_ADMIN`, **when** I save, **then** a privilege-escalation warning requires explicit confirmation.
- **Given** I delete a role with assigned users, **when** I attempt deletion, **then** deletion is blocked and the affected users are listed with a reassignment option.
- **Given** I open a role, **when** I view its users, **then** `GET /roles/{id}/users` lists them with remove action.
- **Accessibility**: permission groups are navigable by keyboard with visible focus.
- **Performance**: catalog loads ≤ 2s; grouped list virtualized if > 100 items.

### Dependencies
- `GET /permissions`, `GET/POST /roles`, `GET/PUT/DELETE /roles/{id}`, `GET /roles/{id}/users`
- Related: `IMPLEMENTATION_PLAN-v3` F6.1c

---

## US-R01-06: Manage Storage Replicas
**Story**: As a super admin, I want to add, edit, and monitor storage replicas, so that data redundancy and disaster recovery are under control.
**Priority**: Must

### Acceptance Criteria
- **Given** I open Replicas, **when** the list loads, **then** each replica shows status (healthy/degraded/offline) with color coding and last-sync info without opening detail.
- **Given** a replica is degraded, **when** I expand it, **then** I see the last sync error and can trigger retry or edit.
- **Given** I delete a replica with pending sync, **when** I confirm, **then** a confirmation shows pending-sync count before deletion proceeds.
- **Given** storage backend is down, **when** status is polled, **then** replica shows "offline" with a retry action and a notification is created.
- **Accessibility**: status is not conveyed by color alone (icon + text).
- **Performance**: replica status refresh ≤ 30s staleness.

### Dependencies
- `GET/POST /replicas`, `GET/PUT/DELETE /replicas/{id}`, notifications

---

## US-R01-07: Configure DICOM Routing Rules
**Story**: As a super admin, I want to build routing rules with a condition builder, so that studies route to the right destinations automatically.
**Priority**: Must

### Acceptance Criteria
- **Given** I open Routing Rules, **when** I create a rule, **then** a condition builder supports modality, AE title, and keyword conditions with AND/OR grouping.
- **Given** rules overlap, **when** I save a conflicting rule, **then** an overlap warning lists the existing rule and requires confirmation.
- **Given** rules are ordered by priority, **when** I reorder, **then** order is persisted and applied.
- **Given** a rule references a disabled destination, **when** the list renders, **then** the rule row shows a warning badge.
- **Accessibility**: condition builder uses labelled selects, not free-form text only.
- **Performance**: rule list with condition trees renders ≤ 2s for 500 rules.

### Dependencies
- `GET/POST /routing`, `GET/PUT/DELETE /routing/{id}`, `RuleConditionBuilder.tsx`

---

## US-R01-08: Manage Service API Keys
**Story**: As a super admin, I want to create and revoke service API keys with rotation support, so that integrations authenticate securely.
**Priority**: Must

### Acceptance Criteria
- **Given** I create a key, **when** the API returns the secret, **then** the full secret is shown exactly once with a copy button and "I saved the secret" confirmation.
- **Given** a key exists, **when** I view the list, **then** I see label, key prefix, created_by, and last_used to identify stale keys.
- **Given** I revoke a key, **when** I confirm, **then** the confirmation text includes the key label and the action is audit-logged (`api_key.revoked`).
- **Given** a key is created without an expiry, **when** it is saved, **then** a rotation-schedule warning is shown.
- **Accessibility**: copy button has an accessible name and announces success.
- **Performance**: create round-trip ≤ 2s p90.

### Dependencies
- `GET/POST /api-keys`, `GET/PUT/DELETE /api-keys/{id}`

---

## US-R01-09: Review Audit Logs with Facets
**Story**: As a super admin, I want to search and filter audit logs by event type, actor, resource, and date, so that I can investigate who changed what and when.
**Priority**: Must

### Acceptance Criteria
- **Given** I open Logs, **when** the screen loads, **then** it defaults to the last 24h with all event types and paginated results.
- **Given** I select an event-type or actor facet, **when** I apply it, **then** results filter server-side and the facet counts update.
- **Given** I open a log row, **then** details render as readable pretty-printed JSON with a copy button.
- **Given** I export, **when** I choose CSV, **then** the current filter set is exported (not just the visible page).
- **Given** the query is too broad and times out, **when** the request fails, **then** a prompt to narrow the date range is shown instead of an endless spinner.
- **Accessibility**: table is fully keyboard-navigable; faceted controls have labels.
- **Performance**: first page ≤ 2s p90 on 1M seeded rows (NFR-R01-03).

### Dependencies
- `GET /logs`, `GET /logs/event-types`, `GET /logs/actors`

---

## US-R01-10: Monitor System Metrics
**Story**: As a super admin, I want to view platform, DICOM-web, HL7, and FHIR metrics, so that I can spot degradation early.
**Priority**: Must

### Acceptance Criteria
- **Given** I open Metrics, **when** the dashboard loads, **then** platform metrics render with time-range control and per-area dashboards for DICOM-web, HL7, and FHIR.
- **Given** a metrics endpoint is down, **when** its panel loads, **then** the panel shows "metrics unavailable" with retry while other panels keep working.
- **Given** a metric exceeds a threshold, **when** rendered, **then** it is visually flagged (amber/red token) with text label, not color alone.
- **Accessibility**: charts include accessible data tables; color ramps are color-blind-safe.
- **Performance**: dashboard LCP ≤ 2.5s; chart interactions INP ≤ 200ms.

### Dependencies
- `GET /metrics`, `GET /dashboard/metrics`, `GET /dicomweb/admin/metrics`, `GET /hl7/admin/metrics`, `GET /fhir/admin/metrics`

---

## US-R01-11: Configure FHIR Integration
**Story**: As a super admin, I want to configure the FHIR server, OAuth clients, and test the integration, so that EMR connectivity is reliable.
**Priority**: Must

### Acceptance Criteria
- **Given** I open FHIR config, **when** I save server configuration, **then** config is persisted and the integration test can be run.
- **Given** I run the integration test, **when** it completes, **then** structured results (status, latency, request/response) are displayed.
- **Given** I create an OAuth client, **when** the secret is issued, **then** it is shown once with confirmation (same pattern as US-R01-08) and never re-displayed.
- **Given** recent requests are viewed, **when** the dashboard loads, **then** 4xx/5xx rates are prominently visible.
- **Accessibility**: test results are structured text, not only color-coded.
- **Performance**: test endpoint returns ≤ 5s (NFR-R01-10).

### Dependencies
- `/fhir/admin/config`, `/fhir/admin/clients`, `/fhir/admin/test`, `/fhir/admin/requests`

---

## US-R01-12: Configure HL7 Interface
**Story**: As a super admin, I want to configure the HL7 listener and review message history, so that RIS/EMR integration issues are diagnosable.
**Priority**: Must

### Acceptance Criteria
- **Given** I open the HL7 dashboard, **when** it loads, **then** listening status is shown in the header with message-history metrics.
- **Given** I edit config, **when** I save, **then** config is persisted and status reflects the change.
- **Given** I open a message, **when** it failed parsing, **then** parse errors are highlighted per HL7 segment alongside the raw payload.
- **Given** the listener is down, **when** status is polled, **then** "not listening" state with retry action and a notification are shown.
- **Accessibility**: message detail is a readable table + preformatted payload.
- **Performance**: message list page ≤ 2s p90.

### Dependencies
- `/hl7/admin/config`, `/hl7/admin/status`, `/hl7/admin/messages`, `/hl7/admin/messages/{id}`, `/hl7/admin/metrics`

---

## US-R01-13: Manage OAuth/SSO Providers
**Story**: As a super admin, I want to manage SSO providers, so that users authenticate through the hospital's identity provider.
**Priority**: Must

### Acceptance Criteria
- **Given** I open OAuth providers, **when** the list loads, **then** each provider shows enabled state without opening detail.
- **Given** I add a provider, **when** I submit, **then** OIDC discovery is tested and discovery errors are shown with detail.
- **Given** I disable a provider with existing users, **when** I confirm, **then** a login-impact warning is shown before disabling.
- **Given** a provider has client secrets, **when** stored, **then** they are encrypted and never re-displayed.
- **Accessibility**: enable/disable is a labelled switch.
- **Performance**: discovery test ≤ 5s.

### Dependencies
- `/oauth/providers` CRUD, `backend/api/encryption.py`

---

## US-R01-14: Receive Admin Notifications
**Story**: As a super admin, I want in-app notifications for critical admin events, so that I react to incidents without polling dashboards.
**Priority**: Should

### Acceptance Criteria
- **Given** a replica fails or an integration goes down, **when** the event occurs, **then** a notification is created and the unread-count badge updates.
- **Given** I open the notification bell, **when** I click a notification, **then** I am routed to the relevant screen (replica detail, integration dashboard).
- **Given** I mark notifications read, **when** I do, **then** the badge count updates immediately (optimistic update).
- **Accessibility**: badge announces count to screen readers (aria-live).
- **Performance**: unread-count update ≤ 5s from event.

### Dependencies
- `GET /notifications`, `GET /notifications/unread-count`, existing `NotificationBell.tsx`
- GAP: notification-creation rules for admin events must be confirmed with backend

---

## US-R01-15: Global System Health Overview
**Story**: As a super admin, I want a single health overview, so that I can assess system-wide state at a glance.
**Priority**: Should

### Acceptance Criteria
- **Given** I open the dashboard, **when** it loads, **then** storage, DICOM, integrations (HL7/FHIR), and auth health are summarized with drill-down links.
- **Given** an area is degraded, **when** rendered, **then** it is flagged with icon + text and a link to the area dashboard with matching time scope.
- **Given** the metrics endpoint is down, **when** the page renders, **then** it shows "metrics unavailable" for that panel without failing the page.
- **Accessibility**: status conveyed by icon + text, not color alone.
- **Performance**: dashboard LCP ≤ 2.5s.
- **Note**: aggregate endpoint implemented — `GET /v2/dashboard/health` (METRICS_READ) returns storage, DICOM, HL7, FHIR, and auth component status; System Health card rows link to area dashboards with time-scope passthrough.

### Dependencies
- `GET /v2/dashboard/health` (implemented) + per-area metrics (`/dicomweb/admin/metrics`, `/hl7/admin/metrics`, `/fhir/admin/metrics`)

---

## US-R01-16: Backup and Restore
**Story**: As a super admin, I want to back up and restore the full system state, so that I can recover from catastrophic failure.
**Priority**: Could

### Acceptance Criteria
- **Given** I trigger backup, **when** it completes, **then** a single artifact containing DB state and files is produced with timestamp and checksum.
- **Given** I restore, **when** I confirm, **then** the system returns to the backed-up state and the restore is audit-logged.
- **Given** restore is in progress, **when** users access the system, **then** a maintenance banner is displayed.
- **Note**: not implemented — roadmap feature; retain as backlog story.

### Dependencies
- GAP: full state backup/restore (Roadmap.md)

---

## US-R01-17: Everything Is Audit-Logged
**Story**: As a super admin, I want every admin mutation audit-logged, so that HIPAA and security reviews are straightforward.
**Priority**: Must

### Acceptance Criteria
- **Given** I perform any mutating admin action (tenant, user, role, routing, key, webhook, integration), **when** it succeeds, **then** an audit entry records actor, action, resource, timestamp, request_id, and tenant.
- **Given** I export audit data, **when** requested by compliance, **then** CSV export includes the full filter set.
- **Given** a non-admin actor attempts an admin action, **when** denied, **then** a 403 is returned and the attempt is logged.
- **Accessibility**: n/a (backend behavior).
- **Performance**: audit write adds ≤ 100ms to mutation latency.

### Dependencies
- `AuditLog.log_event`, `@requires_permission`, `docs/User-Stories.md` Epic E7
