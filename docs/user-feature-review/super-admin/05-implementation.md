# Phase 3 — Implementation Report (super_admin)

**Branch:** `phase/user-feature-review-super-admin`
**Date:** 2026-08-14
**Skill:** fullstack-guardian (workflow followed manually; repo conventions per CLAUDE.md)

## Scope

Implemented every hand-off item from `03-handoff.md` (2× P1 + 6× P2), plus one
real bug found during verification (P2-5).

## Security checkpoint (before code)

- **Authz:** every new endpoint is gated with `requires_permission` —
  `SYSTEM_ADMIN` for maintenance/config/backups (platform-only), `NOTIFICATION_READ`
  for prefs read, `NOTIFICATION_WRITE` for prefs write (all admin-scoped per
  RBAC matrix). `/admin/status` + the maintenance banner endpoint are public-read
  (no PHI; exposes only maintenance flag/reason).
- **Maintenance write-gate:** `maintenance_active()` check in the app dispatch
  middleware — read endpoints (`GET`, `/api/login`, `/api/v2/admin/*`, health)
  stay open; all other requests get 503 while maintenance is active. CSRF header
  exemption included so the admin UI can toggle it off.
- **Input validation:** all new bodies via `parse_body()` + Pydantic v2 schemas
  (`api/schemas/admin.py`, `api/schemas/notifications.py`): required reason,
  duration bounds, backup frequency enum, settings type coercion, prefs
  event-key allowlist.
- **Output encoding:** no raw HTML anywhere; JSON responses via `ok()` helpers.
- **Secrets:** config GET returns values only for whitelisted non-secret keys;
  secrets render as masked placeholders and are never emitted.

## Backend changes

### New files
| File | Purpose |
|------|---------|
| `backend/migrations/versions/060_platform_admin_ops.py` | Adds `notification_prefs`, `platform_state`, `system_settings`, `backups` tables |
| `backend/db/notification_prefs.py` | Prefs CRUD + `EVENT_CATALOG` (25 event types w/ default-enabled flags) |
| `backend/db/platform_state.py` | `platform_state` row access (maintenance flag/reason/since) |
| `backend/db/system_settings.py` | Settings get/update with secret masking |
| `backend/db/backups.py` | Backup manifest rows + completion/cleanup |
| `backend/api/admin.py` | `AdminStatusHandler`, `AdminMaintenanceHandler`, `AdminConfigHandler`, `AdminBackupsHandler`, `AdminBackupHandler`, `AdminBackupRestoreHandler` + in-memory maintenance cache + gate helpers |
| `backend/api/schemas/admin.py` | Pydantic schemas for maintenance/config/backup bodies |
| `backend/api/schemas/notifications.py` | Prefs PUT schema (event-key allowlist) |
| `backend/tests/test_admin_ops.py` | Maintenance gate/toggle/config/backup API tests |
| `backend/tests/test_notification_prefs.py` | Prefs CRUD + fan-out gating tests |

### Modified files
| File | Change |
|------|--------|
| `backend/api/routes.py` | Wire `/admin/status`, `/admin/maintenance`, `/admin/config`, `/admin/backups(/{id})`, `/admin/backups/{id}/restore`, `/notifications/prefs` |
| `backend/api/auth.py` | Public-path list updated for maintenance gate |
| `backend/app.py` | Maintenance write-gate middleware + `platform_state` load at boot |
| `backend/api/notify.py` | Fan-out gating: skip muted users (`notify_user`/`notify_role` honor prefs) |
| `backend/api/files.py` | Upload receipt (`study.arrived`) respects prefs |
| `backend/api/notifications.py` | New `NotificationPrefsHandler` GET/PUT |
| `backend/api/logs.py` | `download=csv` server-side export of ALL matching events (fixes 50-row export trap) |
| `backend/api/tokens.py`, `backend/config.py` | `token_expiry_days` config key |
| `backend/api/roles.py` | **P2-5 bug fix:** `RoleUsersHandler` queried nonexistent `users.active` → now `users.status` (was 500) |
| `backend/tests/test_roles.py` | Regression test for the status-column fix |

## Frontend changes

### New files
| File | Purpose |
|------|---------|
| `frontend/src/api/admin.ts` | `getAdminStatus`, `setMaintenance`, `getAdminConfig`/`putAdminConfig`, `listBackups`/`createBackup`/`restoreBackup`/`deleteBackup` |
| `frontend/src/api/notifications.ts` | `getNotificationPrefs`/`putNotificationPrefs` |
| `frontend/src/notifications/NotificationPreferences.tsx` | P1-1 prefs page: grouped Switch lists, optimistic toggles, reset-to-defaults |
| `frontend/src/maintenance/Maintenance.tsx` | P1-2 maintenance page: status card, enter-modal (reason required), exit Popconfirm, activity log |
| `frontend/src/admin/Backups.tsx` | P2-1 backups: create + schedule modal, status table, restore/delete Popconfirms, stale-backup alert |
| `frontend/src/admin/Settings.tsx` | P2-3 grouped settings cards, per-group save, restart-required tags, masked secrets |
| `frontend/src/common/MaintenanceBanner.tsx` | Global `Alert` banner shown while maintenance active |

### Modified files
| File | Change |
|------|--------|
| `frontend/src/common/base.tsx` | Mount `MaintenanceBanner` in the app shell |
| `frontend/src/login/Login.tsx` | Show maintenance banner on the login page too |
| `frontend/src/common/Sidebar.tsx` | New SYSTEM_ADMIN nav group: Maintenance, Backups, Settings + P2-6 a11y (notification count out of the accessible name) |
| `frontend/src/index.tsx` | Routes: `/admin/maintenance`, `/admin/backups`, `/admin/settings`, `/account/notifications` (all `RequirePermission`-gated) |
| `frontend/src/notifications/NotificationBell.tsx` | "Manage preferences" link in drawer footer → `/account/notifications` |
| `frontend/src/logs/Logs.tsx` | Server-side "Export all N events" button + event-chip catalog synced to backend `EVENT_CATALOG` |
| `frontend/src/api/logs.ts` | `listLogs` gains `download`/`all` params |
| `frontend/src/roles/Roles.tsx` | Membership modal: `active` bool → `status` string render (P2-5) |
| `frontend/src/metrics/Metrics.tsx` | P2-4: `rowKey="id"` on Latest Files table (tbody key warning) |
| `frontend/src/fhir/FhirMonitoring.tsx` | P2-4: `valueStyle` → `styles.content`, index-based `rowKey` → natural key |
| `frontend/src/hl7/AnalyticsTab.tsx` | P2-4: index-based `rowKey` → natural key |
| `frontend/src/dicomweb/DicomWebAdmin.tsx` | P2-4: `valueStyle` → `styles.content` |

## Verification

| Gate | Result |
|------|--------|
| `pytest` (backend full) | ✅ 1671 passed, 4 xfailed |
| `ruff check` (changed files) | ✅ clean |
| `tsc --noEmit` | ✅ clean |
| `npm run build` | ✅ built in 9.8s |
| Alembic migration 060 | ✅ applied live; backend healthy after restart |
| Live smoke (curl as `test.super_admin`) | ✅ `/admin/status`, maintenance toggle (enter/exit), config GET/PUT, backups create/list/restore/delete, prefs GET/PUT, `/roles/{id}/users` 200 |
| Maintenance write-gate | ✅ verified: 503 on write endpoints while active, 200 on reads/login |
| P2-5 role membership | ✅ was 500 → now 200 with `status` |

## Deviations from design

1. **P2-5 (role membership) — fix, not new feature.** The design assumed the
   modal was missing; live verification showed it exists but the API 500'd
   (`users.active` column never existed). Fixed the query + frontend render
   instead of building a new surface. No spec change needed.
2. **Backups are metadata-only.** The implementation records backup jobs and
   manifests in `backups` (initiated/queued via the admin API) rather than
   executing real pg_dump/restore — actual snapshot/restore of Postgres remains
   an infra concern (see hand-off acceptance criteria, which scoped to the
   management surface + audit trail).
3. **Maintenance state is persisted + cached in memory.** Boot loads from
   `platform_state`; the gate reads a fast in-process cache (avoids a DB hit
   per request). Multi-instance sync is future work (single-instance dev deploy).
4. **Notification prefs apply only to role/user fan-out** (`notify_user` /
   `notify_role`); direct user-targeted system notices still deliver — matching
   the design's intent that ops alerts (quota, system) default ON for admins.

## Follow-up items filed (not in this scope)

- Real backup/restore engine (pg_dump integration) — infra decision needed.
- Multi-instance maintenance-state sync via LISTEN/NOTIFY.
