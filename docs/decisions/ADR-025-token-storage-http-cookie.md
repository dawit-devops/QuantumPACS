# ADR-025: Token Storage — HttpOnly Cookies + Headers (No localStorage)

## Status
Accepted

## Date
2026-08-02

## Context
Frontend authentication must survive page reloads without a login prompt.
Storing JWTs in `localStorage` exposes them to any XSS (a single injected
script can exfiltrate every session). Query-string storage is forbidden
(see ADR-024). The refresh token must be even more restricted than the
access token.

## Decision

- **Access token**: returned in the login response body AND set as an HttpOnly
  cookie `token` (`Secure`, `SameSite=strict`, `path=/api`). API requests
  authenticate via `Authorization: Bearer` / `X-Auth-Pacs` header or the
  cookie; the auth middleware accepts both.
- **Refresh token**: travels **only** as an HttpOnly cookie scoped to
  `/api/auth/refresh` — never in localStorage, the body, or URLs.
- **Frontend**: `apiFetch` (and the typed api modules) attach the header from
  the cookie-handshake or rely on the cookie; `logout` deletes both cookies.
- **XSS blast radius**: a forged `localStorage` entry cannot grant API access —
  the server ignores client-side storage entirely (permission-contract tests
  assert a forged admin flag still gets 403).

## Alternatives Considered

- localStorage + Bearer header: simpler but XSS-readable.
- In-memory only: lost on reload, forces re-login — poor UX for a PACS reading
  room.

## Consequences

- XSS cannot steal session tokens; CSRF is mitigated by `SameSite=strict` and
  header checks on state-changing requests.
- Logout must clear the cookie server-side (already implemented in
  `backend/api/users.py`).
- Cookie path scoping (`/api`) keeps the token out of static-asset requests.
