# ADR-004: IUA/OAuth2 Identity + Facility-Scoped RBAC

## Status
Accepted

## Date
2026-08-04

## Context
Three product surfaces (PACS, RIS, EMR) share one platform with 20+ human personas (radiologist, technologist, PACS admin, tenant admin, super admin…), institutional tenants, and machine actors (modalities, HL7/FHIR integrations). We need: single identity across surfaces, fine-grained permissions per facility, auditable access, and web/DICOMweb security that EHRs and zero-footprint viewers can interoperate with.

## Decision
Adopt **IHE IUA / OAuth2 (OIDC) with a facility-scoped RBAC model**:

- **Identity:** OIDC/OAuth2 via `users` (bcrypt password hash, MFA flag) + optional SSO/OIDC/SAML identity providers (M13). Access tokens carry the persona's facility scope.
- **Authorization:** canonical RBAC — `roles` ↔ `permissions` (role_permissions) with **facility-scoped grants** (`user_roles`: user × role × facility — a user can be a Radiologist at facility A and Technologist at facility B). Token version bump invalidates tokens on permission change (PAC-AC-P19-02).
- **Tenant middleware:** every request resolves the tenant, validates it against the JWT, and executes `SET app.facility_id = :id` (RLS enforcement per ADR-001); unset tenant IDs are rejected for clinical routes.
- **DICOMweb/API security:** all DICOMweb routes behind the IUA/OAuth2 token gate; no PHI in URLs (UID-based links); TLS 1.2+, AES-256 at rest.
- **Cross-tenant access** is not a bypass — it requires an explicit grant via `cross_tenant_grants` (ADR-005), audit-logged on every access.
- The canonical role→permission matrix and endpoint→permission map are implementable specs in `requrements/RBAC_matrix_spec.md` (with idempotent seeding SQL).

## Alternatives Considered

### Shared login with app-layer role checks
- Pros: simplest; familiar
- Cons: no per-facility scoping; permission checks scattered in code; no standard EHR trust (no IUA); hard to audit
- Rejected: cannot meet HIPAA audit or cross-facility requirements

### Keycloak-style external IdP only (no internal model)
- Pros: mature IdP features (SSO, MFA, federation)
- Cons: still needs the facility-scoped role/tenant model; adds deployment coupling for every tenant
- Rejected as sole model: external IdP is supported via OIDC/SAML federation; internal model remains source of truth

### Per-tenant separate identity stores
- Pros: isolation
- Cons: breaks teleradiology cross-tenant sessions, duplicate accounts, ops burden
- Rejected: single identity across the platform is a core requirement

## Consequences
- One `users` table spans all surfaces; facility scoping happens in `user_roles`, enforced by RLS + middleware — matching ADR-001.
- Token-version bump on role change gives immediate revocation semantics (PAC-AC-P19-02).
- **Known gap to close in production:** `users.password_hash` is readable by any authenticated role today — restrict via column-level GRANTs to the auth service (schema §5.1 note; sprint1 hardening).
- IUA/OAuth2 enables SMART-on-FHIR launch (v2.0) and teleradiology token sessions (v1.1) without rework.
- RBAC seeding, endpoint→permission map, and cross-tenant policy are directly implementable from `RBAC_matrix_spec.md` §4–§6.

## Sources
`docs/specs/auth_design.md` · `docs/specs/roles_design.md` · `requrements/RBAC_matrix_spec.md` · `requrements/cross_tenant_grants_design.md` · `research/pacs-ris-viewer-integration-spec.md` §8 (IUA) · `research/pacs-ris-schema.sql` §2, §5.1 · sprint1 (RBAC seed, S1-05/22)
