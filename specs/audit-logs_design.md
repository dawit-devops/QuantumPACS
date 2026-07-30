# Feature: Audit Logs — HIPAA Compliance Page

## Current State

`/logs` shows generic app logs (info/warn/error/debug) from the `logs` table.
Backend `LogsHandler` reads from `Log` model (app logs) or `AuditLog` wrapper, both sharing the same table.
`AuditLog` stores JSON payload in `logs.log` as TEXT with fragile LIKE-based filtering.
Frontend shows Time/Type/Log columns with offset pagination.

## Target State

Structured HIPAA audit log viewer with proper event types, actor tracking, resource columns, date/user/tenant filtering, cursor pagination, live streaming, and CSV export.

## Changes

### Backend: `db/audit_log.py`
- Rewrite `query()`: filter by `event_type` (JSONB extraction), `actor` (text search on parsed username), `date_from`/`date_to`, `tenant`, cursor-based pagination
- Parse JSON payload inline and join with `users` table for display names
- Add `get_event_types()` to return distinct event types
- Add `get_actors()` to return recent actor names
- Add `count()` supporting same filters

### Backend: `api/logs.py`
- Rewrite `LogsHandler.get()` to accept structured query params
- Response: `{data, next_cursor, has_more, total}`
- Return structured fields: `id, created_at, event_type, actor, resource_type, resource_id, description, tenant, payload`
- Add `GET /logs/event-types` and `GET /logs/actors` endpoints

### Frontend: `Logs.tsx`
- Complete rewrite — structured columns table
- Event type filter: multi-select chips grouped by category (Data Access, Auth, User, System, etc.)
- Date range picker with 90-day max
- Actor text filter
- Tenant dropdown (super_admin only)
- Live toggle with 5s polling + highlight animation on new rows
- Cursor-based pagination mapped to Ant Design Table onChange
- Expandable rows with `<pre>` formatted JSON payload
- CSV export with proper fields (Timestamp, Actor, Event Type, Resource, Description, Tenant, Payload)

### Security

| Check | Status |
|-------|--------|
| Auth required | ✅ Already behind `LOG_READ` permission |
| Tenant scoping | ✅ Non-super sees own tenant only; super can filter by tenant |
| System events | ✅ Hidden from non-super |
| Action logging | Optional — log audit log access (meta-audit) |
