# Design: Cross-Tenant Access Grants (`cross_tenant_grants`)

**Version:** 1.0 · **Date:** 2026-08-04 · **Status:** Engineering-ready (DDL + RLS + audit)
**Companion:** `requrements/RBAC_matrix_spec.md` §6 · `research/pacs-ris-multitenancy.md` §3 (cross-facility priors), §5.2 (machine tenancy), §9 (security controls matrix)

---

## 1. Purpose & Scope

The platform isolates every clinical row by `facility_id` via RLS. But two **legitimate cross-facility workflows** must exist without weakening that isolation:

1. **Teleradiology (PAC-P03)** — a remote radiologist employed by facility A reads studies *owned by* facilities B, C, … under an engagement contract. Requires read access to studies, priors, and reports across facilities, fully audited.
2. **IDN priors & enterprise scheduling (I5, PAC-I05)** — within a merged health system, priors from another facility must be retrievable at read time (XDS-I.b), and schedulers may view availability across sites.

**Design principle:** cross-facility access is **never** a side-effect of the user's normal session. It requires an explicit, time-boxed, purpose-labeled, **read-only** grant record; every use is authorization-checked per request and audited with source + target facility. No cross-tenant *writes* are ever permitted.

**Requirement traceability (source):** PAC-US-P03-01/03, PAC-US-P20-03, RIS-US-P03-04, RIS-US-P20-02, EMR-US-P20-02 · PAC-AC-P03-01/03, PAC-AC-P20-03, RIS-AC-P20-02, EMR-AC-P20-02 · SLAs PAC-SL-25 (authorization < 1 s, 100% audited), PAC-SL-61 / RIS-SL-61 / EMR-SL-63 (0 cross-tenant incidents).

---

## 2. Data Model (DDL)

Consistent with `pacs-ris-schema.sql` conventions: `BIGINT GENERATED ALWAYS AS IDENTITY` PKs, `TIMESTAMPTZ`, `TEXT + CHECK` for evolving statuses, RLS on tenant-scoped tables, **no RLS** on platform tables.

```sql
-- ---------------------------------------------------------------------------
-- Cross-tenant access grants
-- ---------------------------------------------------------------------------
-- One row per (user, grantee facility, target facility, purpose).
-- A user may hold grants for several target facilities (teleradiologist).
CREATE TABLE cross_tenant_grants (
    grant_id            BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id             BIGINT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    grantee_facility_id BIGINT NOT NULL REFERENCES facilities(facility_id),  -- RESTRICT (deliberate: audit integrity)
    target_facility_id  BIGINT NOT NULL REFERENCES facilities(facility_id),  -- RESTRICT (deliberate: audit integrity)
    purpose             TEXT NOT NULL CHECK (purpose IN
        ('TELERADIOLOGY_READ','IDN_PRIORS','IDN_SCHEDULE_READ','XDS_I_B_SHARING')),
    access_type         TEXT NOT NULL DEFAULT 'READ' CHECK (access_type = 'READ'),
    status              TEXT NOT NULL DEFAULT 'ACTIVE' CHECK (status IN ('ACTIVE','REVOKED','EXPIRED')),
    valid_from          TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at          TIMESTAMPTZ,                 -- NULL = until revoked
    granted_by          BIGINT NOT NULL REFERENCES users(user_id),
    granted_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    revoked_by          BIGINT REFERENCES users(user_id),
    revoked_at          TIMESTAMPTZ,
    revoke_reason       TEXT,
    CONSTRAINT chk_no_self_grant       CHECK (grantee_facility_id <> target_facility_id),
    CONSTRAINT chk_grant_clock         CHECK (expires_at IS NULL OR expires_at > valid_from),
    CONSTRAINT chk_revoke_consistency  CHECK ((status = 'REVOKED') = (revoked_at IS NOT NULL))
);

-- Fine-grained scopes per grant. FK to permissions(code) = the canonical
-- catalog from RBAC_matrix_spec.md §3 (STUDY_READ, REPORT_READ, WORKLIST_READ,
-- SCHEDULE_READ, VIEWER_READ, RESULTS_READ, ...). No write codes allowed.
CREATE TABLE cross_tenant_grant_scopes (
    grant_id        BIGINT NOT NULL REFERENCES cross_tenant_grants(grant_id) ON DELETE CASCADE,
    permission_code TEXT NOT NULL REFERENCES permissions(code) ON DELETE CASCADE,
    PRIMARY KEY (grant_id, permission_code)
);

-- Lookups
CREATE INDEX ctg_lookup ON cross_tenant_grants (user_id, grantee_facility_id, status, expires_at);
CREATE INDEX ctg_target  ON cross_tenant_grants (target_facility_id, status);
CREATE INDEX ctg_scopes  ON cross_tenant_grant_scopes (permission_code);

COMMENT ON TABLE  cross_tenant_grants       IS 'Explicit, time-boxed, read-only cross-facility access grants (teleradiology, IDN priors).';
COMMENT ON TABLE  cross_tenant_grant_scopes IS 'Read permission codes granted per cross-tenant grant.';
```

**Design decisions**

| Decision | Rationale |
| :--- | :--- |
| Facility-pair grants (not patient-level) | Grants model *engagement/relationship* (group practice ↔ client facility). Patient-level lists would churn on merges/MPI changes. |
| `purpose` enum | Auditable "why" per grant; drives policy (e.g., `IDN_SCHEDULE_READ` scopes `SCHEDULE_READ` only) and anomaly detection. |
| `access_type = 'READ'` only | Cross-tenant writes are forbidden by design — the RLS policies below add a SELECT-only path, never INSERT/UPDATE/DELETE. |
| Scopes as child table with FK to `permissions(code)` | Enforces valid permission codes; queryable for policy evaluation; prevents scope creep beyond read codes. |
| `expires_at` nullable | Long-lived engagements (contract renewals) default to *until revoked*; short contracts set an explicit expiry. |
| `chk_no_self_grant` | A facility cannot "grant" access to itself (that is the normal RLS path). |
| `chk_revoke_consistency` | Status and revoke timestamps can never disagree (audit integrity). |
| `grantee_facility_id` / `target_facility_id` use `RESTRICT` (not the schema-wide `ON DELETE CASCADE`) | Deliberate deviation: grants are legal/audit records; a facility row is never hard-deleted (status `CLOSED`/`MERGER_PENDING` instead), and cascade-deleting grants on facility deletion would erase the audit trail. |

---

## 3. Row-Level Security on the Grants Tables

The grants tables are **platform-adjacent** (they cross facilities), so RLS there is selective: users may only ever see grants relevant to them; writes are restricted to the audited ops role.

```sql
ALTER TABLE cross_tenant_grants       ENABLE ROW LEVEL SECURITY;
ALTER TABLE cross_tenant_grant_scopes ENABLE ROW LEVEL SECURITY;

-- A user may SELECT only grants where they are the grantee, the grantee's
-- employer (tenant admin of grantee facility), or the target facility admin.
-- This keeps the authorization helper (below) from leaking other grants.
CREATE POLICY ctg_self ON cross_tenant_grants
  FOR SELECT
  USING (user_id = NULLIF(current_setting('app.user_id', true), '')::BIGINT
         OR grantee_facility_id = app_current_facility_id()
         OR target_facility_id  = app_current_facility_id());

-- Scopes visible alongside their parent grant (join-friendly policy).
CREATE POLICY ctg_scopes_read ON cross_tenant_grant_scopes
  FOR SELECT
  USING (EXISTS (
      SELECT 1 FROM cross_tenant_grants g
      WHERE g.grant_id = cross_tenant_grant_scopes.grant_id
        AND (g.user_id = NULLIF(current_setting('app.user_id', true), '')::BIGINT
             OR g.grantee_facility_id = app_current_facility_id()
             OR g.target_facility_id  = app_current_facility_id())));

-- Writes (create / revoke) are allowed ONLY via the audited ops role
-- (SYSTEM_ADMIN, BYPASSRLS). No permissive INSERT/UPDATE/DELETE policies
-- exist, so the app role can never self-grant.
```

**Grant lifecycle (who can do what)**

| Action | Performed by | Mechanism |
| :--- | :--- | :--- |
| Create grant + scopes | SYSTEM_ADMIN (platform ops, audited) | `POST /api/cross-tenant-grants` — validates purpose, scopes ⊆ read codes, no self-grant, future `expires_at` |
| Revoke | SYSTEM_ADMIN (or automated expiry) | `POST /api/cross-tenant-grants/{id}/revoke` with `revoke_reason`; sets `status='REVOKED'`, `revoked_at`, `revoked_by` |
| Auto-expiry | Daily sweep (pg_cron) | `UPDATE ... SET status='EXPIRED' WHERE expires_at < now() AND status='ACTIVE'` |
| View | Grantee / grantee-admin / target-admin | SELECT via `ctg_self` policy |

---

## 4. Authorization Helper & RLS Policy Extension (read-only)

The grant is enforced at the **database layer**: each target table's RLS policy gains a read-only OR-clause that consults the user's active grants for the permission being exercised.

```sql
-- Returns the facility ids the current user may READ for a given permission.
-- SECURITY DEFINER: runs as table owner (BYPASSRLS) so it can read grants;
-- app.user_id / app.facility_id are set per request by middleware.
CREATE OR REPLACE FUNCTION app_cross_accessible_facilities(p_permission TEXT)
RETURNS BIGINT[] LANGUAGE sql STABLE SECURITY DEFINER
SET search_path = public
SET row_security = off AS $$
    SELECT COALESCE(array_agg(g.target_facility_id), '{}')
    FROM cross_tenant_grants g
    JOIN cross_tenant_grant_scopes s ON s.grant_id = g.grant_id
    WHERE g.user_id             = NULLIF(current_setting('app.user_id', true), '')::BIGINT
      AND g.grantee_facility_id = NULLIF(current_setting('app.facility_id', true), '')::BIGINT
      AND g.status              = 'ACTIVE'
      AND g.valid_from          <= now()
      AND (g.expires_at IS NULL OR g.expires_at > now())
      AND s.permission_code     = p_permission;
$$;
```

Extend the existing `rls_all` policies with a **SELECT-only** cross-read policy on the tables that may be cross-read. Example for `studies`:

```sql
CREATE POLICY rls_cross_read ON studies
  FOR SELECT
  USING (facility_id = ANY (app_cross_accessible_facilities('STUDY_READ')));
```

Per-table policy additions (read-only, all `FOR SELECT`):

| Table | Policy | Scope used |
| :--- | :--- | :--- |
| `studies`, `series`, `instances`, `storage_objects` | `rls_cross_read` | `STUDY_READ` |
| `reports`, `report_versions` | `rls_cross_read` | `REPORT_READ` |
| `worklist_entries` | `rls_cross_read` | `WORKLIST_READ` |
| `appointments`, `rooms`, `modalities` (read-only lists) | `rls_cross_read` | `SCHEDULE_READ` |
| `patients`, `patient_identifiers`, `insurance_coverages` | `rls_cross_read` (join-style, see DDL below) | `PATIENT_READ` |

`patients` carries `facility_id`, so it uses the same `ANY(...)` form. `patient_identifiers` / `insurance_coverages` have **no** `facility_id`; their existing join policies must OR the grants array through the patient:

```sql
CREATE POLICY rls_cross_identifiers ON patient_identifiers
  FOR SELECT
  USING (EXISTS (
      SELECT 1 FROM patients p
      WHERE p.patient_id = patient_identifiers.patient_id
        AND (p.facility_id = app_current_facility_id()
             OR p.facility_id = ANY (app_cross_accessible_facilities('PATIENT_READ')))));
CREATE POLICY rls_cross_coverages ON insurance_coverages
  FOR SELECT
  USING (EXISTS (
      SELECT 1 FROM patients p
      WHERE p.patient_id = insurance_coverages.patient_id
        AND (p.facility_id = app_current_facility_id()
             OR p.facility_id = ANY (app_cross_accessible_facilities('PATIENT_READ')))));
```

> **How policies compose:** for a SELECT, PostgreSQL ORs all permissive policies. The home-facility `rls_all` (FOR ALL) still governs the user's own facility; `rls_cross_read` (FOR SELECT) adds only the granted targets. No cross-tenant INSERT/UPDATE/DELETE path exists — `rls_all`'s `WITH CHECK` still requires `facility_id = app_current_facility_id()`.

**Runtime flow (per request)**

```
Request (teleradiologist @ NGH reads study at CLINIC)
  → middleware resolves session facility = NGH, sets app.user_id/app.facility_id
  → query hits RLS on studies
  → planner: facility_id = NGH (home)  OR  facility_id ∈ app_cross_accessible_facilities('STUDY_READ')
  → helper (index-backed, STABLE) returns [CLINIC, ...] from ACTIVE grants
  → row returned; middleware records audit event (source=NGH, target=CLINIC, grant_id, purpose)
```

**SLA:** authorization decision is an index-backed lookup (< 1 s, PAC-SL-25); the facility array is cached per request in session context by middleware to avoid repeated function calls.

### 4.1 Pixel egress (DICOMweb/object storage) — the PACS-specific path

RLS protects the **SQL metadata** (studies/series/instances/storage_objects rows). Pixels live in object storage under the target tenant's prefix (`s3://vna/{tenant_code}/{facility_id}/…`), where IAM (not RLS) is the boundary. For teleradiology/priors to work end-to-end, the **DICOMweb layer must enforce the same grant**:

- **QIDO-RS / WADO-RS metadata:** served from the RLS-protected tables above — a granted reader sees the target facility's studies; a non-granted reader sees nothing (and the 403/empty result is audited as `CROSS_TENANT_DENIED`).
- **WADO-RS pixels:** the DICOMweb handler authorizes the request **before** resolving object keys: the bearer user must either be at the study's home facility or hold an ACTIVE grant covering `STUDY_READ` for that facility. Only then does the handler stream the object (the object store IAM for the app role already restricts reads to the shared-bucket tenant prefixes; cross-tenant streaming rides on the authorized study context, never on raw object keys).
- **Failure mode:** without this app-layer check, a direct WADO-RS by `StudyInstanceUID` would be blocked by IAM (denying the primary use case) or inconsistently allowed by object-store policy — never silently allowed for an unauthorized user.
- Every WADO/QIDO pixel/metadata retrieval is already logged in `dicom_transactions`; the middleware audit (A2) adds the source/target/grant envelope.

---

## 5. Audit Policy

### 5.1 Audit requirements (from RBAC §6 + HIPAA)

| # | Requirement |
| :-: | :--- |
| A1 | Every **grant lifecycle** event (create / revoke / expire) is audit-logged: actor, grantee, grantee_facility, target_facility, purpose, scopes, reason. |
| A2 | Every **cross-tenant read** is audit-logged with source facility, target facility, grant_id, purpose, resource (study/report UID), and actor. |
| A3 | Attempts to access a target facility **without** an active grant are denied and logged (failed-authorization audit). |
| A4 | Audit records are tamper-evident, facility-scoped, partitioned monthly, and queryable from the audit-logs UI (super admin sees all; tenant admins see their facility's records). |
| A5 | Retention of cross-tenant audit follows the platform audit retention policy + legal hold; nothing cross-tenant is ever purged silently. |

### 5.2 Implementation

Grant lifecycle events reuse the existing `audit_log` table (partitioned, trigger-driven pattern in schema §10):

- **Lifecycle:** dedicated audit rows via app code (ops endpoints) — `action='CROSS_TENANT_GRANT'`, `entity_type='cross_tenant_grants'`, `entity_id=grant_id`, `after` JSONB = `{grantee_facility, target_facility, purpose, scopes:[...], expires_at, reason}`.
- **Reads:** the existing `dicom_transactions` table already logs WADO-RS/QIDO-RS with `facility_id` and `ae_title`. For cross-tenant reads add an explicit audit event in the middleware (after the RLS-authorized fetch): `action='CROSS_TENANT_READ'`, `entity_type='studies'|'reports'`, `entity_id=<study/report UID>`, `after` JSONB = `{source_facility, target_facility, grant_id, purpose, scope}`. Written via the audited ops role or an app-level `insert_cross_tenant_audit()` SECURITY DEFINER helper so it is never blocked by RLS.
- **Failed attempts:** middleware logs `action='CROSS_TENANT_DENIED'` with the same envelope when `app_cross_accessible_facilities(...)` excludes the requested facility.

**Audit-logs UI (existing `audit-logs_design.md`):** the structured viewer's tenant filter (super admin) plus a new `purpose`/`grant_id` facet enables compliance queries such as *"all studies facility CLINIC read by teleradiologist X in the last 30 days"*.

**Anomaly alerting (optional, roadmap):** interface-events or notification hooks when cross-tenant read volume/spike, off-hours pattern, or purpose misuse is detected (`purpose` makes this query trivial).

---

## 6. Workflows

### 6.1 Teleradiology engagement (PAC-WF4)

> **Precondition (session model):** cross-tenant grants activate only when the user's **session facility = grantee facility** (their employer/group practice). A remote reader who instead authenticates directly into the client's own tenant already has client access via their facility role and needs **no grant** — the two modes are mutually exclusive and both are supported. Provision users at their employer facility to use the grant model.

```
Contract signed (ops) ──▶ SYSTEM_ADMIN creates grant:
                            grantee = teleradiologist (facility = NGH/group)
                            target  = CLINIC
                            purpose = TELERADIOLOGY_READ
                            scopes  = STUDY_READ, REPORT_READ, WORKLIST_READ, VIEWER_READ
                            expires = contract end
Grant audit row written. ──▶ Teleradiologist session:
                            home facility = group; target reads flow via §4 RLS
Critical finding → notification to CLINIC on-site staff (target facility context)
Revoke at contract end (reason) ──▶ next request → 403 + CROSS_TENANT_DENIED audit
```

### 6.2 IDN priors at read time (PAC-WF3)

- `purpose='IDN_PRIORS'`, scopes `STUDY_READ`, `REPORT_READ`, `PATIENT_READ`.
- Radiologist's home facility queries priors for a patient known to have studies at a sibling facility; the priors panel request passes through the same RLS OR-clause; audit row per retrieval.
- The XDS-I.b service (documented in `pacs-ris-architecture-deep-dive.md` §3.5 / `pacs-ris-multitenancy.md` §3.3) can be implemented on top of this same grant pattern (service account with scopes), keeping one authorization mechanism.

### 6.3 IDN enterprise scheduling (RIS-WF7)

- Schedulers at site A with `purpose='IDN_SCHEDULE_READ'`, scope `SCHEDULE_READ` can view availability at site B.
- Bookings always write to the user's home facility (`SCHEDULE_WRITE` + `rls_all` `WITH CHECK`); cross-site views never permit writes.

### 6.4 Revocation & expiry semantics

- **Immediate:** `status='REVOKED'` takes effect on the **next request** (authorization is re-evaluated per request; no cached tokens outlive a request). Long-lived viewer sessions are capped by the token/session lifetime.
- **Expiry:** `expires_at < now()` excludes the grant in the helper; a pg_cron sweep flips status to `EXPIRED` for cleanliness and reporting.
- **Suspension interplay:** if the *target* facility's subscription is `SUSPENDED`, its data is blocked at the app layer regardless of grants (RLS persists).

---

## 7. Edge Cases

| Case | Behavior |
| :--- | :--- |
| Patient merged across facilities (MPI) | Grants are facility-pair based — unaffected by patient merges. |
| Teleradiologist gains a new client | New grant row (purpose `TELERADIOLOGY_READ`); no changes to existing rows. |
| Grant revoked mid-read | Current request completes; next request denied + audited. |
| Expired grant still in UI cache | Middleware re-validates per request; UI refresh → 403 with friendly message. |
| Scopes attempted outside grant (e.g., WRITE code) | `chk`/FK + policy structure: no cross-tenant write path exists at all. |
| Grant targets a facility with no active subscription | App-layer read gate blocks; audit `CROSS_TENANT_DENIED`. |
| Cross-tenant access during DR/failover | Edge caches + home RLS still apply; grants checked against replicated metadata (RPO ≤ 60 min). |
| Grantee user deactivated | `users.active=false` blocks login; `ON DELETE CASCADE` on `user_id` removes grants if account deleted. |

---

## 8. Acceptance Criteria (maps to RBAC §9 + persona ACs)

| ID | Criterion |
| :-: | :--- |
| CTG-AC-01 | **GIVEN** a user with an ACTIVE grant (grantee=NGH, target=CLINIC, scope STUDY_READ) **WHEN** they query studies at CLINIC **THEN** authorized rows return; authorization decision < 1 s (PAC-SL-25); audit row written with source/target/grant_id (PAC-AC-P20-03, RIS-AC-P20-02, EMR-AC-P20-02). |
| CTG-AC-02 | **GIVEN** the same user **WHEN** they attempt INSERT/UPDATE/DELETE at CLINIC **THEN** the write is rejected (no cross-tenant write path) and audited. |
| CTG-AC-03 | **GIVEN** a revoked or expired grant **WHEN** the user retries **THEN** 403 + `CROSS_TENANT_DENIED` audit; **AND** the revocation took effect on the next request. |
| CTG-AC-04 | **GIVEN** no grant **WHEN** a user attempts cross-facility access **THEN** denied + audited; 0 cross-tenant PHI incidents (PAC-SL-61). |
| CTG-AC-05 | **GIVEN** grant lifecycle operations **WHEN** performed **THEN** create/revoke/expire are all audit-logged (A1); scopes contain only read codes (FK-enforced). |
| CTG-AC-06 | **GIVEN** a tenant admin of either affected facility **WHEN** viewing audit logs **THEN** relevant grant + cross-read records are visible; super admin sees all (A4). |
| CTG-AC-07 | **GIVEN** a grant to a SUSPENDED facility **WHEN** access is attempted **THEN** app-level read gate blocks it regardless of grant (A3/§6.4). |

---

## 9. Implementation Checklist

- [ ] Apply DDL (§2) + RLS (§3) as migration (after `permissions` seed exists).
- [ ] Create `app_cross_accessible_facilities()` (§4) with `SET search_path`; add `rls_cross_read` policies per table (§4 table).
- [ ] Ops endpoints: `POST /api/cross-tenant-grants`, `POST /api/cross-tenant-grants/{id}/revoke`, `GET /api/cross-tenant-grants` — **full contract, schemas, validation rules & audit events in `requrements/cross_tenant_grants_api_contract.md`** (create/revoke behind `ADMIN`, list/detail behind `TENANT_ADMIN`).
- [ ] Middleware: cache per-request facility array; emit `CROSS_TENANT_READ` / `CROSS_TENANT_DENIED` audit events (§5.2).
- [ ] pg_cron daily expiry sweep; monthly audit partition maintenance (existing pattern).
- [ ] Audit-logs UI facet for `grant_id`/`purpose` (super admin).
- [ ] Tests: CTG-AC-01…07 + RLS regression (home facility behavior unchanged; cross-tenant writes impossible).
