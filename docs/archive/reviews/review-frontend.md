# Frontend Codebase Review — QuantumPACS

- **Reviewer role**: Frontend specialist (React 19 / Vite / Ant Design v6 / Cornerstone3D)
- **Skill applied**: `frontend-react-best-practices` (bundle, re-render, hooks, composition rules)
- **Scope**: `frontend/src/**` — auth, API client, WebSocket, viewer, worklist/technologist/radiologist screens
- **Date**: 2026-08-03
- **Verdict**: Healthy. The frontend is well-structured, deliberately commented (why-not-what), and test-backed (Vitest + RTL + Playwright E2E). Findings below are mostly hardening items, not blockers.

---

## 1. Strengths

| Area | Observation |
|---|---|
| Auth token strategy | Access token in `localStorage`, refresh token in HttpOnly cookie (`src/api/session.ts`), single-flight refresh (`refreshPromise`), 25-min proactive refresh timer vs 1h token. Good XSS posture for a PACS. |
| WebSocket | Module-level singleton socket with shared listener `Set`, capped exponential backoff + jitter, deliberate `disconnect()` semantics (`src/ws.ts`). No connection-per-component leak. |
| Data fetching | `useFetch` aborts prior in-flight request on re-exec, swallows `AbortError`, retries once after refresh on 401 (`src/api/useFetch.ts`). |
| Concurrency | `mapLimit` bounds bulk UI operations to N in-flight requests (`src/helpers.ts:67`). |
| Composition | `AuthProvider` lifts auth state into context with memoized value; `PermissionRoute`/`RequirePermission` gate UI. |
| Error UX | `ErrorBoundary` at app level, `PageState`, `EmptyState`, skeleton loading (300 ms `LOADING_DELAY`). |
| Testing | ~40 unit/component test files plus Playwright specs for login, RBAC, viewer, tenant provisioning, SW, share links, mobile viewport. |

---

## 2. Findings

### F1 (Medium) — Identity state is restored from `localStorage` on reload without token validation
`src/auth/AuthContext.tsx:53-71` rebuilds `user` from `localStorage` keys (`userId`, `admin`, `role`, `permissions`) on every page load. If the access token is expired/revoked, `isAuthenticated` is still `true` until the first API call 401s and the app redirects to `/login`.
- **Scenario**: A user is deactivated server-side; their open tab keeps rendering the full app until the next 401/refresh failure (~25 min max with the refresh timer).
- **Recommendation**: Validate on boot (e.g., a `GET /api/v2/auth/me` check in `AuthProvider` before rendering children) or derive `isAuthenticated` from token presence + expiry check.

### F2 (Medium) — `useFetch` never aborts on unmount
`src/api/useFetch.ts:17` keeps a `controller` ref, but it is only aborted when the *next* `exec` runs. Unmounting a screen with an in-flight request lets the fetch complete and call `setData`/`setError` on an unmounted component (harmless in React 19, but wasted bandwidth + potential state writes after teardown).
- **Recommendation**: `useEffect(() => () => controller.current?.abort(), [])`.

### F3 (Low) — `useFetch` mutates the caller's `options` object and reassigns `url` during render
`src/api/useFetch.ts:19-21,42-49` writes `options.headers = new Headers(...)` and rewrites `url` each render/exec. If the same `options` object is shared by two hooks it is silently mutated; `url` prefixing in the render body is also a side effect (works, but is a footgun if `url` were ever used in a memo dependency).
- **Recommendation**: Build `headers`/`signal` into a local object inside `exec`; prefix `url` with `useMemo`.

### F4 (Low) — `signIn` never persists `tenant_name` while `signOut` clears it
`src/auth/AuthContext.tsx:104-111` writes `tenant_id` but not `tenant_name`; `signOut` removes both (`:86`). After a fresh login the tenant selector name falls back to the slug (`:49`), so it works — but the asymmetry is confusing and the name shown before the tenant picker is resolved is the slug.
- **Recommendation**: Persist `tenant_name` in `signIn` when `userData.tenant_id` is set, or drop the `tenant_name` key entirely and always derive it from the API.

### F5 (Low) — `startRefreshTimer` is a single global interval that keeps running while the tab is hidden
`src/api/session.ts:26-47`. Every 25 min a refresh fires even in background tabs; not a correctness issue, but a `document.visibilitychange` gate would avoid wasted network + backend token churn on idle tabs.

### F6 (Info) — Access token in `localStorage` is XSS-readable
`src/api/session.ts:16`. The refresh token is correctly kept HttpOnly, and the access token is short-lived (1h), so the exposure window is bounded. For a PHI-bearing PACS this is the main residual client-side risk; a stricter posture would keep the access token in memory (module variable) and use the HttpOnly cookie path for the first request after reload.

---

## 3. Positive patterns worth keeping

- Functional `useCallback` setters and memoized context value (`AuthContext.tsx:122-141`) — no avoidable re-renders.
- Named cleanup in effects; `useEffect` count is low across the biggest screens (ExamConsole 3, ReportEditor 4, Detail 2).
- No barrel imports of Ant Design; icons imported individually; manual chunk splitting per CLAUDE.md.
- `parseParams` uses `URLSearchParams` (comment Q-21 documents the prior `%20` bug) — good regression documentation style.

---

## 4. Recommendations (priority order)

1. **F1** — boot-time auth validation (or `me` endpoint) so deactivated/expired sessions can't render the app shell.
2. **F2** — abort in-flight fetch on unmount.
3. **F3/F4** — tidy `useFetch` internals and tenant-name persistence (low effort).
4. Re-evaluate **F6** if the app ever runs third-party scripts or a rich-text surface (keep the CSP strict).

*Reviewed with skill: `frontend-react-best-practices` — rules consulted: rerender-*, hooks-*, client-*, composition-*, bundle-*.*
