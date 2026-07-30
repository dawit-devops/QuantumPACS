# Feature: Share Links — List & Revoke

## Existing State

The create-link flow works: `POST /api/files/{id}/share` creates a 64-char key, frontend shows it in a modal with copy/share buttons. Missing pieces:

1. **No link list** — Created links are invisible (no way to see what's active)
2. **No revoke** — Once created, links can't be deleted
3. **No `/view/:key` route** — Generated URLs `{origin}/view/{key}` 404

## Changes

### Backend

**New methods in `db/share_files.py`:**
- `list_for_file(file_id)` — returns `[{id, created, expires, hash}]` for a file
- `revoke(share_id, file_id)` — deletes row by id + file_id (scoped to prevent cross-file deletion)

**New handler endpoint** — `ShareFilesListHandler` in `api/files.py`:
- `GET /api/files/{id}/shares` — lists active shares for the file (requires FILE_READ)
- `DELETE /api/files/{id}/shares/{share_id}` — revokes a share (requires FILE_WRITE)

### Frontend

**Share.tsx** — Add links list below the generate form. Table with columns:
- Created date
- Expires date
- Status tag (Active/Expired)
- Revoke button (active only)
- Copy link button per row

**index.tsx** — Add `<Route path="/view/:key" element={<ShareView />} />` that extracts key from path, stores in localStorage as `tempKey`, redirects to home or the referenced file.

### Security

| Check | Status |
|-------|--------|
| Auth required | ✅ Behind middleware with permission checks |
| Authz (own file) | ✅ Shares are scoped to `file_id` — can only list/revoke if you have access to the file |
| Input validation | ✅ Path params validated by Starlette routing |
| Rate limiting | Not needed (read/list operations) |
| Logging | Revoke events should be logged |
