# ADR-008: Security Architecture

## Status
Accepted

## Date
2026-07-22

## Context
OpenPACS handles medical imaging data (PHI under HIPAA). The original security model had several gaps: default passwords in config, no rate limiting, no audit trail for file access, and permissive CORS. Requirements:

- Authentication required for all API endpoints
- Role-based access (admin vs. regular user)
- Audit trail for file changes
- Secure defaults (no hardcoded secrets in production)
- CORS restricted appropriately
- Protection against common web vulnerabilities

## Decision
Multi-layer security architecture:

**Authentication layer:**
- JWT tokens (HS256) with configurable expiry (default 14 days)
- `Starlette AuthenticationMiddleware` on every request
- Custom `TokenAuth` backend extracts token from `X-Auth-Pacs` header
- `api/auth.py` — login endpoint with bcrypt password verification
- `api/permissions.py` — admin-only endpoint guard

**Transport security:**
- All API responses include CORS headers
- Tokens transmitted via custom header (never in URL query strings)
- Caddy reverse proxy with automatic HTTPS (in Docker deployment)

**Data security:**
- Passwords hashed with bcrypt (not MD5/SHA1)
- File integrity verified via SHA-256 on every upload/download
- Configurable secret via environment variable (`SECRET`) — never commit secrets
- Database passwords configurable via environment

**Audit:**
- `file_changes` table records all file modifications with user attribution
- Structured logging with request-level tracing
- Logging of 4xx/5xx responses with timing

## Alternatives Considered

### OAuth2 with external IdP
- Pros: Industry standard, SSO support
- Cons: Requires external infrastructure; adds latency for every request
- Rejected: Internal JWT is sufficient; can add OAuth2 later for enterprise SSO

### HTTPS-only with client certificates
- Pros: Strong mutual authentication
- Cons: Certificate management overhead; poor UX for web UI
- Rejected: Token-based auth is more practical for web + API clients

## Consequences
- All endpoints are authenticated by default (no anonymous access)
- Admin endpoints explicitly gated via `requires_admin` decorator
- Audit trail provides non-repudiation for file operations
- CORS is permissive (`*`) currently — should be tightened to specific origins in production
- Rate limiting not yet implemented — should be added before public deployment
