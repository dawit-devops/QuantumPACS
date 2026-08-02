# User Stories — Hospital IT / Tenant Admin (R02)

Priority: Must | Should | Could | Won't. Every story carries acceptance criteria,
accessibility, and performance requirements per the frontend-developer lens.

---

## US-R02-01: Tenant-Scoped User Management
**Story**: As a tenant admin, I want to manage users within my tenant, so that my hospital's staff have the right access.
**Priority**: Must

### Acceptance Criteria
- **Given** I am a tenant admin, **when** I open Users, **then** only my tenant's users are listed (no cross-tenant rows).
- **Given** I create a user, **when** I submit, **then** the user appears with the chosen role and the action is audit-logged with my tenant.
- **Given** I attempt to assign a super-admin role, **when** I submit, **then** the role picker does not offer it (403 if forced) and an inline message explains it is not available at tenant scope.
- **Given** I deactivate a user, **when** confirmed, **then** the user cannot log in and the action is logged.
- **Accessibility**: form labels + error summary for screen readers.
- **Performance**: list first page ≤ 2s p90.

### Dependencies
- `GET/POST /users`, `/users/deactivate`, `/users/role`; tenant scope via middleware

---

## US-R02-02: Bulk Import Tenant Users
**Story**: As a tenant admin, I want to bulk-import users from CSV with validation, so that onboarding whole departments is fast.
**Priority**: Should

### Acceptance Criteria
- **Given** I upload a CSV, **when** validation completes, **then** a per-row report shows valid/error rows with row numbers and reasons.
- **Given** the report has errors, **when** I review, **then** nothing imports until I explicitly commit valid rows.
- **Given** the import commits, **when** finished, **then** created/skipped/failed counts are shown and the import is audit-logged.
- **Performance**: 1,000-row file validates ≤ 10s.

### Dependencies
- `BulkImport.tsx` (tenant-scoped), users endpoints

---

## US-R02-03: Manage Modality Worklist Stations
**Story**: As a tenant admin, I want to register station AE titles per modality, so that modality worklists work for technologists.
**Priority**: Must

### Acceptance Criteria
- **Given** I open the worklist station screen, **when** I add a station (AE title, modality from controlled vocabulary), **then** it appears and is usable by MWL.
- **Given** I enter a duplicate AE title within my tenant, **when** I save, **then** an inline conflict error is shown.
- **Given** a station is referenced by active routing rules, **when** I try to delete it, **then** deletion is blocked and the referencing rules are listed.
- **Accessibility**: modality select is a labelled combobox, not free text.
- **Performance**: station list ≤ 2s p90.

### Dependencies
- `GET /worklist/station-aes`, `GET/POST /dicomweb/admin`, worklist endpoints

---

## US-R02-04: Manage Tenant Routing Rules
**Story**: As a tenant admin, I want to configure DICOM routing rules within my tenant, so that studies route to the right destinations.
**Priority**: Must

### Acceptance Criteria
- **Given** I open Routing, **when** I create a rule, **then** the condition builder supports modality/AE/keyword conditions with AND/OR grouping.
- **Given** a new rule overlaps an existing one, **when** I save, **then** an overlap warning names the existing rule and requires confirmation.
- **Given** rules are priority-ordered, **when** I reorder, **then** the order persists and applies.
- **Given** a rule targets a disabled destination, **when** the list renders, **then** a warning badge shows.
- **Performance**: 500 rules render ≤ 2s.

### Dependencies
- `GET/POST /routing`, `GET/PUT/DELETE /routing/{id}`

---

## US-R02-05: Diagnose HL7 Message Failures
**Story**: As a tenant admin, I want to inspect failed HL7 messages, so that RIS integration issues are diagnosable without vendor support.
**Priority**: Must

### Acceptance Criteria
- **Given** I open the HL7 dashboard, **when** it loads, **then** listening status is in the header and message metrics are visible.
- **Given** I open a failed message, **when** it had parse errors, **then** errors are highlighted per HL7 segment with plain-language hints plus raw payload.
- **Given** the listener is down, **when** status is polled, **then** "not listening" with retry and a notification are shown.
- **Accessibility**: message detail is table + preformatted payload (screen-reader friendly).
- **Performance**: message list page ≤ 2s p90.

### Dependencies
- `/hl7/admin/status`, `/hl7/admin/messages`, `/hl7/admin/messages/{id}`, `/hl7/admin/metrics`

---

## US-R02-06: Configure FHIR for the Tenant
**Story**: As a tenant admin, I want to configure FHIR and test it, so that EMR connectivity is reliable for my tenant.
**Priority**: Must

### Acceptance Criteria
- **Given** I open FHIR config, **when** I save, **then** config persists and the integration test can run.
- **Given** I run the test, **when** it completes, **then** structured results (status, latency, request/response) are shown ≤ 5s.
- **Given** I create an OAuth client, **when** the secret is issued, **then** it is shown once with confirmation and never re-displayed.
- **Given** recent requests load, **when** the dashboard renders, **then** 4xx/5xx rates are prominent.
- **Performance**: test ≤ 5s (NFR).

### Dependencies
- `/fhir/admin/config`, `/fhir/admin/clients`, `/fhir/admin/test`, `/fhir/admin/requests`

---

## US-R02-07: Review Tenant Audit Log
**Story**: As a tenant admin, I want to filter tenant audit logs, so that I can answer "who did what when" for my hospital.
**Priority**: Must

### Acceptance Criteria
- **Given** I open Logs, **when** it loads, **then** it defaults to the last 24h tenant-scoped events.
- **Given** I filter by actor/event type, **then** filters are server-side and only tenant events are offered/returned.
- **Given** I expand a row, **then** details render as pretty JSON with copy.
- **Given** I export, **when** I choose CSV, **then** the current filter set is exported.
- **Given** the query times out, **when** it fails, **then** a "narrow your range" prompt shows.
- **Performance**: first page ≤ 2s p90.

### Dependencies
- `GET /logs`, `GET /logs/event-types`, `GET /logs/actors`

---

## US-R02-08: Monitor Tenant Storage Usage
**Story**: As a tenant admin, I want to see usage against my quota, so that I can manage storage before hitting limits.
**Priority**: Should

### Acceptance Criteria
- **Given** I open the dashboard, **when** it loads, **then** usage vs quota is shown with a progress indicator and percentage.
- **Given** usage exceeds 80%, **when** rendered, **then** a warning state (icon + text) and archive guidance appear.
- **Given** usage is at quota, **when** uploads are attempted, **then** uploads are blocked with a clear quota message.
- **Accessibility**: progress conveyed by icon + text + value, not color alone.
- **Performance**: dashboard LCP ≤ 2.5s.
- **Note**: GAP — requires backend tenant usage aggregation.

### Dependencies
- GAP: tenant usage endpoint (storage_quota_bytes + usage aggregation)

---

## US-R02-09: Tenant Notifications
**Story**: As a tenant admin, I want notifications for tenant incidents, so that I react without polling.
**Priority**: Should

### Acceptance Criteria
- **Given** a tenant replica fails or integration goes down, **when** detected, **then** a tenant-scoped notification is created and the badge updates ≤ 5s.
- **Given** I open a notification, **when** I click it, **then** I am routed to the relevant tenant screen.
- **Given** I mark read, **when** done, **then** the badge updates immediately (optimistic).
- **Accessibility**: badge announces count (aria-live).

### Dependencies
- `GET /notifications`, `GET /notifications/unread-count`; backend event wiring (confirm)

---

## US-R02-10: Tenant Boundary Guarantee
**Story**: As a tenant admin, I want the UI to never expose other tenants' data, so that my hospital's PHI stays isolated.
**Priority**: Must

### Acceptance Criteria
- **Given** I am a tenant admin, **when** the UI loads, **then** no cross-tenant data, tenant CRUD, or global admin items are visible.
- **Given** a cross-tenant API attempt occurs, **when** it is forced, **then** the API returns 403 and logs the attempt.
- **Given** the tenant switcher is available, **when** I open it, **then** only tenants I can access are listed.
- **Performance**: isolation checks add ≤ 50ms to requests.

### Dependencies
- `tenant_middleware.py`; permission-driven menu

---

## US-R02-11: Tenant-Scoped Service Keys
**Story**: As a tenant admin, I want to manage API keys for my tenant's integrations, so that integration credentials are controlled.
**Priority**: Must

### Acceptance Criteria
- **Given** I create a key, **when** the secret returns, **then** it is shown once with copy + "I saved the secret" confirmation.
- **Given** I view keys, **when** the list loads, **then** label, prefix, created_by, and last_used are shown.
- **Given** I revoke a key, **when** I confirm, **then** confirmation names the key label and the action is audit-logged.
- **Given** a key has no expiry, **when** saved, **then** a rotation warning shows.

### Dependencies
- `GET/POST /api-keys`, `GET/PUT/DELETE /api-keys/{id}`

---

## US-R02-12: Everything Is Audit-Logged (tenant scope)
**Story**: As a tenant admin, I want every tenant mutation audit-logged, so that compliance reviews are straightforward.
**Priority**: Must

### Acceptance Criteria
- **Given** I perform any tenant mutation (user, worklist, routing, key, integration), **when** it succeeds, **then** an audit entry records actor, action, resource, timestamp, request_id, and my tenant.
- **Given** a denied cross-tenant attempt occurs, **when** denied, **then** the attempt is logged.
- **Performance**: audit write adds ≤ 100ms to mutation latency.

### Dependencies
- `AuditLog.log_event` with tenant context
