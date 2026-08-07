# ADR-005: Cross-Tenant Grants for Teleradiology & IDN Access

## Status
Accepted

## Date
2026-08-04

## Context
The platform's cross-tenant value (ADR-001) — teleradiologists reading for multiple client facilities, and IDNs accessing priors across facilities — requires deliberate, **policy-gated** access across facility boundaries. RLS (ADR-001) denies all cross-tenant reads by default; we need an explicit, auditable, time-boxed exception mechanism that a SYSTEM_ADMIN controls, without creating a blanket bypass.

## Decision
Introduce a dedicated **`cross_tenant_grants`** table (DDL + RLS + audit policy in `requrements/cross_tenant_grants_design.md`) plus an ops API:

- **Model:** an explicit grant row per (source facility → target facility, purpose scope, grantee role/user, expiry). No grant = no cross-tenant read; RLS remains the default deny.
- **Purpose-driven scopes:** e.g., `TELERADIOLOGY_READ` (nighthawk/telerad reads), `IDN_PRIORS` (prior study access within a health system), `SCHEDULING_REFERRAL` — each maps to a limited permission surface.
- **Authorization helper:** a database function/API layer that checks active, non-expired grants before any cross-tenant query; authorization decision < 1 s and 100% audited (PAC-SL-25).
- **Ops API contract:** `POST /api/cross-tenant-grants`, `GET` (list/filter), `DELETE`/`revoke` — with validation rules (V1–V11: source ≠ target, no overlapping duplicate, purpose required, expiry validation…) and audit events (`cross_tenant.grant.created`, `cross_tenant.denied`, …) — `requrements/cross_tenant_grants_api_contract.md`.
- **UI:** SYSTEM_ADMIN console (list/create/revoke) consistent with tenants/roles pages — `docs/specs/cross-tenant-grants_design.md`.
- **Audit:** every granted access and every attempted-but-denied cross-tenant read is logged with source + target facility context (PAC-AC-P20-03, PAC-SL-60/61).

## Alternatives Considered

### Single platform-wide `BYPASSRLS` ops role for everything
- Pros: trivial to implement
- Cons: not time-boxed, not scoped, not per-purpose; every access becomes an audit review
- Rejected: an all-or-nothing bypass contradicts the "explicit grant" requirement

### Duplicate/denormalized data copies per tenant
- Pros: reads need no cross-tenant path
- Cons: sync/reconciliation burden; staleness; violates single-source-of-truth (MPI, priors)
- Rejected: shared-schema makes read-across natural (ADR-001)

### Schema-per-tenant + federation layer
- Pros: clean physical isolation
- Cons: cross-schema federation is heavy; breaks the shared-schema default
- Rejected: reserved as escape hatch only (ADR-001)

## Consequences
- Teleradiology (v1.1) and IDN priors work without VPNs or per-facility logins; every session is a normal OAuth2 session (PAC-AC-P03-01).
- Cross-tenant read attempts without a grant are denied **and logged** — a security observable, not a silent fail.
- Grants are time-boxed and revocable; revocation is immediately effective (no token to expire — enforcement is per-request).
- The G6 exit gate includes denial + audit verification (`cross_tenant.denied` event evidence in the go-live checklist).
- Feature ships in v1.1 per the release plan; the denial path is verified from Sprint 1 (audit) / Sprint 6 (grants).

## Sources
`requrements/cross_tenant_grants_design.md` (DDL + RLS + audit) · `requrements/cross_tenant_grants_api_contract.md` (endpoints, V1–V11, events) · `docs/specs/cross-tenant-grants_design.md` (UI) · `requrements/RBAC_matrix_spec.md` §6 · `requrements/PACS/06_acceptance_criteria.md` PAC-AC-P03-01/03, P20-03 · PAC-SL-25/60/61
