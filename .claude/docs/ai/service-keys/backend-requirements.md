# Service Keys — Backend Requirements

## Page
`GET /service-keys` — PACS Admins, Technologists

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/service-keys` | List all keys |
| `POST` | `/api/service-keys` | Create a new key |
| `POST` | `/api/service-keys/{id}/revoke` | Revoke a key |
| `GET` | `/api/service-keys/{id}` | Get single key details |

## Key Format
- Prefix: `qpk_`
- Total length: 55 characters
- Stored in DB as SHA-256 hash
- UI shows prefix only: `qpk_` + first 8 chars of hash for identification

## Data Model

```
ServiceKey {
  id: uuid
  prefix: string          // qpk_ + first 8 chars
  name: string
  permissions: string[]   // e.g. ["dicom:read", "dicom:write", "admin:read"]
  created_at: datetime
  last_used_at: datetime | null
  expires_at: datetime | null
  revoked_at: datetime | null
  is_active: boolean      // computed: !revoked && (!expires_at || expires_at > now)
}
```

## Key List Columns
- Prefix + name
- Permissions (tag/badge list)
- Created date
- Last used timestamp
- Expiry status indicator:
  - Green: >7 days until expiry
  - Yellow: ≤7 days until expiry
  - Red: ≤1 day until expiry
  - Grey: expired
  - No indicator: permanent (no expiry)

## Key Creation Flow
1. User enters key name, selects permissions
2. Backend generates key, returns full key once in response body
3. Full key is shown in UI with "Copy to Clipboard" button
4. After dismissal, key is never shown again — only prefix remains visible

## Revocation
- Revoked keys immediately invalidate — all API calls with that key return 401
- UI shows "Active Integrations May Be Affected" confirmation dialog
- Revoked keys remain in the list (option to show/hide revoked)

## Uncertainties & Questions
1. Can service keys expire, or are they permanent until revoked?
2. What permissions can be assigned to a key?
3. Is there a limit on number of keys per tenant?
4. Can I edit a key's permissions after creation, or must I revoke and recreate?
5. Does "last used" update on every API call?
6. Is there a way to test a key before giving it to an integrator?
