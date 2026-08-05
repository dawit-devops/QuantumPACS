# ADR-024: Share Links via Short-Lived TempKey (Query-String) Auth

## Status
Accepted

## Date
2026-08-02

## Context
Users need to share a DICOM file with someone who has no account (a referring
physician, a patient portal). A link must work unauthenticated but must be
revocable, time-boxed, and scoped to exactly one file — and must never leak a
real JWT into URLs (browser history, logs, referrer headers).

## Decision

- `POST /api/v2/files/{id}/share` (requires `FILE_WRITE`) creates a random
  key (`rand_str()`) stored in the `shared_files` table with a TTL expiry
  (`duration` hours). The key is returned once.
- `GET /api/v2/files/{id}/shares` lists active shares (hash truncated to 12
  chars); `DELETE /api/v2/files/{id}/shares/{share_id}` revokes one.
- Anonymous access: `?token=<key>` on HTTP is accepted **only as a share key** —
  the auth layer (`backend/api/auth.py`) refuses full JWTs in query strings
  ("JWTs must travel via header or HttpOnly cookie so tokens never hit URLs").
- Scope enforcement: a share key is honored only for paths under
  `/api/files/{file_id}` and `/api/ws_token`, where `file_id` is the exact
  file the key was created for.
- `check()` auto-deletes expired keys on first use; `cleanup_expired()`
  sweeps expired rows.

## Alternatives Considered

- Signed URL (HMAC over file_id+expiry): stateless but not revocable before
  expiry.
- Full unauthenticated read: no scope, no TTL, unacceptable for PHI.

## Consequences

- Revocable, time-boxed, single-file links with no JWT exposure.
- Keys are stored in the DB and are bearer credentials — treat like passwords
  (log them truncated only, hash at rest in future hardening).
- `?token=` acceptance is narrowly path-scoped; any future endpoint added to
  that allow-list must be reviewed for PHI exposure.
