# Sprint 1 — Frontend Review Hardening: Auth, Session, Transport

Source: `.full-review/05-final-report.md` P0/P1 items. Branch: `v3-dev`.

## Scope

| ID | Finding | Fix |
|----|---------|-----|
| S1-A | S-H3 — no `X-CSRF-Token` → every mutation 403s | Send `X-CSRF-Token: 1` in `request()`, `useFetch`, UploadZone XHR |
| S1-B | S-H2 — logout incomplete/inconsistent | `Sidebar.handleLogout` → `AuthContext.signOut()`; signOut clears all 9 localStorage keys + `tempKey` + sessionStorage |
| S1-C | S-C2 — plaintext ws://, infinite reconnect, unguarded JSON.parse | Scheme derived from `API_URL`, capped exp. backoff + jitter, try/catch parse, Set-based subscriber registry |
| S1-D | S-C1 — JWT in thumbnail/download URLs | Frontend: drop `?token=` (HttpOnly cookie auths same-origin requests). Backend: HTTP query-param creds = share-key only (never JWT); cookie precedence over query |
| S1-E | S-C3 — refresh token in localStorage | Backend: HttpOnly `refresh_token` cookie (`path=/api/auth/refresh`) at login, rotated on refresh, blocked+deleted at logout. Frontend: never persist refresh token; refresh via cookie |
| S1-F | S-H1 — no security headers / WS unproxied | nginx: CSP + security headers, `/ws` upgrade proxy, query-stripped log format |
| S1-G | P-H6 — Worklist params dropped | `request("worklist", { query })` + page/per_page mapping + 300 ms search debounce + contract test |
| S1-H | P-C2 — chart.js in initial chunk | manualChunks `vendor-chart` + preload chunk rule + `chunkSizeWarningLimit` |

## Security posture (checklist)

- **Auth**: server-side `TokenAuth` remains the gate; CSRF header satisfies `CSRFMiddleware`; refresh credential moves to HttpOnly/SameSite=Strict cookie restricted to `/api/auth/refresh` (CSRF-safe: SameSite=Strict blocks cross-site sends).
- **AuthZ**: no client-side gating changes; backend `requires_permission` unchanged.
- **Validation**: refresh endpoint keeps Pydantic body schema; cookie is fallback. Query-token path now rejects JWTs for HTTP (share-key only) — reduces credential surface.
- **Output encoding**: no HTML rendering changes; CSP `script-src 'self'` added at the edge.
- **Secrets**: none added; `tempKey` (share credential) removed from localStorage on signOut.

## Files

Backend: `backend/api/auth.py` (query-token restriction), `backend/api/users.py` (refresh cookie), `backend/tests/test_auth_v2.py`, `backend/tests/test_token_refresh.py`, `backend/tests/test_users.py`.
Frontend: `src/helpers.ts`, `src/hooks.ts`, `src/ws.ts`, `src/auth/AuthContext.tsx`, `src/common/Sidebar.tsx`, `src/detail/ThumbnailStrip.tsx`, `src/files/UploadZone.tsx`, `src/worklist/Worklist.tsx`, `src/index.tsx` (init guard), `src/login/Login.tsx` (signIn arg), `frontend/nginx.conf`, `frontend/vite.config.js`.
Tests: `src/test/helpers.test.ts`, `src/test/AuthContext.test.tsx`, `src/test/Sidebar.test.tsx`, `src/test/ThumbnailStrip.test.tsx`, `src/test/Worklist.test.tsx`, new `src/test/ws.test.ts`.

## Risks / mitigations

- Share-viewer flow already broken (tempKey stored but never sent) — out of scope; S1-E/B remove stale storage, not the feature.
- `open()` download relies on cookie after removing `?token=` — same-origin `window.open` sends HttpOnly cookie; verified via auth.py cookie path (`users.py:31`, `auth.py:202`).
- Refresh cookie rotation: endpoint blocks old jti and issues new pair; cookie replaced per response.
