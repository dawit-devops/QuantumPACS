# Backend Requirements — Share Tab (Expiring Share Links)

## Current Implementation

### Endpoint
`POST /api/files/{id}/share` — creates a share link for a file.

**Request body:**
```json
{ "duration": 24 }
```
- `duration`: integer, hours until link expires

**Response:**
```json
{ "key": "a1b2c3d4e5f6..." }
```
- `key`: 64-char hex string generated via `os.urandom(64).hex()`

### Auth
JWT (`X-Auth-Pacs`) with `FILE_WRITE` permission.

### Database — `shared_files` table
```sql
CREATE TABLE shared_files (
    id          SERIAL PRIMARY KEY,
    created     TIMESTAMP NOT NULL DEFAULT (now() at time zone 'utc'),
    expires     TIMESTAMP NOT NULL,
    file_id     INTEGER NOT NULL REFERENCES files(id) ON DELETE CASCADE,
    hash        TEXT NOT NULL                     -- the share key (urandom(64).hex())
);
CREATE INDEX shared_files_hash ON shared_files(hash);
```

### Share Link Verification (`SharedFiles.check(key)`)
- Lookup by `hash` column
- If `expires < now()` → delete row, return `None`
- Otherwise return `file_id`

### Auth Middleware Integration
In `api/auth.py` `TokenAuth.authenticate`:
- If JWT verification fails, attempt `SharedFiles(conn).check(credentials)` as fallback
- If valid: allow access to `GET /api/files/{file_id}/data` and `POST /api/ws_token` only
- Share-key-authenticated user has `{'id': key, 'admin': False}` — no permissions, no role

### Frontend Behavior (Share.tsx)
- Duration input (hours, InputNumber min=1 max=8760)
- Submit → `request(\`files/${id}/share\`, { data: { duration } })` → receives `{ key }`
- Constructs URL: `` `${window.location.origin}/view/${key}` ``
- Copy to clipboard with `navigator.clipboard.writeText` (fallback to `document.execCommand('copy')`)
- CheckOutlined visual feedback for 2s on copy
- Native share: `navigator.share({ title, text, url })` with fallback to clipboard
- Monospace URL display in Input field
- Security notice: "This link expires after the specified duration. Anyone with the link can view the study."
- **No existing link list** — only "create" flow

### View-Only Mode (Detail.tsx)
- `tempKey` stored in `localStorage` (set from `?key=` query param on page load)
- If `tempKey` is set: Share tab is hidden, only Image tab shown
- No annotations? Currently `tempKey` doesn't disable annotations — need to confirm

---

## Required Coverage

### Create Share Link
- [x] Duration selection (hours, 1–8760)
- [x] 64-char hex key generation (`os.urandom(64).hex()`)
- [x] URL construction: `{origin}/view/{key}`
- [ ] Should duration accept days in addition to hours?

### Copy Link
- [x] Clipboard API (`navigator.clipboard.writeText`)
- [x] Fallback: `document.execCommand('copy')` via textarea
- [x] Visual confirmation (CheckOutlined icon, 2s)

### Native Share
- [x] `navigator.share()` with title + text + url
- [x] Fallback to clipboard copy when unavailable

### Link List (Not Implemented)
- [ ] GET endpoint to list active shares for a file: `GET /api/files/{id}/shares`
- [ ] Each entry: creation date, duration, expiration, status (active/expired)
- [ ] Frontend: table of existing share links
- [ ] Should show active vs expired status

### Revoke Link (Not Implemented)
- [ ] DELETE endpoint: `DELETE /api/files/{id}/shares/{share_id}`
- [ ] Frontend: revoke button per active link
- [ ] On revoke: delete row from `shared_files`

### View-Only Mode Characteristics
- [ ] No annotations/measurements allowed
- [ ] No download button (ServeFile endpoint blocked)
- [ ] Only Image tab visible (confirmed: Share tab hidden)
- [ ] No Data/Changes/Management tabs
- [ ] What about the `tempKey` approach? Current: stored in localStorage, used for auth header. Need to scope.
- [ ] Should the viewer page be a separate route (`/view/{key}`) instead of leveraging `/files/{id}`?

---

## Uncertainties & Questions

| # | Question | Status |
|---|----------|--------|
| 1 | Can multiple share links exist for the same file? If so, how many? (Current schema allows unbounded) | Unresolved |
| 2 | Is the link per-file or per-study? Per-study would be more useful for referring physicians (see all images in a study). | Unresolved |
| 3 | Should duration be in hours only (current) or also support days/weeks? | Unresolved |
| 4 | Can users see how many times a shared link has been accessed? (access tracking / analytics) | Unresolved |
| 5 | Should the share status indicator appear in the file list (Files page) so users know which studies have active shares? | Unresolved |
| 6 | What happens to active view sessions when a link is revoked? (stale localStorage key → 401 on next request) | Unresolved |
| 7 | Can a share be tied to a specific recipient (access tracking by email/identity)? | Unresolved |
| 8 | Is the current `/view/{key}` frontend route served by the SPA? There is no matching React Router route for `/view/:key`. | Unresolved |
| 9 | Should the share link grant access to all files in the same study/series, not just the single file? | Unresolved |
| 10 | What viewer capabilities should be restricted in view-only mode? (download, annotations, measurements, keyboard shortcuts, fullscreen?) | Unresolved |
