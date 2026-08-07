# API Contract: Cross-Tenant Grants (Ops)

**Version:** 1.0 · **Date:** 2026-08-04 · **Status:** Engineering-ready
**Companion:** `requrements/cross_tenant_grants_design.md` (DDL/RLS/audit) · `requrements/RBAC_matrix_spec.md` §7 (endpoint map)
**Conventions:** Starlette handlers · `@requires_permission("CODE")` · Pydantic request schemas · dot-notation audit events (per `docs/specs/audit-logs_design.md`)

---

## 1. Scope

Admin/ops API for managing **explicit cross-tenant access grants** (teleradiology, IDN priors, IDN scheduling). Three write/read surfaces:

| Endpoint | Method | Purpose | Min permission |
| :--- | :--- | :--- | :--- |
| `/api/cross-tenant-grants` | `GET` | List grants (admin view) | `TENANT_ADMIN` |
| `/api/cross-tenant-grants/{grant_id}` | `GET` | Grant detail | `TENANT_ADMIN` |
| `/api/cross-tenant-grants` | `POST` | Create grant + scopes (atomic) | `ADMIN` **+ role `SYSTEM_ADMIN`** |
| `/api/cross-tenant-grants/{grant_id}/revoke` | `POST` | Revoke grant (with reason) | `ADMIN` **+ role `SYSTEM_ADMIN`** |
| `/api/cross-tenant-grants/scopes` | `GET` | Purpose→allowed-scopes map + read-only whitelist (create-form presets, V11) | `ADMIN` **+ role `SYSTEM_ADMIN`** |
| `/api/cross-tenant-grants/mine` | `GET` | Current user's own active grants (UI display) | Any authenticated user |

> **Rationale for `ADMIN` + `SYSTEM_ADMIN` on writes:** grant creation/revocation is a platform-ops, audited action (design §3 — no permissive write policies; only the `SYSTEM_ADMIN`/`BYPASSRLS` role path). The `ADMIN` permission alone also grants `RADIOLOGY_ADMIN` (RBAC Matrix A), which must **not** create/revoke cross-tenant grants — so the handler checks **both** `@requires_permission("ADMIN")` **and** actor role membership `SYSTEM_ADMIN`. `TENANT_ADMIN` may *view* grants touching their facility but never create/revoke. Runtime enforcement of grants happens at the **database layer** (RLS helper), not via these endpoints.

---

## 2. Authorization & RLS interplay

1. Handler-level: `@requires_permission("TENANT_ADMIN")` (list/detail) or `@requires_permission("ADMIN")` **plus an actor-role check that the caller holds `SYSTEM_ADMIN`** (create/revoke) — the role check closes the `RADIOLOGY_ADMIN`-has-`ADMIN` path (design §3: writes are ops-role only).
2. Row-level: list/detail queries are filtered by the existing `ctg_self` RLS policy — an admin sees grants where `grantee_facility_id` **or** `target_facility_id` = their session facility; `SYSTEM_ADMIN` (BYPASSRLS) sees all.
3. `GET /mine` returns only `user_id = current user` rows (via `ctg_self`).
4. These endpoints never change `app.facility_id`; session facility = actor's facility for audit attribution.
5. Request tenant context must be resolved & valid before any grant read/write (standard middleware; reject unset tenant on admin routes).

---

## 3. Schemas

### 3.1 `POST /api/cross-tenant-grants` — Create

**Request body** (Pydantic `CreateCrossTenantGrantRequest`):

```json
{
  "user_id": 42,
  "grantee_facility_id": 1,
  "target_facility_id": 7,
  "purpose": "TELERADIOLOGY_READ",
  "scopes": ["STUDY_READ", "REPORT_READ", "WORKLIST_READ", "VIEWER_READ"],
  "valid_from": "2026-08-04T00:00:00Z",
  "expires_at": "2027-08-04T00:00:00Z"
}
```

| Field | Type | Required | Rules |
| :--- | :--- | :-: | :--- |
| `user_id` | int | yes | User must exist and be `active=true` |
| `grantee_facility_id` | int | yes | Facility must exist & not `CLOSED`; user must hold ≥1 role grant (`user_roles`) there |
| `target_facility_id` | int | yes | Facility must exist & not `CLOSED`; `!= grantee_facility_id` (no self-grant) |
| `purpose` | string | yes | ∈ `TELERADIOLOGY_READ` \| `IDN_PRIORS` \| `IDN_SCHEDULE_READ` \| `XDS_I_B_SHARING` |
| `scopes` | string[] | yes | Non-empty; **every** code ∈ read-only set (§5); no duplicates |
| `valid_from` | datetime | no | Defaults `now()`; must be `<= expires_at` when `expires_at` set |
| `expires_at` | datetime | no | Defaults `null` (until revoked); must be `> valid_from` |

**Response `201 Created`:**

```json
{
  "data": {
    "grant_id": 101,
    "user_id": 42,
    "user_display_name": "Dr. Alan Chen",
    "grantee_facility_id": 1,
    "grantee_facility_code": "NGH",
    "target_facility_id": 7,
    "target_facility_code": "CLINIC",
    "purpose": "TELERADIOLOGY_READ",
    "access_type": "READ",
    "scopes": ["STUDY_READ", "REPORT_READ", "WORKLIST_READ", "VIEWER_READ"],
    "status": "ACTIVE",
    "valid_from": "2026-08-04T00:00:00Z",
    "expires_at": "2027-08-04T00:00:00Z",
    "granted_by": 1,
    "granted_at": "2026-08-04T09:00:00Z"
  }
}
```

### 3.2 `POST /api/cross-tenant-grants/{grant_id}/revoke` — Revoke

**Request body** (`RevokeCrossTenantGrantRequest`):

```json
{ "reason": "Contract ended 2026-08-04" }
```

| Field | Type | Required | Rules |
| :--- | :--- | :-: | :--- |
| `reason` | string | yes | Trimmed, 1–500 chars; recorded in `revoke_reason` + audit payload |

**Behavior:** `status → REVOKED`, `revoked_at = now()`, `revoked_by = actor`. **Idempotent:** revoking an already-`REVOKED` grant returns `200` with the current state (no-op). Revoking an `EXPIRED` grant → `409` (`GRANT_ALREADY_EXPIRED`). Takes effect on the **next request** (per-request authorization, design §6.4).

**Response `200 OK`:** same grant object shape as §3.1 with `status: "REVOKED"`, `revoked_at`, `revoked_by`, `revoke_reason`.

### 3.3 `GET /api/cross-tenant-grants` — List

Query params (all optional): `status` (ACTIVE/REVOKED/EXPIRED) · `purpose` · `grantee_facility_id` · `target_facility_id` · `user_id` · `date_from` · `date_to` (on `granted_at`) · `limit` (default 50, max 200) · `cursor`.

**Response `200 OK`:**

```json
{
  "data": [
    {
      "grant_id": 101,
      "user_id": 42,
      "user_display_name": "Dr. Alan Chen",
      "grantee_facility_id": 1,
      "grantee_facility_code": "NGH",
      "target_facility_id": 7,
      "target_facility_code": "CLINIC",
      "purpose": "TELERADIOLOGY_READ",
      "access_type": "READ",
      "scopes": ["STUDY_READ", "REPORT_READ", "WORKLIST_READ", "VIEWER_READ"],
      "status": "ACTIVE",
      "valid_from": "2026-08-04T00:00:00Z",
      "expires_at": "2027-08-04T00:00:00Z",
      "granted_by": 1,
      "granted_at": "2026-08-04T09:00:00Z",
      "revoked_at": null,
      "revoke_reason": null
    }
  ],
  "total": 3,
  "next_cursor": "eyJhY3RvciI6...",
  "has_more": false
}
```

### 3.6 `GET /api/cross-tenant-grants/scopes` — Purpose/scope map (create-form presets)

Returns the V11 policy (§4.1) so the UI never hard-codes scope rules. **Response `200 OK`:**

```json
{
  "data": {
    "whitelist": ["STUDY_READ", "REPORT_READ", "WORKLIST_READ", "SCHEDULE_READ", "VIEWER_READ", "RESULTS_READ", "PATIENT_READ"],
    "purposes": {
      "TELERADIOLOGY_READ": ["STUDY_READ", "REPORT_READ", "WORKLIST_READ", "VIEWER_READ", "RESULTS_READ", "PATIENT_READ"],
      "IDN_PRIORS": ["STUDY_READ", "REPORT_READ", "PATIENT_READ"],
      "IDN_SCHEDULE_READ": ["SCHEDULE_READ"],
      "XDS_I_B_SHARING": ["STUDY_READ", "REPORT_READ"]
    }
  }
}
```

> Consumed by the create-form UI (`docs/specs/cross-tenant-grants_design.md`); cached client-side per session, re-fetched on page load.

### 3.4 `GET /api/cross-tenant-grants/{grant_id}` — Detail

**Response `200 OK`:** single grant object (shape above). `404 GRANT_NOT_FOUND` if absent or not visible under `ctg_self`.

### 3.5 `GET /api/cross-tenant-grants/mine` — My grants

Returns the caller's own `ACTIVE` grants (grants where `user_id` = caller and `status = 'ACTIVE'`, plus `expires_at > now()`). Response: `{ "data": [...] }` using the detail shape. Used by the UI to show "you can read studies at: CLINIC (until …)". `O` — optional v1.

---

## 4. Validation Rules (server-side, in order)

| # | Rule | Failure |
| :-: | :--- | :--- |
| V1 | `user_id` exists and `active` | `404 USER_NOT_FOUND` |
| V2 | `grantee_facility_id` exists, not `CLOSED` | `404 FACILITY_NOT_FOUND` |
| V3 | User holds ≥1 role at `grantee_facility_id` (`user_roles`) | `422 GRANTEE_MEMBERSHIP_REQUIRED` |
| V4 | `target_facility_id` exists, not `CLOSED` | `404 FACILITY_NOT_FOUND` |
| V5 | `grantee_facility_id != target_facility_id` | `422 SELF_GRANT_NOT_ALLOWED` |
| V6 | `purpose` ∈ allowed set | `422 VALIDATION_ERROR` (details: purpose) |
| V7 | `scopes` non-empty, no duplicates, all ∈ read-only set (§5) | `422 VALIDATION_ERROR` (details: scopes) |
| V8 | `valid_from` default `now()`; `expires_at > valid_from` | `422 VALIDATION_ERROR` (details: dates) |
| V9 | No **duplicate ACTIVE grant** for (user, grantee, target, purpose) — reuse or revoke first | `409 DUPLICATE_ACTIVE_GRANT` |
| V10 | Target facility subscription not `SUSPENDED`/`CANCELLED` (a grant there is dead on arrival) | `422 TARGET_FACILITY_SUSPENDED` |
| V11 | **Purpose→scope policy:** scopes must match the purpose's allowed set (§4.1). A `TELERADIOLOGY_READ` grant cannot carry `SCHEDULE_READ`; `IDN_SCHEDULE_READ` can only carry `SCHEDULE_READ` | `422 VALIDATION_ERROR` (details: purpose/scopes) |

> **Grantee-side subscription note:** the grantee (employer) facility is not subscription-checked in V10 — if the grantee is `SUSPENDED`, the user cannot log in anyway (app-level gate), so no grant is needed. Optionally warn when the grantee is `SUSPENDED`. **Extending grants:** there is no update endpoint in v1 — extend `expires_at`/scopes by revoke + recreate (V9's "reuse or revoke first"); a future `PATCH /api/cross-tenant-grants/{grant_id}` (extend `expires_at`, add scopes within purpose policy) is an `O`-priority addition.

### 4.1 Purpose → allowed scopes (V11 policy)

| Purpose | Allowed scopes (subset of the §5 whitelist) |
| :--- | :--- |
| `TELERADIOLOGY_READ` | `STUDY_READ`, `REPORT_READ`, `WORKLIST_READ`, `VIEWER_READ`, `RESULTS_READ`, `PATIENT_READ` |
| `IDN_PRIORS` | `STUDY_READ`, `REPORT_READ`, `PATIENT_READ` |
| `IDN_SCHEDULE_READ` | `SCHEDULE_READ` only |
| `XDS_I_B_SHARING` | `STUDY_READ`, `REPORT_READ` |

> **Scope whitelist (read-only, from RBAC spec §3):** `STUDY_READ`, `REPORT_READ`, `WORKLIST_READ`, `SCHEDULE_READ`, `VIEWER_READ`, `RESULTS_READ`, `PATIENT_READ`. Anything else (incl. all write codes) → V7 reject. This whitelist is enforced both at the API and by the DB `permissions(code)` FK.

---

## 5. Error Handling

Envelope (consistent across the platform):

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Request validation failed",
    "details": [ { "field": "scopes", "message": "code 'BILLING_WRITE' is not a read-only scope" } ]
  }
}
```

| HTTP | Code | Notes |
| :-: | :--- | :--- |
| 401 | `UNAUTHORIZED` | Missing/invalid token |
| 403 | `FORBIDDEN` | Authenticated but missing `ADMIN`/`TENANT_ADMIN` |
| 404 | `GRANT_NOT_FOUND` / `USER_NOT_FOUND` / `FACILITY_NOT_FOUND` | |
| 409 | `DUPLICATE_ACTIVE_GRANT` / `GRANT_ALREADY_EXPIRED` | Conflict / state mismatch |
| 422 | `VALIDATION_ERROR` + rule-specific code in `details` | V3/V5/V7/V8/V10/V11 |
| 429 | `RATE_LIMITED` | Admin op throttle (§7) |
| 500 | `INTERNAL` | Unhandled |

---

## 6. Audit Events

Emitted through the platform audit pipeline (`audit_log`, partitioned; `audit-logs_design.md`). Envelope fields: `event_type`, `actor`, `resource_type`, `resource_id`, `description`, `tenant` (actor's facility), `payload` (JSONB).

> **Naming alignment with the design doc:** `cross_tenant_grants_design.md` §5.2 refers to the same events as `action='CROSS_TENANT_GRANT'` / `'CROSS_TENANT_READ'` / `'CROSS_TENANT_DENIED'` (the raw `audit_log.action` column, which allows free-form TEXT). The **canonical, UI-visible naming is the dot-notation `event_type` below**; the design-doc `action` values map: `CROSS_TENANT_GRANT` → `cross_tenant_grant.created/revoked/expired`, `CROSS_TENANT_READ` → `cross_tenant.read`, `CROSS_TENANT_DENIED` → `cross_tenant.denied`. Implementers emit `event_type` (dot-notation) and may also set `action` for raw-table compatibility.

| Event | Trigger | actor | resource_type/id | payload (required fields) |
| :--- | :--- | :--- | :--- | :--- |
| `cross_tenant_grant.created` | `POST` create success | requester user | `cross_tenant_grants` / `{grant_id}` | `{grantee_facility_id, target_facility_id, purpose, scopes, valid_from, expires_at}` |
| `cross_tenant_grant.revoked` | revoke success | revoking user | `cross_tenant_grants` / `{grant_id}` | `{grantee_facility_id, target_facility_id, purpose, reason, revoked_by}` |
| `cross_tenant_grant.expired` | daily sweep flips status | `system` | `cross_tenant_grants` / `{grant_id}` | `{expires_at}` |
| `cross_tenant.read` | middleware, post-authorized read | reader user | `studies`/`reports` / `{study_or_report_uid}` | `{source_facility, target_facility, grant_id, purpose, scope}` |
| `cross_tenant.denied` | failed/unauthorized attempt | attempting user | `studies`/`reports` / `{uid if known}` | `{source_facility, target_facility, grant_id: null, reason}` |

**Audit-logs UI:** the structured viewer gains a `purpose`/`grant_id` facet (super admin) enabling queries like *"all `cross_tenant.read` events where target_facility = CLINIC in the last 30 days"*. Event grouping: `cross_tenant.*` under **Data Access**.

**Integrity:** lifecycle events are written by the handler **in the same transaction** as the grant change (rollback removes both); read/denied events are fire-and-log via the middleware helper (never blocking clinical reads). No grant event is ever silently purged (retention + legal hold, design A5).

---

## 7. Rate Limiting & Security Notes

- **Admin ops throttle:** per-actor token bucket on `POST`/`revoke` — 30 ops/min (Redis, keyed by user_id, mirroring the platform's rate-limit pattern); `GET` endpoints exempt.
- **No PHI in responses:** grant objects contain user/facility identifiers and purpose — no patient data.
- **CSRF:** state-changing endpoints are token-authenticated; `SameSite=Strict` cookie policy applies to session-authenticated calls (platform default).
- **SSRF/IDOR:** `grant_id`/`user_id` are validated for existence and scope; list/detail always subject to `ctg_self` — a tenant admin can never read another facility's unrelated grants.
- **Logging:** every rejection (V1–V11, permission denials) logged at `info` with reason code for ops forensics.

---

## 8. Transactionality & Concurrency

| Operation | Guarantee |
| :--- | :--- |
| Create | `INSERT cross_tenant_grants` + scopes + audit event in **one transaction**; any failure (incl. duplicate check race) rolls back — no grant without scopes, no scopes without audit. |
| Revoke | `UPDATE` status/revoked fields + audit event in one transaction; concurrent double-revoke serializes via row lock → second caller sees `REVOKED` and no-ops (idempotent). |
| Duplicate guard | Unique predicate evaluated with `FOR UPDATE` on existing ACTIVE grant (or advisory lock) to close the race between two simultaneous creates. |
| Expiry sweep | pg_cron daily; sets `status='EXPIRED'` under the ops role; helper also enforces `expires_at > now()` at query time (defense in depth). |

---

## 9. Example Flows (curl)

```bash
# 9.1 Create (SYSTEM_ADMIN)
curl -X POST https://portal.example.com/api/cross-tenant-grants \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": 42,
    "grantee_facility_id": 1,
    "target_facility_id": 7,
    "purpose": "TELERADIOLOGY_READ",
    "scopes": ["STUDY_READ","REPORT_READ","WORKLIST_READ","VIEWER_READ"],
    "expires_at": "2027-08-04T00:00:00Z"
  }'
# → 201, grant_id=101; audit cross_tenant_grant.created

# 9.2 List active grants for a target facility (TENANT_ADMIN)
curl -G https://portal.example.com/api/cross-tenant-grants \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -d status=ACTIVE -d target_facility_id=7 -d limit=50
# → {data:[...], total, next_cursor, has_more}

# 9.3 Revoke (SYSTEM_ADMIN)
curl -X POST https://portal.example.com/api/cross-tenant-grants/101/revoke \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{ "reason": "Contract ended 2026-08-04" }'
# → 200, status=REVOKED; audit cross_tenant_grant.revoked
# Next request by user 42 to CLINIC studies → 403 + cross_tenant.denied audit
```

---

## 10. Acceptance Criteria (API-level)

| ID | Criterion | Maps to |
| :-: | :--- | :--- |
| CTG-API-01 | **GIVEN** a `SYSTEM_ADMIN` **WHEN** creating a valid grant **THEN** 201 returns grant + scopes; grant + `cross_tenant_grant.created` audit exist atomically. | CTG-AC-01, A1 |
| CTG-API-02 | **GIVEN** any of V1–V10 violated **WHEN** POSTed **THEN** the mapped 4xx with error envelope returns and **no** grant/audit row is created. | CTG-AC-02/05 |
| CTG-API-03 | **GIVEN** a duplicate ACTIVE grant attempt **WHEN** POSTed **THEN** 409 `DUPLICATE_ACTIVE_GRANT`; parallel duplicate attempts serialize (one succeeds). | V9 |
| CTG-API-04 | **GIVEN** a revoke **WHEN** performed **THEN** 200 with REVOKED state; idempotent on re-revoke; revoking EXPIRED → 409; audit `cross_tenant_grant.revoked`. | CTG-AC-03, A1 |
| CTG-API-05 | **GIVEN** a tenant admin (non-SYSTEM_ADMIN) **WHEN** they POST or revoke **THEN** 403 `FORBIDDEN`; **WHEN** they GET list/detail **THEN** only grants touching their facility return (ctg_self). | CTG-AC-06, A4 |
| CTG-API-06 | **GIVEN** a revoked/expired grant **WHEN** the grantee reads target data **THEN** 403 + `cross_tenant.denied` audit; **GIVEN** an ACTIVE grant **WHEN** reading **THEN** `cross_tenant.read` audit with source/target/grant_id. | CTG-AC-03, PAC-AC-P20-03 |
| CTG-API-07 | **GIVEN** admin op throttling **WHEN** > 30 write ops/min **THEN** 429 `RATE_LIMITED`. | §7 |

---

## 11. Implementation Checklist

- [ ] Schemas: `CreateCrossTenantGrantRequest`, `RevokeCrossTenantGrantRequest` (Pydantic) with §4 rules.
- [ ] Handlers: `CrossTenantGrantsHandler` (`GET`, `POST`), `CrossTenantGrantHandler` (`GET`, revoke `POST`), `MyGrantsHandler` — registered in `routes.py`.
- [ ] `db/cross_tenant_grants.py`: create (txn + duplicate guard), revoke (txn), list (filters + cursor), get, get_mine.
- [ ] Audit wiring: lifecycle events in-txn; `cross_tenant.read`/`.denied` middleware hooks (design §5.2).
- [ ] Permission gates: `@requires_permission("ADMIN")` **+ `SYSTEM_ADMIN` role check** on create/revoke (closes the `RADIOLOGY_ADMIN`-has-`ADMIN` path); `TENANT_ADMIN` on list/detail; auth-only on `/mine`.
- [ ] Admin op rate limiter (Redis, 30/min/user).
- [ ] Audit-logs UI `purpose`/`grant_id` facet + Data Access grouping.
- [ ] Admin console UI: `docs/specs/cross-tenant-grants_design.md` (list/create/revoke, purpose-driven scope groups, status/expiry badges, route guard).
- [ ] Tests: CTG-API-01…07 (unit + integration), incl. RLS scope checks.
