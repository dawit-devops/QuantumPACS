# 01 — Super Admin Hypothetical Flows (what the platform admin expects but the app cannot do)

Persona: the platform super admin owns the whole QuantumPACS installation — tenants, storage, interfaces, audit, upgrades. The walkthrough shows every *inventory* surface loads and the admin console is rich. These flows are the platform-ops tasks that a super admin will reach for that the app cannot perform today. Each step is marked **exists** (the app does it today) or **missing** (the app has no path).

---

## Flow 1 — Put the platform in maintenance mode before an upgrade

> **User story:** As a super admin, I want to flip the whole platform into maintenance mode before a scheduled upgrade, so that no clinical work can be written mid-migration and users see a clear banner instead of confusing errors.

1. Open the Admin section and find "Maintenance" — **missing** (no entry in sidebar, no route, no control anywhere).
2. Toggle maintenance ON with a reason + expected duration — **missing**.
3. The app blocks write endpoints (uploads, STOW, report signing, bookings) with a readable "system in maintenance" message — **missing** (no such gate exists).
4. Every user sees a maintenance banner on login/session — **missing**.
5. The change is audited — **partial**: the audit catalog already knows `system.maintenance_mode` (frontend/src/logs/Logs.tsx EVENT_GROUPS), but nothing ever emits it because there is no control to trigger it.
6. Toggle maintenance OFF after the window — **missing**.

**Data/API impact:** new `POST /api/admin/maintenance` (on/off + reason), a `system_maintenance` flag read by the auth/middleware layer to gate writes and drive a global banner; audit event `system.maintenance_mode` wired to it.

---

## Flow 2 — Run and manage backups of the archive

> **User story:** As a super admin, I want to trigger and monitor backups of the archive (metadata + storage) and restore from one when disaster strikes, so that a failed disk or botched migration never loses patient studies.

1. Open "Backups" — **missing** (no entry anywhere).
2. Start an on-demand backup / view the last backup + its status and age — **missing**.
3. Schedule recurring backups — **missing**.
4. Restore from a chosen backup (point-in-time) with a confirmation gate — **missing**.
5. Success/failure is audited — **partial**: `system.backup_completed` / `system.backup_failed` exist in the audit catalog (Logs.tsx) but nothing emits them today; there is no backup service or UI.

**Data/API impact:** backup service (DB dump + object-storage snapshot + metadata export), `GET/POST /api/admin/backups`, `POST /api/admin/backups/{id}/restore`; audit events wired.

---

## Flow 3 — View and change platform configuration from the UI

> **User story:** As a super admin, I want to see and change platform settings (token lifetimes, retention, upload limits, interface defaults, DICOM AE titles) in the UI, so that tuning the platform doesn't require SSH + YAML + a restart.

1. Open "System Settings" — **missing** (no route; config lives in `config.local.yaml` + env vars only).
2. See current effective settings with descriptions — **missing**.
3. Change a setting with validation and an audit trail — **missing** (`system.config_changed` is catalogued in Logs.tsx but nothing emits it).
4. Know which settings need a restart vs. apply live — **missing**.

**Data/API impact:** `GET/PUT /api/admin/config` (whitelisted keys only), audit `system.config_changed` with old/new values; frontend page under Admin.

---

## Flow 4 — Subscribe to operational alerts and mute clinical noise

> **User story:** As a super admin, I want my notification bell to carry operational signals (quota breaches, interface failures, failed stores) and not every clinical event, so that I notice the things only I can fix.

1. A quota breach or failed store raises an alert — **partial**: `storage.quota_breach` fans out to all super admins (backend/api/files.py `_notify_quota_breach` → `notify_role('super_admin', …)`); other operational events have no fan-out.
2. Every file upload I make creates a `study.arrived` notification — **exists but wrong**: the walkthrough showed **49 unread study.arrived** in the platform admin's bell (files.py Upload creates `study.arrived` for the uploader; E2E/seeding uploads as the admin account).
3. I can choose which event types reach me (mute `study.arrived`, keep `storage.quota_breach` / `system.alert` / `quota.warning`) — **missing** (no notification preferences UI or API; bell is a flat dump).
4. Alerts carry a link to the affected surface (`/tenants` for quota) — **partial**: quota breach links to `/tenants`; most events link nowhere actionable.

**Data/API impact:** `GET/PUT /api/notifications/preferences` (per-user event-type subscriptions + role defaults); backend respects prefs when fanning out; seed role-default prefs (platform admin: ops events ON, clinical events OFF).

---

## Flow 5 — Investigate an incident from notification → audit → export

> **User story:** As a super admin, I want to jump from an alert/notification straight into the filtered audit trail for that actor/tenant/time window and export the *full* result set for the compliance file, so that an investigation is minutes, not hours.

1. From a notification, open the audit trail pre-filtered — **missing** (notification → audit has no link; audit is only reachable via sidebar).
2. Filter by event type, tenant, actor, date range — **exists** (Logs.tsx chips + range + tenant + actor autocomplete; live tail with row highlight).
3. Inspect a single event's full payload — **exists** (expandable row renders `record.payload` as JSON).
4. Export *all* matching events to CSV for the file — **missing/partial**: CSV exports only the current page (`exportCsv` serializes `data`, max 50 rows) — exporting a 2,280-event filtered investigation silently yields 50 rows.
5. The event-type catalog matches what the backend actually emits — **partial/drift**: backend emits `auth.login_success`, `user.role_changed`, `role.created/updated/deleted`, `tenant.provisioned`, `billing.*`, `qa.*`, `exam.*`, `routing.*`, `report.*` …; the UI filter chips cover only a subset and some chips (`auth.login`) may match nothing.

**Data/API impact:** extend `GET /api/logs` export to stream/return the full filtered set (or `download=csv` server-side); add missing event types to the Logs.tsx catalog; optional `?from_notification=` deep link.

---

## Flow 6 — Oversee tenant usage trends and quota headroom

> **User story:** As a super admin, I want to see each tenant's storage trend and who is approaching their quota, so that I can resize quotas or chase over-usage before a tenant's uploads start failing.

1. See per-tenant current usage — **exists** (Tenants page: 0 B / 500.0 GB @ 0%, Edit Usage, quota-change audited as `tenant.storage_quota_changed`).
2. See usage over time (trend line per tenant) — **missing** (no time series anywhere; METERING_READ exists but no metering UI).
3. Get a "tenants approaching quota" list surfaced on the dashboard — **missing** (only reactive per-upload breach notification).

**Data/API impact:** usage-history table or metrics endpoint per tenant; dashboard panel + Tenants page trend chart.

---

## Flow 7 — Govern role lifecycle end to end

> **User story:** As a super admin, I want to see who holds each role, how a role's permissions changed over time, and compare two role sets, so that I can audit privilege creep without SQL.

1. See the role catalog with permission summaries — **exists** (Roles page, humanized labels, +N more, built-in badges, immutability tiers enforced).
2. See which users hold a role — **missing** (Roles table shows user_count; no membership drill-down despite a `roles/{id}/users` API existing in frontend/src/api/roles.ts `listRoleUsers`).
3. See a role's permission-change history — **missing** (backend audits `role.created/updated/deleted`, but the audit filter catalog has no role.* chips, so they're hard to find).
4. Compare two roles' permission sets side by side — **missing**.

**Data/API impact:** membership panel on the role editor (listRoleUsers exists), role.* chips in Logs.tsx, optional role-diff view.

---

## Summary

| # | Flow | Status | Key blocker |
|---|------|--------|-------------|
| 1 | Maintenance mode | **Missing** (audit event exists, no control) | No backend flag/gate + no UI |
| 2 | Backups / restore | **Missing** (audit events exist, no service) | No backup service + no UI |
| 3 | System configuration UI | **Missing** (audit event exists, no route) | No config API + no UI |
| 4 | Notification preferences / operational alerts | **Missing** (49-item noise confirmed) | No prefs API + role-default fan-out |
| 5 | Incident investigation → full export | **Partial** (rich audit, page-only CSV, catalog drift) | CSV scope + event-type catalog |
| 6 | Tenant usage trends / quota headroom | **Partial** (current usage only) | No time-series metering |
| 7 | Role lifecycle governance | **Partial** (catalog + immutability; no membership/diff) | Membership UI unused; role.* chips absent |
