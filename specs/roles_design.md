# Feature: Roles — Permission Matrix UI

## Current State

Roles page at `/roles` (222 lines, single component). Table shows Name/Slug/Permissions/Built-in/Action columns. Create/edit modal has name/slug inputs + flat permission checkboxes in groups. Delete with Popconfirm. Built-in roles hide action column.

Backend has full CRUD in `api/roles.py` with audit logging, token version bump on permission changes, built-in role protection.

## Gaps vs Requirements Doc

1. **Description** — field missing from table + form + backend schema
2. **User count** — no column showing users per role
3. **Permission count** — not shown (easy, computed client-side)
4. **Built-in lock icon** — missing lock indicator
5. **Immutable admin** — super_admin permissions should be uneditable
6. **Permission search** — no search/filter within modal
7. **Group select-all** — no select/deselect all per group
8. **Expandable permissions** — no way to see full set without clicking edit
9. **`/api/permissions`** — no endpoint to list all available permissions
10. **`/api/roles/{id}/users`** — no endpoint to list users per role

## Changes

### Backend

1. **Migration 028**: Add `description TEXT` column to roles table
2. **`db/roles.py`**: Add user_count subquery to `get_all()`, include description in response
3. **`api/roles.py`**: Add `PermissionsHandler` at `/api/permissions`, `RoleUsersHandler` at `/api/roles/{id}/users`
4. **`api/schemas/roles.py`**: Add optional `description` field to CreateRoleRequest, UpdateRoleRequest
5. **`api/permissions.py`**: Add `PERMISSION_GROUPS` constant for grouped permission listing

### Frontend

**`Roles.tsx`** — major rewrite:
- Description column in table
- User count column (with link to filtered users page)
- Permission count display
- Built-in lock icon + `(Built-in)` label
- Edit button disabled for super_admin + tooltip "Immutable built-in role"
- Expandable permission view in table rows (full permission set list)
- Permission search input in create/edit modal
- Group-level select all / deselect all checkboxes
- Group header shows `(selected/total)` counts

### Security

| Check | Status |
|-------|--------|
| Auth required | ✅ Already behind ROLE_READ/WRITE/DELETE |
| Built-in protection | ✅ Backend rejects DELETE for built-in, name changes blocked |
| Admin immutability | ✅ super_admin permissions not editable via UI |
| Audit logged | ✅ Already logs role.created / role.updated / role.deleted |
