# ADR-003: JWT Token Authentication

## Status
Accepted

## Date
2026-07-22

## Context
The original authentication system used a custom token format with mixed responsibilities — token creation spread across multiple modules, no centralized verification, and inconsistent error handling. Requirements:

- Stateless authentication for horizontal scaling
- Token expiry and refresh support
- Admin vs. regular user role distinction
- Backward compatibility with existing client tokens
- Secure by default (no hardcoded fallback secrets in production)

## Decision
Use JWT (HS256) tokens with a centralized `api/tokens.py` module for all create/verify operations.

Key design:
- `create_token(user, expire=)` produces signed JWTs with `id`, `admin`, and `exp` claims
- `verify_token(token)` decodes and validates in one call
- Token secret sourced from `config['secret']` (env `SECRET` > config YAML > db_password fallback)
- Default 14-day expiry with caller-configurable duration
- All endpoints authenticate via Starlette `AuthenticationMiddleware` with `TokenAuth` backend
- Custom `X-Auth-Pacs` header for token transport (in addition to standard Authorization header)

## Alternatives Considered

### Session-based auth (server-side sessions)
- Pros: Can revoke individual sessions, no token size limits
- Cons: Requires Redis or DB for session store; stateful; harder to scale
- Rejected: Stateless JWT better aligns with containerized deployment

### OAuth2 / OIDC
- Pros: Industry standard, supports third-party identity providers
- Cons: Requires external identity provider; adds complexity for a single-app system
- Rejected: Overkill for internal PACS authentication; can add later if SSO needed

## Consequences
- No session storage needed — scales horizontally trivially
- Token revocation requires a blocklist (not yet implemented — acceptable for current deployment)
- JWT payload is visible (not encrypted) — never store PHI in the token
- Migration to RS256/ES256 possible if key rotation becomes a requirement
