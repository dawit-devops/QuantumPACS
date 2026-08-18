# Technical Design — super_admin platform-ops features (user-feature-review)

Source: `docs/user-feature-review/super-admin/03-handoff.md` + `04-design.md`.
Branch: `phase/user-feature-review-super-admin`. Stack: Starlette + asyncpg + Alembic (backend), React 19 + Ant Design v6 + Vite (frontend).

## Scope

| Item | Backend | Frontend |
|------|---------|----------|
| P1-1 Notification prefs | `notification_prefs` table; GET/PUT `/api/notifications/preferences`; fan-out gating in `api/notify.py` + `files.py` upload receipt | `/account/notifications` page; bell-drawer footer link |
| P1-2 Maintenance mode | `platform_state` table; in-process flag + DB source of truth; write-gate middleware (503); `GET /api/admin/status` (public), `POST /api/admin/maintenance` (SYSTEM_ADMIN) | `/admin/maintenance` page; global shell banner + login banner |
| P2-1 Backups | `backups` table; `POST/GET /api/admin/backups`, `GET …/download`, `DELETE …/{id}`; metadata-manifest artifact on master storage; audit `system.backup_completed/failed` | `/admin/backups` page |
| P2-2 Audit export | `GET /api/logs?download=csv` (full filtered set, server-side) | Logs "Export all N" button; event-chip catalog sync |
| P2-3 Config page | `system_settings` table; `GET/PUT /api/admin/config` whitelist; startup merge + live in-process update for runtime-safe keys | `/admin/settings` page |
| P2-4 Console hygiene | — | `Statistic valueStyle`→`styles.content`; drop `rowKey` index param; fix tbody key warning |
| P2-5 Role membership | (API `GET /roles/{id}/users` exists) | Roles "Users" modal |
| P2-6 Sidebar a11y | — | Notification count split from accessible label |

## Security checkpoint (fullstack-guardian)

- **Authn**: all new endpoints behind the existing JWT middleware; `/api/admin/status` is added to `TokenAuth._PUBLIC_PATHS` (maintenance state is non-sensitive status, like a status page).
- **Authz**: maintenance/config/backups endpoints gated `requires_permission(Permission.SYSTEM_ADMIN)` — only super_admin holds it; notification prefs gated `FILE_READ` (matches existing notification endpoints) and are strictly per-`request.user.id`.
- **Validation**: `parse_body()` + Pydantic v2 schemas (`MaintenanceRequest`, `ConfigUpdateRequest` with whitelist key allowlist, `BackupRestoreRequest`, `NotificationPrefsRequest`). Backups/restore take an id path param parsed as UUID.
- **Output encoding**: all responses via `ok()`/`api_error()`; config values rendered by the frontend as React text (auto-escaped); CSV export built server-side with `csv.writer` (no formula-injection risk beyond standard CSV escaping; values are audit payload strings).
- **CSRF**: frontend `request()` always sends `X-CSRF-Token: 1`; new POST/PUT/DELETE endpoints are covered by `CSRFMiddleware`.
- **Least privilege**: config GET returns only whitelisted keys, never secrets; backup artifacts contain file metadata (uids, hashes, sizes) — no pixel data, no user passwords.
- **Audit**: every mutation (maintenance on/off, config change, backup start, backup delete) writes an audit event.

## Data model (migration 060)

```sql
CREATE TABLE notification_prefs (
  user_id    bigint NOT NULL,
  event_type text   NOT NULL,
  enabled    boolean NOT NULL,
  PRIMARY KEY (user_id, event_type)
);
CREATE TABLE platform_state (
  key        text PRIMARY KEY,
  value      jsonb NOT NULL,
  updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE system_settings (
  key        text PRIMARY KEY,
  value      jsonb NOT NULL,
  updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE backups (
  id           uuid PRIMARY KEY,
  status       text NOT NULL,          -- running | completed | failed
  kind         text NOT NULL DEFAULT 'metadata',
  artifact_key text,
  size_bytes   bigint NOT NULL DEFAULT 0,
  files_count  int NOT NULL DEFAULT 0,
  bytes_count  bigint NOT NULL DEFAULT 0,
  created_by   bigint,
  created_at   timestamptz NOT NULL DEFAULT now()
);
```

## Key decisions

1. **Notification default resolution**: a pref row wins; absent row → role default (super_admin: clinical events OFF, everything else ON). `CLINICAL_EVENT_TYPES = {study.arrived, study.verified, worklist.performed, share.accessed, annotation.shared, report.ready}`. `files.py` upload receipt and `notify_role`/`notify_user` consult `is_enabled(conn, user_id, event_type, role_slug)`.
2. **Maintenance gate**: `MaintenanceMiddleware` (or a check in `CustomMiddleware.dispatch`) reads an in-process flag (`platform_state` loaded at startup, updated by the admin endpoint + a 1s-TTL refresh). Non-GET/HEAD/OPTIONS on `/api/**` (excluding login/refresh/logout, the admin maintenance endpoint, and share-key GETs) return `503 MAINTENANCE` with a readable message. DICOMweb STOW writes are blocked; WADO reads pass.
3. **Config whitelist**: runtime-safe keys (read live from the module `config` dict): `max_upload_size_mb`, `max_stow_size_mb`, `tenant_usage_retention_days`; restart-required keys (stored, flagged in UI): `token_expiry_days` (tokens.py reads `expire={'days': 14}` default — stored value surfaced as recommendation; changing it requires restart per design), `allowed_hosts`, `cors_origins`, `cookie_secure`. PUT writes `system_settings` and updates the in-process dict for runtime-safe keys.
4. **Backup artifact**: JSON manifest of `files` metadata (id, name, hash, patient/study/series/sop uids, size, created_at, tenant) + replica master info + totals, written to master replica storage as `backup/<ts>.json`, row recorded, `system.backup_completed` emitted on success / `system.backup_failed` on error. **Restore = artifact download + verification (dry-run) report; destructive in-place rehydration is a documented follow-up** (safety: never overwrite live data from a review feature).
5. **CSV export**: `LogsHandler.get` with `download=csv` streams `csv.writer` rows of the full filtered set (chunked fetch via `AuditLog.query` limit 200 loop) as `text/csv` with `Content-Disposition`; unchanged JSON path for the page.

## Files touched

Backend: `migrations/versions/060_platform_admin_ops.py`, `db/notification_prefs.py` (new), `api/notifications.py`, `api/notify.py`, `api/files.py`, `api/admin.py` (new), `api/routes.py`, `api/auth.py` (public path), `app.py` (maintenance gate + startup load), `api/logs.py`, `api/schemas/admin.py` (new), `db/platform_state.py` (new), `db/system_settings.py` (new), `db/backups.py` (new), `db/audit_log.py` (bulk query helper).
Frontend: `api/admin.ts` (new), `api/notifications.ts`, `notifications/NotificationPreferences.tsx` (new), `maintenance/Maintenance.tsx` (new), `admin/Backups.tsx` + `admin/Settings.tsx` (new dir), `common/base.tsx` (banner), `login/Login.tsx` (banner), `common/Sidebar.tsx` (nav items + a11y), `index.tsx` (routes), `logs/Logs.tsx`, `roles/Roles.tsx`, `dicomweb/DicomWebAdmin.tsx` + `metrics/Metrics.tsx` (deprecation fixes).
Tests: `backend/tests/test_notification_prefs.py`, `backend/tests/test_admin_ops.py`, `backend/tests/test_logs.py` (csv), frontend `src/test/` additions where the new pages need coverage.

## Deviations from design (tracked)

- **Restore**: implemented as artifact download + verification report, not destructive in-place restore (see decision 4). Flagged in `05-implementation.md`.
- **Backup scheduling**: on-demand only; recurring schedule UI deferred (design P2-1 AC2 partial) — noted as follow-up.
- **Login-page banner**: `/api/admin/status` is public, so the login page can render the banner (implemented).
