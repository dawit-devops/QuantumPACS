# Phase 3 — Implementation Report (tenant_admin)

**Branch:** `phase/user-feature-review-tenant-admin`
**Date:** 2026-08-14
**Skill:** fullstack-guardian (workflow followed; repo conventions per CLAUDE.md)

## Scope

Implemented every hand-off item (2× P1 + 5× P2) from `03-handoff.md` per the
design in `04-design.md` (grant direction for P1-2).

## Security checkpoint (before code)

- **Authz:** no new endpoints. Enrichment (tenants list counts) stays behind the
  existing `TENANT_READ`/`CROSS_TENANT_READ` gate + own-tenant scoping; users
  tenant-filter is read-scoping only; the new `modifiable` field on the roles
  list is derived from the caller's admin flag (no new write path).
- **No schema change** → no Alembic table migration; grant changes ship via the
  migration-059-style role-grant migration 061 (idempotent append + token bump).
- **Output:** no secrets leak — `_pool_info_for()` keeps `db_password` internal
  to `get_stats()` (existing contract preserved); response shapes only *add*
  fields (`search_available`, `modifiable`, `user_count`/`study_count`).

## Backend changes

| File | Change |
|------|--------|
| `backend/api/permissions.py` | `MATRIX_C_TENANT_ADMIN` gains `HL7_READ`, `ROUTING_READ`, `DICOMWEB_READ` (P1-2a) |
| `backend/migrations/versions/061_tenant_admin_interface_grants.py` | Idempotent grant append + `token_version` bump for tenant_admin holders (059 pattern) |
| `backend/migrations/versions/048_trim_legacy_role_grants.py` | Frozen snapshot updated to stay equal to `BUILT_IN_ROLES` (test parity) |
| `backend/api/tenants.py` | List enrichment (P2-1): per-visible-tenant `get_stats` merge → `user_count`/`study_count`/`file_count`/`last_activity`; `_pool_info_for()` helper shared with `TenantStatsHandler` |
| `backend/api/users.py` + `db/users.py` | P2-2: `get_users`/`count_users` gain `tenant` filter; `UsersHandler.get` scopes to own tenant for non-admin users |
| `backend/db/notification_prefs.py` | P2-4: `ADMIN_SCOPED_ROLE_SLUGS` (super/tenant/pacs/emr admin) mute clinical event types by default |
| `backend/es/es.py` + `backend/api/files.py` | P2-5: `es.available()`; search response carries `search_available: false` when ES down |
| `backend/api/roles.py` | P2-3: roles list adds authoritative `modifiable` field (immutable + platform-only tiers, admin-flag-aware) |

### New tests
| File | Covers |
|------|--------|
| `tests/test_rbac_matrix.py` | P1-2 grants present; no clinical writes; SYSTEM_ADMIN still absent |
| `tests/test_tenant_stats.py` | P2-1 list enrichment merges counts + registry fields |
| `tests/test_users_api.py` | P2-2 tenant-scoped admin passes own tenant; platform admin unscoped |
| `tests/test_notification_prefs.py` | P2-4 admin roles mute clinical, ops stay ON |
| `tests/test_roles.py` | P2-3 modifiable per tier + platform-admin bypass |
| `tests/test_files_search_degraded.py` | P2-5 degraded flag when ES down; absent when up |

## Frontend changes

| File | Change |
|------|--------|
| `frontend/src/dashboard/AdminDashboard.tsx` | **P1-1:** `HEALTH_LINK_PERMISSIONS` map; `HealthStrip` + Interfaces panel render "Open" only when the target route's permission passes (FHIR gated for tenant_admin; Storage/DICOM Listener/HL7 now real) |
| `frontend/src/account/Account.tsx` | **P1-2:** permission list grouped into capability families + "roadmap — no surface yet" tags |
| `frontend/src/tenants/Tenants.tsx` | **P2-1:** counts consumed from enriched list; `?` fallback → `—` (loading only) |
| `frontend/src/users/Users.tsx` + `src/api/users.ts` | **P2-2:** Tenant column (Tag / —); `User.tenant` typed |
| `frontend/src/roles/Roles.tsx` | **P2-3:** already had lock hints (R2-16) — now backed by the authoritative `modifiable` field |
| `frontend/src/notifications/NotificationPreferences.tsx` | **P2-4:** copy reflects admin-scoped defaults |
| `frontend/src/files/Files.tsx` + `src/api/files.ts` | **P2-5:** `search_available` state; warning Alert + degraded empty-state copy when search down |

## Verification

| Gate | Result |
|------|--------|
| `pytest` (backend full) | ✅ **1680 passed**, 4 xfailed |
| `ruff check` (changed files) | ✅ clean |
| `tsc --noEmit` | ✅ clean |
| `npm run build` | ✅ built in 8.3s |
| Alembic migration 061 | ✅ applied live; backend restarted healthy |
| Live smoke as `test.tenant_admin` | ✅ grants present in `/roles` (HL7/ROUTING/DICOMWEB True), tenants list carries counts (23 users/17 studies/20 files), users list tenant-scoped, search-degraded unit-tested |
| **P1-1 dead-ends** | ✅ dashboard FHIR "Open" hidden; DICOM Listener/HL7 "Open" now land on real pages; sidebar gains Routing/HL7/DICOMweb |
| **P2-1 counts** | ✅ "? users" gone; "23 users / 17 studies" render |
| **P2-2 tenant column** | ✅ Users table shows Tenant column |
| **P2-3 lock hints** | ✅ immutable anchor rows (EMR Admin, PACS Admin, Patient) show disabled Edit |
| **P1-2 Account groups** | ✅ "Tenant & platform ops" + "roadmap — no surface yet" render |

## Deviations from design

1. **P2-3 was already implemented** (frontend lock hints from the R2-16 work) —
   the backend `modifiable` field makes it authoritative and regression-tested
   rather than a new UI.
2. **No tenant filter Select on Users** — the backend now scopes the list itself
   for tenant-scoped admins, so a filter would always show one option for them
   (platform admins still see all tenants via the column). The column satisfies
   the "never mistake another facility's account" AC; a filter was dropped as
   redundant for the scoped persona.
3. **FHIR stays SYSTEM_ADMIN-only** per the design (platform FHIR policy) — the
   dashboard correctly hides its "Open" affordance for tenant_admin.
4. **Users "?" → "—"** instead of a shimmer: the enriched list resolves in the
   same request as the card, so a shimmer would be an empty flash, not a fetch
   wait.
