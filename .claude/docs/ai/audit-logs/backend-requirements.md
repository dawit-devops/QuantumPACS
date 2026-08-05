# Audit Logs Page — Backend Requirements

**Route**: `/logs`
**Role**: PACS Admin (tenant-scoped), Super Admin (cross-tenant)
**Compliance**: HIPAA — access to ePHI access history

---

## Event List Display

| Column | Type | Notes |
|--------|------|-------|
| timestamp | datetime (ISO 8601) | When the event occurred |
| actor | string | Username or `system` for automated events |
| event_type | enum | See event types below |
| resource_type | string | e.g. `study`, `series`, `instance`, `user`, `tenant`, `replica` |
| resource_id | string \| null | UUID or SOP Instance UID |
| description | string | Human-readable summary |
| tenant | string \| null | Tenant slug (null for system-level events); visible only for super_admin |
| payload | jsonb | Expandable row with full details |

Display as a paginated table, newest-first by default. Each row is expandable to show the full JSON payload in a formatted viewer.

---

## Event Types

### Data Access
- `study.read` — Study viewed in viewer
- `study.download` — Study exported/downloaded
- `series.read` — Specific series viewed
- `instance.read` — Specific DICOM instance accessed
- `instance.download` — Individual file download

### Data Modification
- `study.updated` — Study metadata edited
- `study.anonymized` — Study anonymized
- `study.deleted` — Study deleted
- `series.updated` — Series metadata changed
- `instance.annotations_changed` — Annotations (key images, measurements) added/modified/deleted
- `instance.tags_edited` — DICOM tag values edited

### Auth & Session
- `auth.login` — Successful login
- `auth.login_failed` — Failed login attempt (includes IP, no password stored)
- `auth.logout` — Explicit logout or session expiry
- `auth.token_refreshed` — JWT refresh
- `auth.password_changed` — Password change (self or admin-reset)

### User Management
- `user.created` — New user added
- `user.updated` — User details/role changed
- `user.deactivated` — User deactivated
- `user.reactivated` — User reactivated
- `user.deleted` — User permanently deleted

### Tenant Management
- `tenant.created` — Tenant provisioned
- `tenant.updated` — Tenant details edited
- `tenant.quarantined` — Tenant placed in quarantine
- `tenant.decommissioned` — Tenant decommissioned
- `tenant.storage_quota_changed` — Quota modified

### Replica Management
- `replica.created` / `replica.updated` / `replica.deleted`
- `replica.master_changed` — Master replica reassigned
- `replica.sync_status_changed` — Status changed (e.g. ok → indexing)

### System
- `system.config_changed` — Global config modified
- `system.backup_completed` / `system.backup_failed`
- `system.maintenance_mode` — Toggled on/off

---

## Filtering

| Filter | Type | Behavior |
|--------|------|----------|
| Event type | Multi-select chips | Checkbox group with search; "Select all" / "Clear all" |
| Date range | DateRangePicker | Inclusive of start and end dates. Default: last 7 days. Max range: 90 days |
| Actor | Autocomplete input | Search by username, show recent actors |
| Tenant | Dropdown | Visible only for super_admin. Filters to single tenant. Default: current tenant for non-super |

Filters combine as AND. Clearing all filters shows events from the last 7 days.

---

## Live Streaming

- Polling interval: **5 seconds**
- On each poll, request events since the last-seen event ID
- New events appear at the top of the table with a subtle highlight animation (fade in yellow, transition to default bg over 2s)
- A pulsing "Live" indicator dot in the header
- Toggle on/off via switch; when off, poll stops and user sees static data
- Live mode respects current active filters — only events matching the filter set appear
- If user has scrolled down (not at newest), a "New events available" toast appears instead of auto-scrolling

---

## CSV Export

**Current implementation**: Client-side export from displayed data only (whatever is loaded in the table).

**Fields exported** (in order):
1. Timestamp (ISO 8601)
2. Actor (username)
3. Event Type
4. Resource Type
5. Resource ID
6. Description
7. Tenant (if super_admin)
8. Payload (JSON stringified)

This is acceptable for current scope. A server-generated export (with full result set, async, emailed or downloadable) is a future enhancement.

---

## Pagination

- Cursor-based pagination (cursor = last event ID + timestamp)
- Page size: default 50, configurable 10–200
- Response includes `next_cursor` and `has_more` boolean
- Sorting: newest-first only (reverse chronological). Future: sorting by any column.

---

## Permissions

- **Regular admin**: Sees only events scoped to their tenant
- **Super admin**: Can view events across all tenants; can filter by tenant
- System events (`system.*`) visible only to super admin
- Event details (payload) may contain PHI — access is logged separately (meta-audit)

---

## Uncertainties & Questions for BE

1. **Event type completeness**: Are there any event types I've missed? Specifically: MWL operations (MWL SCP), worklist status changes, HL7 message ingestion, share link creation/access?
2. **Retention policy**: How far back does the audit log go? Is there automatic purging (e.g. delete after 1 year)? Configurable?
3. **Time window queries**: Can I request events for an arbitrary time window (e.g. "show me everything between Jan 1 and Jan 15"), or only paginated from newest?
4. **Live mode filter scope**: When live polling is active and filters are applied, does the backend return only events matching the filters since the last poll, or all events (filtered client-side)?
5. **CSV export scope**: Is client-side export (current page only) acceptable for now, or do we need server-side full-result-set export?
6. **Payload schema**: What fields are included in the expandable JSON payload? For example: `study_uid`, `series_uid`, `instance_uid`, `request_ip`, `user_agent`, `previous_values` (for edits), `error_message` (for failures). Can we get a representative example per event type?
7. **Tenant scoping**: For super_admin viewing cross-tenant events, should the tenant filter default to "All tenants" or require explicit selection?
8. **Meta-audit**: Is there existing infrastructure for logging access to audit log entries themselves (to satisfy HIPAA's "audit of audit logs" requirement)?
