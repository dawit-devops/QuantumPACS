# 03 — Hand-off to the Dev Team (tenant_admin)

Prioritized improvement list from the Phase 1 review of the tenant-admin
experience. Every item has a user story, numbered acceptance criteria, affected
areas, and a priority. Priority reflects impact on the tenant-admin persona and
implementation cost.

---

## P0 — none

No task-blocking defects: all 10 reachable surfaces render without error, all 13
denied surfaces bounce correctly, and the two prior-review fixes that matter
(role-membership modal, notification-prefs surface) work for this role too.

---

## P1-1 — Dashboard "Open" buttons and health pills must never be dead ends

**User story:** As a tenant admin, I want every dashboard control I can see to do
something, so that I never click "Open" on an interface I'm not allowed to view and
silently land back where I started.

**Acceptance criteria**
1. The AdminDashboard Interfaces panel "Open" buttons and the HealthStrip pills are
   rendered **only when the target route's permission passes** (mirror the guard the
   Metrics page `HealthRow` already uses: `hasPermission(area.permission)`), for every
   admin-scoped role.
2. For a role that lacks the target permission (tenant_admin → `/dicomweb`, `/hl7`,
   `/fhir/monitoring`), the row renders as a plain status line — no button, no
   aria-label claiming "Open".
3. "Open Storage dashboard" → `/replicas` keeps working for tenant_admin (REPLICA_READ held).
4. No console error and no dead click remains on `/admin` for `test.tenant_admin`.
5. A test (unit or e2e) asserts the dashboard renders zero "Open" affordances whose
   target route the current role cannot open.

**Affected areas:** `frontend/src/dashboard/AdminDashboard.tsx` (`HealthStrip`,
`INTERFACE_LINKS`, Interfaces panel); reuse the permission-aware pattern from
`frontend/src/metrics/Metrics.tsx` (`AREA_LINKS` + `HealthRow`).

---

## P1-2 — Reconcile interface/ops grants: either give tenant_admin the surfaces or drop the dead grants

**User story:** As a tenant admin, I want my permission list to reflect what I can
actually do, so that I don't discover a capability exists only by reading the Account page.

**Acceptance criteria**
1. Pick one direction and apply it consistently across `MATRIX_C_TENANT_ADMIN` (and
   `MATRIX_B_EMRADM`, `MATRIX_A_PACS` if in scope):
   - **(a) Grant direction:** add `HL7_READ`, `ROUTING_READ`, `DICOMWEB_READ` to
     tenant_admin so the interfaces a facility operator manages are reachable, **or**
   - **(b) Trim direction:** remove `INTERFACE_ADMIN`/`INTERFACE_MONITOR`/`STORAGE_ADMIN`
     (and document `METERING_READ`/`BILLING_READ`/`CDS_ADMIN`/`REPORT_TEMPLATE_ADMIN`
     as roadmap-only) from the role so the permission list is honest.
2. Whichever direction: `BUILT_IN_ROLES['tenant_admin']` no longer contains a grant
   with no reachable surface, **except** grants explicitly flagged roadmap-only in
   the RBAC spec.
3. The RBAC matrix doc (`docs/reaserch/RBAC_matrix_spec.md`) is updated to match.
4. `test_rbac_matrix.py` gains an assertion that every non-roadmap grant of
   `tenant_admin` maps to at least one `RequirePermission`/`requires_permission` gate
   in the app.
5. Update the sidebar comments in `frontend/src/common/Sidebar.tsx` that currently
   document the mismatch ("INTERFACE_ADMIN was dropped from the gate …").

**Affected areas:** `backend/api/permissions.py` (MATRIX_C_TENANT_ADMIN + friends),
`frontend/src/common/Sidebar.tsx` (routing/hl7/dicomweb gates), `backend/tests/test_rbac_matrix.py`,
`docs/reaserch/RBAC_matrix_spec.md`.

**Note:** Direction (a) is the larger but more useful change for the persona; (b) is
cheap and safe if interface surfaces are intentionally super-admin-only. The dev
team should confirm intent with the product owner before choosing. This review
recommends **(a)** for HL7/ROUTING/DICOMweb (facility operators manage their own
interfaces) and trimming the four truly roadmap-only grants.

---

## P2-1 — Tenant cards show real user/study counts

**User story:** As a tenant admin, I want the Tenants page to show how many users and
studies my tenant has, so that I can gauge activity without clicking into anything.

**Acceptance criteria**
1. The tenant card renders actual `user_count` and `study_count` values (not "?")
   for `test.tenant_admin`.
2. Implement by either enriching `GET /api/v2/tenants` (scoped per tenant, cheap for
   the single-card case) **or** having the card call the existing
   `GET /tenants/{id}/stats` (the `TenantStats` type already exists in
   `frontend/src/api/tenants.ts`).
3. `last_activity` renders when available; card hides the line when null.
4. A test asserts the Tenants page never renders "? users".

**Affected areas:** `backend/api/tenants.py` (list enrichment) and/or
`frontend/src/tenants/Tenants.tsx` (fetch stats per card), `frontend/src/api/tenants.ts`.

---

## P2-2 — Tenant-scoped user directory with a visible tenant filter

**User story:** As a tenant admin, I want to see only my tenant's users (or at least
know which tenant each user belongs to), so that I never mistake another facility's
account for mine.

**Acceptance criteria**
1. The Users page shows a tenant column and/or a tenant filter.
2. Backend behavior is decided and consistent with the tenants-list scoping in
   `api/tenants.py`: either `GET /api/v2/users` is tenant-scoped for tenant-scoped
   admins, or the page makes cross-tenant rows unambiguous via the column/filter.
3. `test.tenant_admin` can filter to exactly the `default` tenant's users.
4. No regression for `super_admin` (sees all tenants, filter is optional).

**Affected areas:** `backend/api/users.py` (scoping), `frontend/src/users/Users.tsx`
(column + filter), `backend/tests/test_users*.py`.

---

## P2-3 — Roles page hints immutability before the 403

**User story:** As a tenant admin, I want to know which roles I cannot edit before I
try, so that I don't get a rejection after doing the work.

**Acceptance criteria**
1. Rows for roles the current user cannot modify (immutable anchors,
   platform-admin-only tiers) render a disabled/lock indicator (tooltip with reason).
2. Edit/Delete affordances are disabled (or show the tooltip) for those rows, for
   `test.tenant_admin`.
3. `super_admin` sees no change (everything editable per tier).

**Affected areas:** `frontend/src/roles/Roles.tsx` (use the immutability tier data —
`IMMUTABLE_ROLE_SLUGS` / `PLATFORM_ADMIN_ONLY_MODIFIABLE_ROLES` or a new
`/roles/meta` endpoint if the frontend lacks it).

---

## P2-4 — Notification role-defaults cover admin roles (P1-1 spillover)

**User story:** As a tenant admin, I want my bell to stay relevant out of the box, so
that I don't get an upload receipt for every file my facility stores.

**Acceptance criteria**
1. `db/notification_prefs.default_enabled()` mutes clinical event types for every
   admin-scoped role (`super_admin`, `tenant_admin`, `pacs_admin`, `emr_admin`) —
   not just `super_admin`.
2. The prefs page's copy reflects the new default for tenant_admin.
3. Backend tests cover the tenant_admin default.

**Affected areas:** `backend/db/notification_prefs.py`, `frontend/src/notifications/NotificationPreferences.tsx`,
`backend/tests/test_notification_prefs.py`.

---

## P2-5 — Files page surfaces search-unavailable state (not "No files uploaded")

**User story:** As a tenant admin, I want to know when search is degraded, so that I
don't believe my archive is empty when it isn't.

**Acceptance criteria**
1. When the search backend is unavailable, the Files page shows a distinguishable
   notice ("Search is unavailable — showing nothing" or similar), not the empty-archive
   copy.
2. The notice does not block upload (FILE_WRITE path unaffected).
3. A unit test covers the degraded-search branch (mock the failing search call).

**Affected areas:** `frontend/src/files/Files.tsx` (empty-state branch),
`backend/api/files.py` search handler (already logs "search disabled" — surface it).

---

## Definition of Done (whole hand-off)

- [ ] Backend: `pytest` passes (new tests for tenant scoping, grant-reconciliation,
      notification defaults, search-degraded).
- [ ] Frontend: `tsc` + `npm run build` pass; `ruff`/prettier clean.
- [ ] No schema change ships without an Alembic migration.
- [ ] Every new endpoint is permission-gated and validated with `parse_body()`.
- [ ] `scripts/dev.sh status` healthy; smoke-login as `test.tenant_admin` walks the
      Admin section with **zero dead "Open" buttons** (P1-1).
- [ ] E2E: tenant-admin spec covers the dashboard dead-end fix (P1-1), tenant card
      counts (P2-1), and users tenant filter (P2-2).
