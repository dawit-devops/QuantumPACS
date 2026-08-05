# Feature: Account Page

## Requirements (from `.claude/docs/ai/account/backend-requirements.md`)

| Endpoint | Purpose | Existing |
|----------|---------|----------|
| `GET /account/profile` | Get current user profile | ❌ Missing |
| `PUT /account/profile` | Update profile (email) | ❌ Missing |
| `POST /change_password` | Change password | ✅ Exists, but missing `current_password` |

## Architecture

### [Backend]

**Migration `025`** — Add `email`, `last_login` to `users`:
```sql
ALTER TABLE users ADD COLUMN IF NOT EXISTS email VARCHAR(255) DEFAULT '';
ALTER TABLE users ADD COLUMN IF NOT EXISTS last_login TIMESTAMP;
```

**New schemas** (`api/schemas/account.py`):
- `UpdateProfileRequest`: `email: str | None`
- `ChangePasswordRequestV2`: `current_password: str, new_password: str`, `new_password2: str | None` (validator: match)

**New endpoints** (`api/account.py`):
- `GET /account/profile` — reads `request.user.id`, queries `users + roles + tenants`, returns `ProfileResponse { id, username, email, role, role_display_name, tenant, tenant_display_name, permissions, created_at, last_login }`
- `PUT /account/profile` — accepts `{ email }`, updates current user's email

**Updated endpoint** (`api/users.py:ChangePassword`):
- Rename to accept `ChangePasswordRequestV2` with `current_password`
- Verify `current_password` against stored hash before accepting new password
- Block current token after change (already does this)

**Login update** — `POST /login` stores `last_login = now()` after successful auth.

**Route** — Register `/account/profile` in `routes.py`

### [Frontend]

**`Account.tsx`** — currently bare password form. Rewrite to show:

1. **Profile Card** — avatar placeholder (initials), username, email (editable inline), role badge, tenant name, permissions as tags, created/last-login dates
2. **Change Password Card** — existing form but with `current_password` field added
3. **Layout** — Ant Design `Card` components in a vertical stack, max-width 640px

**Data fetching** — `useFetch('account/profile')` on mount. PUT via `request('account/profile', { method: 'PUT', body })`.

**API client** — `helpers.ts:request()` already handles auth headers.

### [Security]

| Check | Status |
|-------|--------|
| Auth required? | ✅ All endpoints behind middleware (user must be authenticated) |
| Authz (self-only)? | ✅ Endpoints derive user from `request.user`, no user-supplied IDs |
| Input validation? | ✅ Pydantic schemas for PUT + change_password |
| Rate limiting? | ⚠️ Change password should have rate limiting (separate from login bucket?) |
| Current password required? | ❌ Added in this change — prevents session hijacking from unattended machine |
| Sensitive data in response? | ✅ Profile response excludes password hash, token version, status |
| Security event logging? | ✅ Password change + email change should be logged |

Rate limiter for password change: use a separate Redis bucket keyed by `user_id` (not IP) — 3 attempts per 5 minutes.

## Implementation Order

1. Alembic migration `025`
2. New schemas + account endpoints
3. Update ChangePassword schema + verify current_password
4. Update login to set last_login
5. Register routes
6. Rewrite Account.tsx
7. Build verification
