# 03 — Hand-off to the Dev Team (super_admin)

Prioritized improvement list from the Phase 1 review of the platform-admin experience. Every item has a user story, numbered acceptance criteria, affected areas, and priority. Priority reflects both impact on the platform-admin persona and implementation cost.

---

## P0 — none

The admin console has no task-blocking defects. All P1/P2 items below are additions/corrections on a healthy surface.

---

## P1-1 — Notification relevance for the platform admin (mute clinical noise, keep ops alerts)

**User story:** As a super admin, I want my notification bell to surface operational signals (quota breaches, interface failures, failed stores) and not a receipt for every file upload, so that I notice the events only I can act on.

**Acceptance criteria**
1. A notification-preferences surface exists (page or drawer entry under Account/Admin) listing event types with on/off toggles.
2. `study.arrived` upload-receipt notifications are OFF by default for `super_admin` (role-default preference), while `storage.quota_breach`, `quota.warning` and `system.alert` are ON.
3. The bell, unread badge and drawer respect the preferences server-side (fan-out skips muted event types) — not merely hidden client-side.
4. Preferences persist per user and are audited (`user.notification_prefs_changed`).
5. The 49-notification flood scenario (bulk uploads as the admin account) no longer accumulates unread `study.arrived` rows for a super admin.

**Affected areas:** `backend/api/notify.py` + `backend/api/notifications.py` (prefs table/API), `frontend/src/notifications/`, seed role defaults; tests in `backend/tests/test_notifications.py`.

---

## P1-2 — Maintenance mode control (the audit event already exists)

**User story:** As a super admin, I want to put the platform into maintenance mode before an upgrade and take it back out, so that no clinical writes happen mid-migration and users see a clear banner instead of confusing failures.

**Acceptance criteria**
1. A "Maintenance" control exists in the Admin section (toggle + reason + optional duration).
2. `POST /api/admin/maintenance` (on/off) is restricted to `SYSTEM_ADMIN`/admin users and writes the `system.maintenance_mode` audit event with the reason.
3. While ON: write endpoints (file upload, STOW, report save/sign, bookings, role/tenant mutations) return a readable 503 "maintenance" response; reads stay available.
4. Authenticated users see a maintenance banner (in-app + on login) while it is active.
5. Toggling OFF restores writes and clears the banner; the window is visible in the audit trail.

**Affected areas:** new `backend/api/admin.py` (or `config` flag), write-gate in `api/rbac.py`/middleware, `frontend/src/admin/` maintenance page + global banner; audit event wiring to the existing `system.maintenance_mode` catalog entry in `frontend/src/logs/Logs.tsx`.

---

## P2-1 — Backup & restore management (audit events already exist)

**User story:** As a super admin, I want to run, schedule and monitor archive backups and restore from one when needed, so that patient studies are never at risk during a disk failure or migration.

**Acceptance criteria**
1. A "Backups" surface under Admin lists past backups (time, size, status, age) with an "empty state" that says no backups exist yet.
2. "Back up now" triggers an on-demand backup; recurring schedule (daily/weekly, retention count) can be configured.
3. Backup success/failure emits `system.backup_completed` / `system.backup_failed` (already catalogued in Logs.tsx) and surfaces in the UI.
4. Restore is offered per backup and requires an explicit confirmation with the tenant scope it affects.

**Affected areas:** backup service (DB dump + storage snapshot + metadata export), `backend/api/admin_backups.py`, `frontend/src/admin/Backups.tsx`; Alembic migration only if a backup registry table is added.

---

## P2-2 — Full-result audit export + event-type catalog sync

**User story:** As a super admin, I want to export the complete filtered audit result set and filter on every event the backend records, so that compliance investigations are complete and role changes are findable.

**Acceptance criteria**
1. CSV export returns **all** rows matching the active filters (server-side `download=csv` on `GET /api/logs`, or streamed pagination), not the current 50-row page; the UI labels the export scope ("Export all N events").
2. The Logs.tsx chip catalog includes the emitted-but-missing families: `auth.login_success`, `user.role_changed`, `role.created/updated/deleted`, `tenant.provisioned`, `billing.*`, `qa.*`, `exam.*`, `routing.*`, `report.*`, `peer_review.*`, `equipment.*`.
3. The stale `auth.login` chip is either removed or the backend alias resolves it to `auth.login_success` (mirror the LOG_READ/AUDIT_READ alias pattern).
4. A test asserts the UI catalog's event types are a superset of event types the backend can emit (single-source list, e.g. exported from `backend/api/`).

**Affected areas:** `backend/api/logs.py`, `frontend/src/api/logs.ts`, `frontend/src/logs/Logs.tsx`.

---

## P2-3 — Platform configuration page (view + audited change)

**User story:** As a super admin, I want to view and change platform settings from the UI, so that tuning the platform does not require SSH and YAML edits.

**Acceptance criteria**
1. A "System Settings" page under Admin shows effective values for a whitelist: token expiry, log retention, max upload/STOW size, DICOM AE title, allowed origins, interface defaults.
2. Editable settings validate server-side and write `system.config_changed` audit events with old → new values.
3. The page flags which settings need a restart to take effect.
4. Read access is `SYSTEM_ADMIN`/admin-only; write access is admin-only.

**Affected areas:** `backend/api/admin_config.py` (whitelisted keys only, no secrets), `frontend/src/admin/Settings.tsx`; tests for the config gate.

---

## P2-4 — Console hygiene (React key warning + antd v6 deprecations)

**User story:** As a developer reading the admin pages' console, I want a clean console so that real errors are not lost among warnings.

**Acceptance criteria**
1. No "Each child in a list should have a unique key prop" warning in any admin page table (find the `tbody` child render — likely Files/metrics "Latest Files" or DICOMweb request tables — and fix the rowKey/render).
2. No `Statistic valueStyle` deprecation warnings — migrate to `styles.content` (DICOMweb metrics, Metrics page).
3. No `Table rowKey index` deprecation warnings — stop using the `index` parameter of `rowKey`.
4. `tsc` + `npm run build` green after the changes.

**Affected areas:** `frontend/src/dicomweb/DicomWebAdmin.tsx`, `frontend/src/metrics/Metrics.tsx`, `frontend/src/files/Files.tsx` (or wherever the key warning originates).

---

## P2-5 — Role membership drill-down (API already exists)

**User story:** As a super admin, I want to see which users hold a role and how a role's grants changed, so that I can audit privilege creep in-app.

**Acceptance criteria**
1. The Roles page exposes a "Users" action per role opening a membership list (uses the existing `GET /api/roles/{id}/users` — `listRoleUsers` is already in frontend/src/api/roles.ts).
2. `role.*` and `user.role_changed` events are filterable in the audit log (covered by P2-2 AC2) and a role row links to the audit filtered to that role.

**Affected areas:** `frontend/src/roles/Roles.tsx`, `frontend/src/api/roles.ts`.

---

## P2-6 — Sidebar badge/label split (a11y polish)

**User story:** As a screen-reader user, I want the notification count announced as a count, not glued to the label.

**Acceptance criteria**
1. The notification menu item's accessible name reads as "Notifications" with the count as a separate badge (e.g. `aria-label="Notifications, 49 unread"`), not the concatenated "49Notifications".
2. No visual change.

**Affected areas:** `frontend/src/common/Sidebar.tsx` (notification menu item).

---

## Definition of Done (whole hand-off)

- [ ] Backend: `pytest` passes (new tests for prefs fan-out, maintenance gate, backup events, config whitelist, logs CSV).
- [ ] Frontend: `tsc` + `npm run build` pass; `ruff`/prettier clean.
- [ ] No schema change ships without an Alembic migration.
- [ ] Every new mutation is audited (no silent admin actions).
- [ ] Every new endpoint is permission-gated (SYSTEM_ADMIN/admin) and validated with `parse_body()`.
- [ ] `scripts/dev.sh status` healthy; smoke-login as `test.super_admin` walks the Admin section.
- [ ] Console clean (P2-4) across the Admin section.
- [ ] E2E: super-admin spec covers maintenance on→off (P1-2), backup trigger (P2-1), notification prefs toggling (P1-1).
