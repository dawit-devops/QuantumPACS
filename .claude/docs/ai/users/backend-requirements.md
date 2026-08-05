# Users Management — Backend Requirements

## Context

User management page at `/users`. Used by PACS Admins to manage user accounts. Lists users with ID, Username, Role (inline dropdown + permission tooltip), Admin flag, Status. Supports creating, deactivating, role-switching, password reset, and bulk CSV import.

## Screens/Components

### User List Table

**Purpose**: Browse, filter, sort, and manage all user accounts.

**Data I need to display**:
- User ID (numeric, used as row key)
- Username
- Role name + role ID (for inline Select dropdown)
- Admin flag (boolean, rendered as colored Tag)
- Status (string, rendered as colored Tag — currently "active" or other)
- Full permission list for the user's role (for InfoCircle tooltip)

**Actions**:
- Change user role via inline Select dropdown → immediately persists; no confirm step
- View role permissions via InfoCircle tooltip → shows role name + comma-separated permission slugs
- Reset password → returns the new cleartext password; displayed in a modal. Admin copies it and shares with user (no email delivery)
- Deactivate user → Popconfirm, then sends deactivate request; row disappears or status changes
- "Add user" button → opens creation modal
- "Bulk Import" button → opens CSV import modal

**States to handle**:
- **Loading**: Table spinner while user list is fetched
- **Empty**: "No users found" message + Add user button
- **Error**: Error message with retry button
- **Sorting**: Sortable by ID, Username (sorter params sent to backend)
- **Pagination**: Server-side pagination with page, pageSize, sortField, sortOrder params

**Business rules affecting UI**:
- Deactivate button only shown for users with `status === 'active'`
- Deactivated users show Status tag in gray; no action column rendered
- Admin tag is green for admin, geekblue for non-admin
- Only "active" users show action buttons

### Create User Modal

**Purpose**: Admin creates a new user account.

**Data I need to display**:
- Username input (required)
- Admin checkbox (optional, defaults to false)
- Role dropdown (populated from roles list, optional)

**Actions**:
- Submit form with username + admin flag → server creates user, generates password
- Server returns the generated username and cleartext password
- A result modal displays the credentials so admin can share them with the user
- Close result modal → refreshes user list

**States to handle**:
- **Validation error**: Inline field errors from form rules (username required)
- **Server error**: Message.error with server response message
- **Success**: Show result modal with credentials; user added to list after dismiss

### Bulk Import Modal

**Purpose**: Import many users at once via CSV upload with preview and sequential import.

**Data I need to display**:
- CSV file drop zone with format hint: "username,admin (one per line)"
- Preview table showing parsed rows (Username, Admin, Status columns)
- Progress bar during import
- Success/fail counts per row in the preview table

**Actions**:
- User selects/upload a CSV file → client-side parse, display preview table
- User clicks "Import {N} Users" button → sequential POST to users endpoint for each row
- Each row updates its status (Pending → Imported/Failed) in real-time
- After import: success message with counts; if any succeeded, refresh user list

**States to handle**:
- **No file selected**: Drop zone only; no preview table
- **File selected + parsed**: Preview table with Pending status per row
- **Importing**: Progress bar + per-row status updates; import button disabled
- **Import complete**: Final success/fail toast; reload user list on any success
- **Invalid CSV**: Warning message if no valid rows found after parsing
- **Empty file**: Warning, no preview shown

**Business rules affecting UI**:
- CSV parsed client-side: splits by newline, skips header row, splits by comma, trims whitespace
- Admin column accepts `true`/`false` or `1`/`0`
- Each row imported individually via the same `users` endpoint as single create
- Rows with empty username are skipped

## Uncertainties
- [ ] When an admin changes a user's role, do existing tokens get invalidated?
- [ ] Can a user be permanently deleted, or only deactivated?
- [ ] What happens when a deactivated user tries to log in?
- [ ] Is there a minimum password strength requirement?
- [ ] Should the CSV import support updating existing users or only creating new ones?
- [ ] Role is now assignable at creation — should it remain optional or be required for non-admin users?
- [ ] The list pagination contract is inconsistent across code paths: one fetcher expects a `meta` block (total/page/per_page/total_pages) with offset/limit paging, while the legacy screen guesses totals from the current page length. Which is canonical?
- [ ] Inline role change is issued via different HTTP semantics in different code paths (one defaults to POST, another explicitly PUT) — the screen must use the backend's expected semantics.
- [ ] What fields beyond username + admin can be set at creation (email, role, etc.)?

## Questions for Backend
- Do I need to send the current password when an admin resets another user's password?
- Is there a way to list available roles (for the role dropdown) separate from users — I already fetch `roles` separately; is that the right endpoint?
- Should the import report show line-number errors or field-level errors?
- Can a user have multiple roles or is it exactly one role per user?
- Is there an endpoint to get a user's current active sessions?
- The password reset flow returns a cleartext password in the response — is that the intended UX (admin copies and shares manually)?
- Is role assignment available during user creation, or only via the inline dropdown after creation?

## Discussion Log
- *(To be filled after backend review)*
