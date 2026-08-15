# Technical Design — user-feature-review/tenant_admin (Phase 3)

Source: `docs/user-feature-review/tenant-admin/03-handoff.md` + `04-design.md`.
Branch: `phase/user-feature-review-tenant-admin`.

## Scope

- **P1-1** Dashboard dead "Open" buttons → permission-guard HealthStrip pills +
  Interfaces panel rows (mirror Metrics `HealthRow`).
- **P1-2** Grant reconciliation: add `HL7_READ`, `ROUTING_READ`, `DICOMWEB_READ`
  to `MATRIX_C_TENANT_ADMIN`; annotate roadmap-only grants in the Account page
  (grouped permission display). RBAC matrix doc + test updated.
- **P2-1** Tenants page cards show real `user_count`/`study_count`/`last_activity`.
- **P2-2** Users directory tenant column + filter; backend scoping for
  tenant-scoped admins.
- **P2-3** Roles page lock hints for immutable/platform-only tiers.
- **P2-4** Notification role-defaults mute clinical types for admin-scoped roles.
- **P2-5** Files page shows a search-degraded Alert when ES is unavailable.

## Backend changes

### 1. Grants (P1-2) — `backend/api/permissions.py`
```python
MATRIX_C_TENANT_ADMIN = {
    ...,
    # P1-2: facility operators manage their own interfaces (review finding C2).
    'HL7_READ', 'ROUTING_READ', 'DICOMWEB_READ',
}
```
- `test_rbac_matrix.py`: assert the three grants present; assert no roadmap-only
  grant list expansion beyond documented set (METERING_READ, BILLING_READ,
  CDS_ADMIN, REPORT_TEMPLATE_ADMIN stay as roadmap-only, already in role — mark
  them in the doc).
- `docs/reaserch/RBAC_matrix_spec.md`: add HL7_READ / ROUTING_READ / DICOMWEB_READ
  to the tenant_admin row.

### 2. Tenants list counts (P2-1) — `backend/api/tenants.py`
`TenantsHandler.get`: after scoping, enrich each visible tenant with
`Tenants(None).get_stats(slug, pool_info, ...)` — reuse the same pool_info
construction as `TenantStatsHandler` (extract a helper). Single-tenant case = one
pool open; acceptable. Return `user_count`, `study_count`, `file_count`,
`last_activity` merged into each tenant dict.

### 3. Users scoping (P2-2) — `backend/api/users.py` + `db/users.py`
- `db/users.py` `get_users`/`count_users` gain an optional `tenant` filter
  (`WHERE tenant = $n`).
- `UsersHandler.get`: when the requester is tenant-scoped (not `user.admin` and
  `user.tenant` set), pass `tenant=user.tenant`; platform admins see all.
- No change to user create (tenant already accepted via body).

### 4. Notification defaults (P2-4) — `backend/db/notification_prefs.py`
`default_enabled(role_slug, event_type)`: mute clinical types when the role is
admin-scoped. Import `ADMIN_SCOPED_ROLES` is frontend-only; use a local set here
(super_admin, tenant_admin, pacs_admin, emr_admin) to avoid a backend→frontend dep.
- `test_notification_prefs.py`: assert tenant_admin clinical defaults OFF, ops ON.

### 5. Search-degraded signal (P2-5) — `backend/es/es.py` + `backend/api/files.py`
- `es.py`: expose `def available() -> bool: return get_client() is not None`.
- `FilesHandler.post` (search): return `{'data': [], 'total': 0, 'search_available': False}`
  when ES is down (instead of `es.search` returning the empty dict shape).
- Frontend Files.tsx reads `search_available` and shows the Alert.

## Frontend changes

### 6. Dashboard permission guard (P1-1) — `frontend/src/dashboard/AdminDashboard.tsx`
- `HealthStrip`: for each component with a target link, render the pill as a
  button only when `hasPermission(ROUTE_PERMISSION[name])`; else status-only span
  + Tooltip "View requires {label} access". Define a route→permission map:
  `storage: REPLICA_READ`, `dicom_listener: DICOMWEB_READ`, `hl7: HL7_READ`,
  `fhir: SYSTEM_ADMIN`.
- Interfaces panel: same guard on the "Open" buttons.
- No visual change for super_admin (holds all).

### 7. Account permission grouping (P1-2) — `frontend/src/account/*`
- Group the raw permission list into Matrix-C families (Tenant ops / Users &
  roles / Interfaces / Read-only clinical / Roadmap), roadmap annotated
  "coming soon". Keep the raw list behind an expandable `<details>`.

### 8. Tenant cards (P2-1) — `frontend/src/tenants/Tenants.tsx`
- Cards consume `tenant.user_count` / `tenant.study_count` / `tenant.last_activity`
  from the enriched list (already typed in `frontend/src/api/tenants.ts`); remove
  the "?" fallbacks — render "—" only while loading.

### 9. Users tenant column + filter (P2-2) — `frontend/src/users/Users.tsx`
- Add a Tenant column (Tag) and a tenant Select filter fed from the tenants list
  (or a `tenants` query param). Default filter = own tenant for tenant-scoped
  admins (backend returns only own tenant anyway).

### 10. Roles lock hints (P2-3) — `frontend/src/roles/Roles.tsx`
- Backend: `GET /api/roles` already returns `built_in`; add a `modifiable` field
  per role (`built_in` && slug in IMMUTABLE ∪ PLATFORM_ADMIN_ONLY, and not
  platform admin → False). Frontend renders a Lock tooltip + disabled Edit/Delete
  when `modifiable === false`.

### 11. Prefs copy (P2-4) — `frontend/src/notifications/NotificationPreferences.tsx`
- Copy tweak: "muted by default for admin accounts" when the user's role is
  admin-scoped.

### 12. Files degraded Alert (P2-5) — `frontend/src/files/Files.tsx`
- Track `searchAvailable` from the search response; render a warning `Alert`
  when false; hide the bare "No files uploaded" empty message in favor of the
  degraded notice.

## Tests
- Backend: `test_rbac_matrix.py` (grants), `test_tenants_api.py` (list counts),
  `test_users*.py` (tenant filter), `test_notification_prefs.py` (admin defaults),
  `test_files_api.py` (degraded search shape).
- Frontend: `tsc`, `npm run build`; e2e spec `super-admin`-style
  `tenant-admin.spec.ts` covering dashboard dead-end removal, tenant counts,
  users tenant filter.

## Security checkpoint
- New `GET /tenants` enrichment stays behind the existing TENANT_READ/CROSS_TENANT_READ
  gate + own-tenant scoping (no new exposure; counts are already exposed via
  `/tenants/{id}/stats` for owners).
- Users tenant filter is read-scoping only — no new write surface; platform
  admins unaffected.
- No new endpoints; no schema changes → **no Alembic migration needed**.
- Frontend guards are UX-only; backend gates remain authoritative (DICOMWEB_READ
  etc. now genuinely held by tenant_admin after P1-2).
