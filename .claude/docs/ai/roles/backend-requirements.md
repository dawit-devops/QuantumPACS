# Roles Management — Backend Requirements

## Context

Roles management page at `/roles`. Used by PACS Admins to configure RBAC roles. Lists roles with their permission sets. CRUD operations. 34 permission slugs across 13 resource domains. 5 built-in roles that are protected from deletion.

## API Endpoints Required

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/roles` | List all roles (with permission count, user count, built-in flag) |
| GET | `/api/roles/{id}` | Get single role with full permission set |
| POST | `/api/roles` | Create new role |
| PUT | `/api/roles/{id}` | Update role (name, description, permissions) |
| DELETE | `/api/roles/{id}` | Delete role (reject for built-in roles) |
| GET | `/api/roles/{id}/users` | List users assigned to a role |
| GET | `/api/permissions` | List all available permission slugs grouped by domain |
| POST | `/api/roles/{id}/test` | Simulate what a user with this role can access |

## Data Model

```
Role {
  id: uuid
  name: string (unique, max 64 chars)
  description: string (max 255)
  is_builtin: boolean
  permissions: string[]   // e.g. ["study:read", "study:write", ...]
  user_count: number
  created_at: datetime
  updated_at: datetime
}
```

### 34 Permission Slugs — 13 Resource Domains

| Domain | Slugs |
|--------|-------|
| study | study:read, study:write, study:delete, study:anonymize, study:merge, study:export |
| patient | patient:read, patient:write, patient:merge, patient:delete |
| series | series:read, series:write, series:delete, series:reorder |
| modality | modality:read, modality:write, modality:configure |
| routing | routing:read, routing:write, routing:delete, routing:test |
| user | user:read, user:write, user:delete |
| role | role:read, role:write, role:delete |
| audit | audit:read, audit:export |
| worklist | worklist:read, worklist:write, worklist:assign |
| report | report:read, report:write, report:approve |
| dicom | dicom:send, dicom:receive, dicom:query |
| system | system:configure, system:logs, system:backup |
| billing | billing:read, billing:write, billing:void |

### 5 Built-In Roles (Protected from Deletion)

| Role | Description |
|------|-------------|
| `admin` | Full system access, all permissions |
| `radiologist` | Study/patient/series read+write, report write+approve |
| `technologist` | Modality operations, worklist management |
| `viewer` | Read-only access to studies and reports |
| `billing` | Billing read/write, limited study read |

### Built-In Role Protection Rules

- Built-in roles (`is_builtin: true`) **cannot be deleted** — DELETE returns 403
- Built-in role **name cannot be changed** — PUT rejects name changes
- Built-in role **description can be changed**
- Built-in role **permission set can be modified** (except `admin`)
- The `admin` role's permission set is immutable

## UI Behavior Notes

### Role List
- Each row shows: name, description, permission count, built-in badge, user count
- Built-in roles have a lock icon and "(Built-in)" label
- Delete button hidden/disabled for built-in roles
- User count links to user list filtered by that role

### Create/Edit Form
- **Name**: text input, required, unique, max 64 chars
- **Description**: textarea, optional, max 255 chars
- **Permissions**: 13 collapsible groups (one per domain), each group has a toggle-all checkbox
- Each permission rendered as a labeled checkbox with the slug shown as a subtitle
- Search/filter input to find permissions by name or slug

### Permission Groups UI
- 13 groups displayed as accordion/collapsible sections
- Group header shows domain name + (selected/total) count
- "Select All" / "Deselect All" per group
- Quick-select presets: "Radiologist-like", "Technologist-like", "Read-only"
- Changes not saved until form is submitted

### Role Change Effects
- When role permissions are modified, all active sessions for users with that role should receive a token invalidation
- Implementation: bump `role_version` on the role → JWT includes `role_version` claim → middleware checks and rejects stale tokens
- Users currently on a page that relies on the removed permission will see a 403 on next API call → UI should show a permission denied toast and redirect to home

## Uncertainties

- [ ] When role permissions change, are all users with that role immediately affected?
- [ ] Can I change the name of a built-in role or just the description?
- [ ] How do I know which users have a given role?
- [ ] Is there a way to test a role's effective permissions before applying?

## Questions for Backend

- Should I display all 34 permissions as flat list or grouped by resource domain?
- Can I get a count of users per role?
- What happens if I remove a permission that a user is currently relying on (e.g., they're on the page)?
- Is there a "permission audit" that shows which permissions are unused?
