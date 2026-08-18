# 01 — Hypothetical Flows: what a tenant admin expects but the app lacks

As a tenant admin I run my facility's PACS day-to-day: manage who's in my
tenant, watch my storage/usage, keep integrations healthy, and audit what
happens. These are the flows I expect that the app cannot complete today.

## H1 — Manage my facility's integrations (HL7 / DICOMweb / routing)

**User story:** As a tenant admin, I want to see and manage the HL7, DICOMweb
and routing surfaces for my tenant, so that I can keep my interfaces healthy
without calling the platform super admin for everything.

**Steps:**
1. From the dashboard, click "Open" on the HL7 interface. → **Missing:** bounces back to `/admin` (gate is `HL7_READ`; I hold only `INTERFACE_ADMIN`/`INTERFACE_MONITOR`).
2. Open the DICOMweb console (Server/STOW/Browser). → **Missing:** same bounce (`DICOMWEB_READ` required).
3. Configure routing rules for incoming studies. → **Missing:** same bounce (`ROUTING_READ` required).
4. See interface health without dead-end links. → **Partially exists:** the Interfaces panel renders (INTERFACE_MONITOR) but every "Open" button is a dead end.

**Data/API impact:** grant reconciliation (`INTERFACE_ADMIN`/`INTERFACE_MONITOR` vs `HL7_READ`/`DICOMWEB_READ`/`ROUTING_READ`) or route-gate changes; dashboard link permission-guarding.

## H2 — See my tenant's real numbers on the Tenants page

**User story:** As a tenant admin, I want the tenant card to show how many users and studies my tenant actually has, so that I can gauge activity at a glance.

**Steps:**
1. Open Tenants. → The card renders `? users` and `? studies`. **Missing:** the list API omits `user_count`/`study_count` and the page never fetches the per-tenant stats endpoint.
2. Click Usage. → Drawer opens but shows "No usage data" in dev (metering empty). **Partial.**
3. Check storage. → Storage bar renders from `storage_used_bytes`/`storage_quota_bytes` ✅.

**Data/API impact:** enrich `GET /api/v2/tenants` with counts (or have the card call `GET /tenants/{id}/stats` — endpoint exists, `TenantStats` type exists, UI never calls it).

## H3 — Scope the user directory to my tenant

**User story:** As a tenant admin, I want to see and manage only my tenant's users, so that I don't scroll past other facilities' accounts and don't worry about cross-tenant data exposure.

**Steps:**
1. Open Users. → Lists every user in the platform (other tenants included) with **no tenant column and no tenant filter**. **Missing.**
2. Add a user. → Works, but there's no way to confirm which tenant the user lands in from the UI. **Partial.**

**Data/API impact:** tenant scoping on `GET /api/v2/users` (or a visible tenant filter), mirroring the tenants-list scoping already applied in `api/tenants.py`.

## H4 — Metering / usage trends (I hold METERING_READ but there's no surface)

**User story:** As a tenant admin, I want a usage-over-time view (API calls, storage growth), so that I can plan quota and spot anomalies.

**Steps:**
1. Look for a "Usage"/"Metering" page in the sidebar. → **Missing:** no nav item; METERING_READ unlocks only the tiny per-tenant Usage drawer with date + api_calls.
2. See storage growth over time. → **Missing.**

**Data/API impact:** a `/admin/usage` or tenant-scoped usage page consuming the existing metering tables; sidebar item gated `METERING_READ`.

## H5 — Billing read access (BILLING_READ held, no surface)

**User story:** As a tenant admin, I want to see my tenant's billing/plan information, so that I can answer "what plan are we on / what did we consume".

**Steps:**
1. Look for a Billing page. → **Missing:** no surface consumes `BILLING_READ` (only the tenant card shows `plan: free`).

**Data/API impact:** a tenant-scoped billing/plan summary surface, or at minimum plan/quota info surfaced on the Tenants page.

## H6 — CDS / report-template admin (grants held, no surface)

**User story:** As a tenant admin, I want to manage clinical decision-support hooks and report templates, so that my facility's templates are usable by my radiologists.

**Steps:**
1. Look for a Templates/CDS surface. → **Missing:** `REPORT_TEMPLATE_ADMIN` and `CDS_ADMIN` have no UI anywhere in the admin console.

**Data/API impact:** report-template admin surface (list/edit/version) + CDS hook config; both currently dead grants.

## H7 — Notification preferences for a non-super-admin (P1-1 spillover)

**User story:** As a tenant admin, I want to choose which notifications reach my bell, so that I am not flooded with clinical receipts.

**Steps:**
1. Open the bell → "Manage preferences" → `/account/notifications`. → **Exists** (FILE_READ-gated, reachable).
2. Toggle study.arrived off. → **Exists** — but the **role default is ON** for `tenant_admin` (only `super_admin` mutes clinical types by default), so a fresh tenant admin still gets every upload receipt until they manually opt out. **Partial.**

**Data/API impact:** extend role-default muting to tenant_admin (or any admin-scoped role), or surface a first-run prompt.

## H8 — Decommission / suspend from a tenant card I can act on

**User story:** As a tenant admin, I want to act on lifecycle state of MY tenant only, so that I cannot affect other facilities.

**Steps:**
1. Tenants page lists only my tenant ✅ (scoped).
2. Suspend/Quarantine/Decommission buttons render ✅ and hit TENANT_ADMIN-gated endpoints — but the frontend renders them for any `TENANT_ADMIN` holder without re-checking tenant ownership; the backend does scope-check. **Works, but UI shows no ownership context.** Partial/edge.
