# Account Page — Backend Requirements

## Page
`GET /account` — All authenticated users

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/account/profile` | Get current user profile |
| `PUT` | `/api/account/profile` | Update profile fields |
| `POST` | `/api/account/change-password` | Change password |
| `GET` | `/api/account/sessions` | List active sessions (future) |
| `POST` | `/api/account/logout-all` | Logout from all devices (future) |

## Data Model

```
UserProfile {
  id: uuid
  username: string
  email: string
  role: string              // e.g. "radiologist", "technologist", "admin"
  role_display_name: string
  tenant: string
  tenant_display_name: string
  permissions: string[]     // resolved permission list
  created_at: datetime
  last_login: datetime | null
}
```

## Profile Display
- Username (read-only)
- Email (read-only or editable — see Q1)
- Role name
- Tenant name
- Permissions list (flat list of permission strings, shown as tags)
- Created date
- Last login timestamp

## Change Password
- Requires current password for verification
- New password must meet validation rules (min length, complexity)
- On success: invalidate all other sessions (optional), return success message
- Backend validates current password before accepting change

## Future Features (documented but not implemented)
- Session list: show active sessions with device info, IP, last active timestamp
- Logout all devices: invalidate all refresh tokens except current

## Uncertainties & Questions
1. What profile fields can a user change themselves vs. admin-only?
2. For password change, do I need the current password or can I use a token-based flow?
3. Should I show the user's permission list or just their role name?
4. Is there a concept of "profile picture" or avatar?
