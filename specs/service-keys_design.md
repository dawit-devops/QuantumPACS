# Feature: Service Keys — UI Polish

## Existing State

Backend is complete: CRUD endpoints, key generation (`qpk_` prefix, SHA-256), `X-API-Key` middleware, full test coverage.
Frontend has table + create modal + revoke. Missing: permissions, expiry badges, last used, show/hide revoked.

## Changes (all frontend)

**`ServiceKeys.tsx`:**
1. Add permission `Checkbox.Group` to create modal (grouped by domain)
2. Add permissions column with tags
3. Add expiry status indicators: green (>7d), yellow (≤7d), red (≤1d), grey (expired), none (permanent)
4. Add last_used column with relative time
5. Add show/hide revoked toggle switch
6. Update revoke confirmation: "Active integrations may be affected"
7. Compute `is_active` from `enabled + expires_at` in the table data

No backend changes needed — all required data is already returned by API.

### Security

| Check | Status |
|-------|--------|
| Auth required | ✅ Already behind SERVICE_KEY_READ/WRITE/DELETE |
| Input validation | ✅ Backend Pydantic schema accepts `permissions` list |
| Rate limiting | Not needed |
