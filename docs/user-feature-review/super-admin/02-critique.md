# 02 — Super Admin Experience Critique

Worn hat: **test.super_admin**. Every finding is what the platform admin experiences — what they can do, what they expect and cannot do, and where the UI fights them. Rated on Discoverability / Efficiency / Feedback / Consistency / Trust / Accessibility (WCAG 2.1 AA).

## What works well (the platform admin experience today)

- **The dashboard is the right home.** Landing on `/admin` with a live health strip, KPIs, charts and per-permission panels is exactly what an ops role wants. The auto-refresh toggle + "Updated" timestamp solve staleness honestly.
- **Role-scope discipline is excellent.** All 8 clinical/front-desk/portal routes bounce an admin-scoped role to `/admin`, and the sidebar hides those sections entirely. super_admin holds *every* permission, yet the app deliberately walls off clinical surfaces — the strongest trust signal in the whole console.
- **Destructive actions are confirmed everywhere**: tenant Suspend/Quarantine/Decommission (Popconfirm), service-key Revoke (Popconfirm), role deletion blocked for built-ins. Immutability tiers (R2-16) are surfaced with real tooltips on the Roles page.
- **Audit is a first-class citizen**: 2,280 events, groupable event-type chips, tenant/actor/date filters, live tail with row highlight, expandable JSON payloads.
- **One-time secrets are handled responsibly**: service-key generation shows the raw key once with a copy button and "This key will not be shown again."
- **Interfaces each get an honest home**: DICOMweb (Endpoints/Search Parameters/Modalities/Metrics/Requests/**Missing Features**), FHIR (config + monitoring + capability docs with "Try It"), HL7 (Messages/Analytics/Configuration), Integrations (webhooks + OAuth providers).

## Findings (severity-rated)

### Critical — none
Every reachable surface loads without errors; no task is fully blocked. (Note: this review walks the *admin console*; the maintenance/backup gaps below are complete-absence gaps, not broken flows.)

### High

**H1 — No maintenance-mode control, though the audit already knows the event.**
The audit catalog (frontend/src/logs/Logs.tsx) lists `system.maintenance_mode`, but there is no UI, endpoint, or gate anywhere to enter maintenance. When the platform admin upgrades the system, they have no supported way to stop writes first or tell users why things are failing. *Trust/Efficiency: an ops role's core pre-upgrade task is impossible in-app.* (Hypothetical Flow 1)

**H2 — No backup/restore management, though the audit already knows the events.**
`system.backup_completed` / `system.backup_failed` are catalogued but never emitted — no backup service, no UI, no restore path. For a medical archive, an admin with no backup visibility is a compliance/DR gap, not a UX nicety. (Hypothetical Flow 2)

### Medium

**M1 — The notification bell floods the platform admin with clinical noise.**
49 unread `study.arrived` notifications ("Study arrived for E2E^MOBILE", file-upload confirmations) crowd out the operational signals that are actually aimed at this role (e.g. `storage.quota_breach` fans out to super_admin via backend/api/files.py `_notify_quota_breach`). There is no preference to mute event types. *Discoverability/Trust: the one signal worth seeing (quota breach) is buried under upload receipts.* (Hypothetical Flow 4)

**M2 — Audit CSV export silently exports only the current page.**
`exportCsv` (Logs.tsx) serializes `data` — the 50 rows on screen. Filtering 2,280 events down to an investigation set and clicking CSV quietly produces a 50-row file, a data-completeness trap for compliance work. (Hypothetical Flow 5)

**M3 — Audit event-type filter catalog drifts from what the backend emits.**
The chip catalog omits whole families the backend writes: `auth.login_success` (users.py Login), `user.role_changed`, `role.created/updated/deleted`, `tenant.provisioned`, `billing.*`, `qa.*`, `exam.*`, `routing.*`, `report.*`, `peer_review.*`, `equipment.*`. Meanwhile the `auth.login` chip may match nothing (backend emits `auth.login_success`). A platform admin filtering "who changed roles" cannot — the chips aren't there. *Consistency: the filter UI contradicts the audit store.* (Hypothetical Flow 5)

**M4 — Platform configuration is YAML-and-SSH only.**
`system.config_changed` is catalogued but there is no way to view or change settings in-app; every tuning action (token expiry, retention, upload caps) requires editing `config.local.yaml` and restarting. (Hypothetical Flow 3)

**M5 — Console noise hides real errors: a React `key` warning in a table `tbody` plus antd v6 deprecations.**
The walkthrough logged `Each child in a list should have a unique "key" prop … Check the render method of tbody` (a table render) plus `Statistic valueStyle` and `Table rowKey index` deprecation warnings on the DICOMweb/metrics pages. The deprecations break on the next antd bump; the duplicate-key warning can corrupt row state silently. *Accessibility/maintainability: console hygiene for a monitoring-heavy role.*

### Low

**L1 — Sidebar notification item concatenates the unread count into the label ("49Notifications").**
The badge count joins the menu item's accessible name; a screen reader announces "49 Notifications" as one run-on token. Cosmetic, but a 20-second fix for a WCAG-AA surface.

**L2 — DICOMweb STOW validates only by file extension client-side.**
`StowUpload.tsx` filters on `/\.dcm$/i` with a warning, so a garbage file named `x.dcm` passes the client and only fails server-side (`message.error(e.message)`). Acceptable for an ops tool; worth a client-side magic-byte check.

**L3 — DICOMweb "Missing Features" tab surfaces the roadmap as a plain one-column table.**
Honest and useful, but a raw list with no severity/version context; an admin can't tell "planned" from "never". Minor polish.

**L4 — Per-tenant usage has no history.**
Tenants page shows a point-in-time number and quota percentage; there is no trend, so "is usage accelerating?" is unanswerable. (Hypothetical Flow 6 — folded here as Low severity polish.)

## Dimension summary

| Dimension | Verdict |
|-----------|---------|
| Discoverability | Strong — sections map 1:1 to ops jobs; gaps are *absent* features (maintenance, backups, config), not hidden ones |
| Efficiency | Good — dashboard quick-links, filters everywhere; CSV page-scope + missing membership drill-down cost extra steps |
| Feedback | Good — loading/error/empty states via PageState, success/error messages; maintenance-mode absence means no feedback at all for that flow |
| Consistency | Mostly strong (PageHeader, Popconfirm, RequirePermission); audit chip catalog drift (M3) is the outlier |
| Trust | Very strong — immutability tiers, destructive-action confirmations, honest health/usage numbers, tenant scoping; notification noise (M1) and no DR visibility (H2) are the weak spots |
| Accessibility | Adequate — labeled buttons/inputs, keyboard nav works; L1 (badge-in-label) and M5 (console/deprecation hygiene) are the actionable items |
