# 02 — Critique: the tenant_admin experience

Rate each finding on **Discoverability / Efficiency / Feedback / Consistency /
Trust / Accessibility**, severity **Critical / High / Medium / Low**.

## High

### C1 — Dashboard "Open" buttons and health pills are permission dead-ends
The Interfaces panel (gated `INTERFACE_MONITOR`, which tenant_admin holds) renders
"Open" buttons that navigate to `/dicomweb`, `/hl7`, `/fhir/monitoring` — all gated
behind `DICOMWEB_READ` / `HL7_READ` / `SYSTEM_ADMIN`, which tenant_admin does **not**
hold. The HealthStrip pills do the same for DICOM Listener/HL7/FHIR. Verified live:
3/3 interface "Open" clicks and 3/4 health-pill clicks **bounce straight back to
`/admin`** with zero feedback (only "Open Storage dashboard" → `/replicas` works).

- **Discoverability:** High — the buttons invite the click.
- **Efficiency:** n/a — the task (view interface) is impossible.
- **Feedback:** **None.** Click → same page, no toast, no error. Feels broken.
- **Consistency:** The Metrics page's `HealthRow` already guards links by permission
  (`hasPermission(area.permission)` renders a plain row instead of a link); the
  AdminDashboard did not get the same guard.
- **Trust:** Low — a control that silently does nothing erodes confidence.
- **Severity:** High (the dashboard is the landing page; every tenant_admin sees
  these dead buttons on every login).

### C2 — Dead grants: INTERFACE_ADMIN / INTERFACE_MONITOR / STORAGE_ADMIN / METERING_READ / BILLING_READ / CDS_ADMIN / REPORT_TEMPLATE_ADMIN
7 of 32 grants unlock **no reachable UI**. A tenant admin — the person who operates
the facility's PACS — cannot open HL7, the DICOMweb console, routing rules, metering,
billing, CDS, or report templates. The sidebar comments even document the mismatch
("INTERFACE_ADMIN was dropped from the gate: tenant_admin and emr_admin hold it but
the route and backend both reject them"). Either the grants are aspirational or the
gates are wrong; today the role's own permission list is a fiction.

- **Trust:** Medium — the Account page shows all 32 permissions as if they mean something.
- **Severity:** High (whole capability classes are unreachable for the role they were named for).

## Medium

### C3 — Tenant cards always render "? users / ? studies"
The tenants list API omits `user_count`/`study_count`/`last_activity`, and the Tenants
page never calls the existing `GET /tenants/{id}/stats` endpoint (the `TenantStats`
type is defined but unused). Verified: every visit shows `?` for both counts.

- **Trust:** Low — the card claims it doesn't know the tenant's own numbers.
- **Severity:** Medium (a core metric is permanently missing on the primary surface).

### C4 — Users directory is not tenant-scoped and has no tenant column/filter
`GET /api/v2/users` returns every user in the platform; the page renders no tenant
column and no filter. Meanwhile the tenants list **is** scoped to own tenant
(`api/tenants.py` filters by slug). Asymmetric scoping: a tenant admin sees other
facilities' accounts with no indicator, while the Tenants page hides other tenants.

- **Trust:** Medium — cross-tenant user exposure without a marker is a privacy concern.
- **Severity:** Medium (data-scope inconsistency + missing filter).

### C5 — Role mutation capability is misleading on the Roles page
tenant_admin holds ROLE_WRITE/ROLE_DELETE, and the Roles page lets them edit roles —
but built-in roles are tiered (immutable anchors, platform-only teleradiologist).
The UI shows edit affordances and only surfaces the 403 on save. No upfront
"immutable" hint on rows the user can never change.

- **Feedback:** Medium — errors arrive only after attempting the action.
- **Severity:** Medium.

## Low

### C6 — Files page "No files uploaded" while the dashboard shows 20 files / 9.4 MB
Environmental in this dev env (search is ES-backed and ES is down), but the page
gives no hint that search is degraded — a tenant admin would believe the archive is
empty. A "search unavailable" notice would prevent that misread.

### C7 — Notification prefs default: clinical receipts ON for tenant_admin
The P1-1 prefs surface exists and is reachable, but `default_enabled()` mutes
clinical types only for `super_admin`. A fresh tenant admin's bell will accumulate
`study.arrived` receipts until they manually opt out.

### C8 — Usage drawer is a thin date+count table
METERING_READ unlocks only that; no trends, no quota projection, no charts.

### C9 — Account page dumps the raw permission list
32 comma-joined permission tokens with no grouping or explanation — developer output,
not user-facing.

## Accessibility summary
No axe violations were flagged on the walked surfaces in this review's probes
(no console errors on any page). Dead-end buttons (C1) are the biggest a11y-adjacent
issue: they announce as actionable but do nothing.

## Severity tally
**Critical 0 · High 2 · Medium 3 · Low 4**
