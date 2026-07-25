# ADR-017: OAuth/OIDC + RBAC for v3 Authentication and Authorization

## Status
Accepted

## Date
2026-07-25

## Context

v2.0 uses a single-shared-secret HS256 JWT with a binary `admin` boolean on the `users` table. This works for small single-tenant deployments but blocks enterprise adoption:

- **No SSO**: Each hospital user needs a separate QuantumPACS username/password. Password policies (complexity, rotation, MFA) are not enforced.
- **No role granularity**: `admin` vs. `standard` is insufficient. Radiologists need file read/write but not user management. Technologists need upload but not delete. Referring physicians need read-only.
- **No token revocation**: JWT is valid for 14 days with no way to revoke a compromised token.
- **No audit for auth events**: Login attempts, role changes, and permission grants are not systematically logged.

v3.0 must support:
1. Enterprise SSO via Azure AD, Okta, Keycloak
2. Role-based access control with per-resource permissions
3. Token revocation within minutes of a compromise
4. Backward compatibility with v2 JWT tokens during migration

## Decision

### Auth Stack

| Component | Protocol | Audience | Implementation |
|-----------|----------|----------|---------------|
| **Internal JWT** | HS256 with `jti` | Service-to-service, ingestion ↔ monolith | PyJWT (existing, enhanced) |
| **Human OIDC** | RS256 (JWKS-verified) | Azure AD, Okta, Keycloak users | `authlib` + OAuth 2.0 Authorization Code + PKCE |
| **Share Links** | HMAC key | Unauthenticated study access | Existing `shared_files` table (unchanged) |

### OAuth Flow (Authorization Code + PKCE)

```
1. Browser → GET /api/v2/oauth/login?idp=azure-ad
2. Backend generates PKCE code_verifier, stores in Redis (TTL 10 min)
3. Backend redirects to IdP authorization URL with code_challenge (S256)
4. User authenticates at IdP, grants consent
5. IdP redirects to /api/v2/oauth/callback?code=...&state=...
6. Backend exchanges code at IdP token endpoint (verifies PKCE)
7. Backend verifies id_token (RS256, JWKS, audience, issuer, nonce)
8. Backend extracts email, groups from id_token claims
9. Backend resolves tenant from email domain or user's existing tenant
10. Backend finds user or JIT-provisions them in the tenant database
11. Backend issues QuantumPACS JWT (HS256) with role + permissions + tenant
12. Backend sets httpOnly cookie + returns JWT in response body
```

### RBAC Model

Replacing the `users.admin` boolean:

- **Roles table**: `id UUID PK`, `name TEXT`, `slug TEXT UNIQUE`, `permissions JSONB`, `built_in BOOL`, `tenant_id TEXT`
- **Permissions** are per-resource, per-action:
  ```
  {
    "files": ["read", "write", "delete"],
    "patients": ["read", "write"],
    "studies": ["read"],
    "users": ["read", "write", "delete", "admin"],
    "replicas": ["read", "write", "delete"],
    "logs": ["read"],
    "tenants": ["read", "write", "admin"],
    "roles": ["read", "write", "delete"]
  }
  ```

### Default Roles

| Role | Permissions | Notes |
|------|-------------|-------|
| `super_admin` | All resources: all actions | Can manage tenants and all tenant data |
| `tenant_admin` | All resources within tenant: all actions | Cannot access other tenants or registry |
| `radiologist` | files/patients/studies: read + write; logs: read | Can view, annotate, edit studies |
| `technologist` | files/patients/studies: read + write | Can upload, cannot delete, cannot manage users |
| `referring_physician` | files/patients/studies: read | View-only access |
| `auditor` | logs: read; files: read (metadata only) | Read-only audit trail access |

### Token Changes

| v2 Claim | v3 Claim | Change |
|----------|----------|--------|
| `user_id` | `sub` | Kept (aliased) |
| `admin` | (removed) | Replaced by `role` + `permissions` |
| — | `role` | New — role slug |
| — | `permissions` | New — permission map |
| — | `tenant` | New — tenant slug |
| — | `jti` | New — UUID token ID (for revocation) |

### Token Lifecycle

| Action | v2 | v3 |
|--------|----|----|
| Access token TTL | 14 days | 1 hour |
| Refresh token | None | 14 days (rotate on use) |
| Revocation | None (must wait 14 days) | Add `jti` to Redis blocklist (TTL = token expiry) |
| Blacklist on password change | None | Blocklist all user's tokens |
| Blacklist on role change | None | Blocklist all user's tokens |

## Consequences

### Positive

- **Enterprise SSO** — Hospitals can use existing identity infrastructure; no per-user account management.
- **Fine-grained access** — Role-permission model supports radiologist, technologist, referring physician, and auditor use cases without over-provisioning.
- **Token revocation** — Compromised tokens can be blocked within seconds.
- **Backward compatibility** — v2 JWT tokens (without `jti`, `role`, `permissions`) are still accepted during transition, treated as `admin` according to the `admin` boolean (which remains in the DB).

### Negative

- **OAuth adds latency** — The initial login flow involves 2 redirects and a token exchange. After that, QuantumPACS JWTs are issued for 1 hour, so per-request latency is unchanged. The OAuth flow only runs on initial login (or after token expiry).
- **OIDC provider dependency** — If the IdP is down during login, users cannot authenticate. They can still use existing QuantumPACS JWTs (up to 1 hour TTL). For full offline resilience, local JWT login remains as fallback.
- **JIT provisioning risk** — Auto-creating users on first login could create stale accounts if the IdP sends unexpected claims. Mitigation: audit log all JIT creations, with a super-admin approval mode (disabled by default).

## References

- ADR-003: JWT Authentication
- ADR-008: Security Architecture
- PRD-v3.md §3.5 — Authentication & Authorization
- IMPLEMENTATION_PLAN-v3.md Phase 2 — Auth & Tenancy
- "OAuth 2.0 for Browser-Based Applications" — IETF RFC 8252