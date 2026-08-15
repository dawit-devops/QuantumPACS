# 04 — Design Proposal (tenant_admin)

**Skill:** ui-ux-pro-max (product: healthcare/PACS internal ops console; stack:
React 19 + Ant Design v6 + Vite)
**Input:** `03-handoff.md` (2× P1, 5× P2)

---

## Design system baseline

ui-ux-pro-max recommends for an internal ops console: dense dashboard density,
calm cyan palette, subtle motion, AA contrast, and a **no-dead-ends** rule for
interactive controls. The recommended palette is the **exact QuantumPACS token
system already in place** (`--color-primary: #0891B2`, cyan + health-green), so
**no token changes are needed** — consistent with the super_admin review.

Rejected as conflicts (documented at the end): dark-mode-only OLED theme, Fira
Code/Fira Sans font swap, glow effects, and the "landing page hero" pattern —
the tenant console is a dense clinical ops tool that must match the existing
Ant Design language.

---

## Design decisions per hand-off item

### P1-1 — No dead "Open" buttons on the dashboard

**Pattern:** permission-aware status list (mirror Metrics' `HealthRow`).

- `HealthStrip` pills and the Interfaces panel rows resolve the target route's
  permission; when the current user lacks it, the row renders **status-only**
  (dot + name + latency + Tag) with **no button and no "Open" aria-label**.
- When permitted (`/replicas` for tenant_admin), the pill/button renders exactly
  as today — no visual regression for super_admin.
- Add a one-line `Tooltip` on status-only rows ("View requires INTERFACE admin
  access") only when a target exists but is gated — discoverability without a
  dead click.
- **States:** loading (existing skeleton), empty ("No interface status
  reported"), permitted (link), gated (status-only + tooltip).
- **A11y:** no false "Open" announcement; keyboard focus never lands on a dead
  control.

### P1-2 — Honest grants: grant the surfaces (recommended direction)

**Pattern:** reconcile grants ↔ gates, keep the permission list truthful.

- **Direction (a) — grant:** `MATRIX_C_TENANT_ADMIN` gains `HL7_READ`,
  `ROUTING_READ`, `DICOMWEB_READ` (the interface surfaces a facility operator
  manages). Sidebar items Routing, HL7, DICOMweb then appear for tenant_admin;
  FHIR stays SYSTEM_ADMIN-only (platform FHIR server policy).
- **Trim:** `METERING_READ`, `BILLING_READ`, `CDS_ADMIN`, `REPORT_TEMPLATE_ADMIN`
  stay as **documented roadmap-only grants** (they are genuinely future
  surfaces); the Account page groups and annotates them ("coming soon") instead
  of listing them as live capabilities. `INTERFACE_ADMIN`/`INTERFACE_MONITOR`/
  `STORAGE_ADMIN` become meaningful again because the surfaces they name are now
  reachable.
- **Account page permission display** becomes grouped + annotated (Matrix C
  groups: Tenant ops / Users & roles / Interfaces / Read-only clinical /
  Roadmap), replacing the raw comma-joined dump (C9).
- **RBAC matrix doc + `test_rbac_matrix.py`** updated per hand-off AC 3–4.

### P2-1 — Real tenant card counts

**Pattern:** data-grounded card (empty/loading/data states).

- Enrich `GET /api/v2/tenants` with `user_count` / `study_count` / `last_activity`
  (single-tenant case is one cheap aggregate; keep `get_stats()` as the deep
  source).
- Card renders `N users` / `N studies` with a subtle loading shimmer while
  fetching; `last_activity` line renders only when present.
- **No "?" ever renders** (hand-off AC 4). Storage bar unchanged.

### P2-2 — Tenant-scoped user directory

**Pattern:** scoped list + visible filter (Consistency with the tenants page,
which already scopes).

- Users page gains a **tenant column** (Tag per row) and a **tenant Select
  filter** (defaults to the user's own tenant for tenant-scoped admins; empty =
  all for super_admin).
- Backend: `GET /api/v2/users` scopes to own tenant for tenant-scoped admins
  (mirror the `api/tenants.py` slug filter) — cross-tenant rows become
  impossible rather than merely labeled.
- Filter UI reuses the existing antd `Select` pattern from the Reading worklist
  filters (aria-labels included, per the resident-review precedent).

### P2-3 — Role immutability shown before the 403

**Pattern:** pre-emptive disabled state (ui-ux-pro-max "Disabled States" rule).

- Roles table rows render a small lock `Tag`/`Tooltip` for tiers the user cannot
  modify (`IMMUTABLE_ROLE_SLUGS`, `PLATFORM_ADMIN_ONLY_MODIFIABLE_ROLES`),
  with the reason ("Platform role — super admin only").
- Edit/Delete affordances **disabled** (opacity + `cursor-not-allowed`) for those
  rows — never an invitation to a 403.
- super_admin sees no change (all tiers editable as today).

### P2-4 — Notification role-defaults for admin roles

**Pattern:** role-based defaults (extend the P1-1 super_admin precedent).

- `default_enabled()` mutes clinical event types for all admin-scoped roles
  (`super_admin`, `tenant_admin`, `pacs_admin`, `emr_admin`).
- Prefs page copy on `/account/notifications` reflects "muted by default for
  admin accounts"; no UI change beyond copy.

### P2-5 — Search-degraded state on Files

**Pattern:** honest empty state (ui-ux-pro-max "No Results" rule).

- When the search backend is down, the Files page shows a distinguishable
  `Alert` banner ("Search is unavailable — archive contents are not listed
  right now") above the empty table, instead of the bare "No files uploaded".
- Upload stays enabled (FILE_WRITE path untouched).

---

## Component map (all existing Ant Design primitives)

| Item | Component | States |
|------|-----------|--------|
| P1-1 status rows | `Tag` + `Tooltip` + existing pill/button | loading / empty / permitted / gated |
| P2-1 card counts | `Statistic`-style inline text + `Skeleton` shimmer | loading / data |
| P2-2 tenant filter | `Select` (aria-label) + `Tag` column | empty / filtering |
| P2-3 immutability | `Tooltip` + disabled `Button` + `LockOutlined` | editable / locked |
| P2-4 defaults | copy-only change on existing `Switch` page | — |
| P2-5 degraded | `Alert` (warning, banner) | search up / search down |

## Conflicts with existing patterns

1. **Dark-mode-only OLED** — rejected: QuantumPACS is light-mode-first with a
   working dark theme; forcing dark would fight the existing clinical language.
2. **Font swap (Fira)** — rejected: the app uses Inter/system stack; a mono/data
   font would break consistency across clinical pages.
3. **Landing-page hero / big CTA** — rejected: this is an authenticated ops
   console, not a marketing surface; the Operations Dashboard pattern stays.
4. **Grant direction (P1-2a)** widens tenant_admin's reachable surfaces — must be
   confirmed as intended policy (facility operators manage their own interfaces),
   and the RBAC matrix is the source of truth if product disagrees (fall back to
   trim direction 1-2b, which is UI-invisible).
