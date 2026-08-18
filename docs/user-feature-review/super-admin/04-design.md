# 04 — Design Proposal (ui-ux-pro-max) — super_admin hand-off

Inputs: `03-handoff.md` (source of truth), `01-hypothetical-flows.md` (context). Stack detected from `frontend/package.json`: **React 19 + Ant Design v6 + Vite** (chart.js/react-chartjs-2 already present).

## Design system baseline

ui-ux-pro-max `--design-system` (product: "healthcare PACS internal operations admin console"; density 8/10 dashboard, variance 4/10 balanced, motion 2/10 subtle) recommends:

- **Pattern**: Real-Time / Operations Landing — status first, key metrics, drill-downs. The current dashboard already follows this.
- **Colors**: Primary `#0891B2`, Secondary `#22D3EE`, Accent `#059669`, Background `#ECFEFF`, Foreground `#164E63`, Destructive `#DC2626`. **This is already the QuantumPACS token set** (`--color-primary: #0891B2` is read by AdminDashboard.tsx) — no token changes needed. 
- **Typography**: Fira Sans / Fira Code (data/technical mood).
- **Motion**: subtle (150–300ms, `prefers-reduced-motion` respected), no decorative animation.
- **Avoid**: slow updates + no automation — i.e. the ops console must surface status and refresh honestly (already true: "Updated" timestamps + auto-refresh toggles).

**Adopted from the search:** dense dashboard density (8–32px spacing), subtle motion only, AA contrast, distinct line styles (not color alone) for multi-series charts, confirmations for every destructive action, loading indicators > 300ms, visible labels (never placeholder-only).

**Not adopted (conflicts, see §Conflicts):** Fira font swap, gradient buttons, spring/haptic effects, glassmorphism nav.

## Item → design decision map

### P1-1 — Notification relevance (mute clinical noise, keep ops alerts)

**Surface: bell drawer + new "Notification Preferences" page** (`/account/notifications`, listed under Account; also a "Manage preferences" link in the bell drawer footer — the drawer stays the fast path, the page carries the full control).

- Bell drawer (unchanged look): keep Read all / Dismiss all; add a muted footer link **Manage notification preferences** → the page. A small `Tag` in the drawer header shows "Showing 3 of 9 event types" when prefs filter.
- Preferences page layout (antd `Card` + grouped `Switch` list, mirroring the Service Keys permission-group pattern):
  - **Operational** (default ON for super_admin): `storage.quota_breach`, `quota.warning`, `system.alert`, `storage.quota_breach` fan-out.
  - **Clinical** (default OFF for super_admin): `study.arrived`, `report.ready`, `worklist.performed`, `share.accessed`, `annotation.shared`.
  - **System** (default ON): `interface.down`, `failed_store`.
- Each row: label + humanized description + `Switch` with `loading` state while saving; group headers with "all on/off" affordance.
- States: skeleton while loading (PageState), per-toggle optimistic update with rollback + `message.error` on failure, success `message.success` ("Preferences saved"), **Reset to role defaults** secondary button with `Popconfirm`.
- Server-side enforcement (fan-out skip), per-user persistence, audit `user.notification_prefs_changed` — design doesn't change these; the page is the UI for the API.

### P1-2 — Maintenance mode

**Surface: new Admin item "Maintenance"** (`/admin/maintenance`, gated `SYSTEM_ADMIN`, icon `ToolOutlined`) + **global banner**.

- Page (PageHeader "Maintenance Mode" + PageState):
  - Status card reusing the dashboard health-dot language: a pulsing cyan dot + "Platform online" / orange dot + "Maintenance active" (`Tag` + `Typography`), plus "since <time>" and the recorded reason.
  - **Enter maintenance** primary button (`danger`-tinted outline) → `Modal` with a `Form`: required *Reason* (TextArea), optional *Expected duration* (`DatePicker`/`InputNumber` hours), and a typed-confirmation note ("This blocks all clinical writes platform-wide"). `okText="Enter maintenance"`, loading on submit, `Popconfirm`-style guard is redundant — the typed reason IS the guard.
  - While active: **Exit maintenance** button (primary) with `Popconfirm` ("Resume clinical operations?").
  - Activity log: last 5 `system.maintenance_mode` events from the audit API (time, actor, reason, on/off) as a compact Table.
- Global banner while active: antd `Alert type="warning" banner showIcon` with "System is in maintenance — writes are paused" + optional reason, rendered in the app shell (above `<Routes>`), visible to all roles; also on `/login`.
- Write-gate feedback: endpoints returning 503 "maintenance" surface the existing error toast; the banner explains why.

### P2-1 — Backup & restore

**Surface: new Admin item "Backups"** (`/admin/backups`, gated `SYSTEM_ADMIN`, icon `CloudUploadOutlined`).

- Header: **Back up now** primary button (`loading` while running) + **Schedule** secondary button opening a `Modal` `Form` (frequency `Select` daily/weekly, retention `InputNumber` days).
- Table of backups (pattern: Replicas/Service Keys tables): Time, Size, Status `Tag` (green **Completed** / red **Failed** / orange **Running**), Age, Actions — **Restore** (opens Modal: scope summary + `Popconfirm` "Restore patient data from this backup?") and **Delete** (`Popconfirm`).
- PageState empty state: "No backups yet — run your first backup" with a primary action (same empty-state pattern as Replicas "Add replica").
- Status panel: last backup time + age + a "stale backup" orange `Alert` when the newest backup is older than the configured schedule window.
- Audit wiring `system.backup_completed/failed` is backend work; UI reads the same events for the activity column.

### P2-2 — Full-result audit export + event-type catalog sync

**Surface: Logs page (existing) — export + chip catalog only, no new route.**

- Replace the client-side CSV button with **Export all N** (`DownloadOutlined`): server-side streaming CSV (`GET /api/logs?download=csv` with the active filters). Button shows the exact count from the filters ("Export all 342 events"); disabled at 0; `loading` while generating; success toast on download; **no silent page-scope export** (fixes M2).
- Keep the current chip-row layout and colors; **extend the catalog** with the missing families (auth.login_success, user.role_changed, role.*, tenant.provisioned, billing.*, qa.*, exam.*, routing.*, report.*, peer_review.*, equipment.*) using the existing grouped `Tag` chips; remove the stale `auth.login` chip or alias it server-side to `auth.login_success` (mirror the LOG_READ/AUDIT_READ alias pattern).
- The expandable JSON-payload row and Live tail stay exactly as-is.

### P2-3 — Platform configuration page

**Surface: new Admin item "Settings"** (`/admin/settings`, gated `SYSTEM_ADMIN`, icon `SettingOutlined`).

- PageHeader + grouped `Card` forms (pattern: FHIR config page, which already has Save/Test Connection):
  - **Auth & Sessions**: token expiry days (`InputNumber`), refresh lifetime.
  - **Storage & Upload**: max upload MB, max STOW MB, retention days.
  - **DICOM**: AE title, C-STORE port, MWL port (read-only `Descriptions` for listener-bound keys with a "restart required" `Tag`).
  - **Interfaces**: CORS origins, allowed hosts (validated textarea).
- Every editable field is a `Form.Item` with `rules`; **Save** per group (loading → success toast), disabled until dirty; values fetched from a whitelist `GET /api/admin/config` (no secrets ever rendered).
- "Restart required" `Tag` per key that needs a process restart; a footnote "Changes are audited as `system.config_changed`."

### P2-4 — Console hygiene

- Fix the React `key` warning in the table `tbody` (find the duplicate/undefined rowKey — likely Files/metrics "Latest Files" or DICOMweb request tables) by giving every row a stable unique `key`.
- Migrate `Statistic valueStyle` → `styles.content` (DICOMweb metrics tab, Metrics page) per the antd v6 deprecation message.
- Stop passing `index` to `rowKey` (use a stable field).
- No visual changes; verified by a clean console walk of the Admin section.

### P2-5 — Role membership drill-down

**Surface: Roles page (existing) — new per-row action "Users".**

- Each role row gains a **Users** link (next to Edit) opening a `Modal` with a membership Table (username, status `Tag`, created date) backed by the existing `GET /api/roles/{id}/users` (`listRoleUsers` is already in frontend/src/api/roles.ts).
- Footer action **View audit for this role** → navigates to `/logs` with the role filter pre-applied (requires P2-2's role.* chips).
- Empty membership state: "No users hold this role."

### P2-6 — Sidebar badge/label split

- Notification menu item gets `aria-label`/text split: count rendered as a visually-hidden separate text or `Badge` offset outside the accessible name — screen reader hears "Notifications, 49 unread" instead of the concatenated "49Notifications". Zero visual change.

## Shared interaction & accessibility conformance (all items)

- **Loading**: skeleton/`Spin` for ops > 300ms (PageState pattern).
- **Feedback**: success `message`, error `message` with retry; no silent actions.
- **Destructive**: `Popconfirm` or typed-confirmation Modal for maintenance enter, restore, delete, decommission (existing pattern, kept).
- **Accessibility (WCAG 2.1 AA)**: labeled `Switch`es and inputs (visible labels, never placeholder-only), keyboard reachable, focus rings intact, 4.5:1 contrast, `prefers-reduced-motion` respected for the banner pulse.
- **Responsive**: Admin pages stay desktop-first; tables scroll horizontally inside cards; the global maintenance banner wraps on narrow widths; settings forms stack on ≤768px.

## Conflicts with existing patterns

| Proposed | Existing QuantumPACS pattern | Conflict / resolution |
|----------|------------------------------|-----------------------|
| Fira Sans / Fira Code font swap | Existing font stack in `common/tokens.css` | **Rejected** — font swap would ripple across every page; the design mood (data/technical) is already served by the current stack. |
| Gradient buttons, spring/haptic motion, glassmorphism | Calm clinical Ant Design (flat buttons, subtle hover) | **Rejected** — fights the clinical trust language; adopted only the subtle-motion + status-dot ideas. |
| Notification prefs as a page under Account | Bell drawer + sidebar Admin pages | **Compatible** — the page is a new surface, the drawer keeps its role as the fast path with a footer link; no existing pattern broken. |
| New SYSTEM_ADMIN-gated Admin items (Maintenance/Backups/Settings) | Admin items gated by read permissions | **Compatible** — super_admin is the only SYSTEM_ADMIN holder; the gate mirrors the FHIR/Integrations items which already use SYSTEM_ADMIN. |
| Server-side full-result CSV | Client-side current-page CSV | **Deliberate change** — fixes a data-completeness trap (M2); button labels the scope explicitly so nothing is lost in transition. |
| Chart for tenant usage trend | chart.js/react-chartjs-2 already used on dashboard/metrics | **Compatible** — reuse the same Line/Area chart with line-style differentiation (AA), not color alone. |
