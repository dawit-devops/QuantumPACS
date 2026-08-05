# Phase 1: Code Quality & Architecture Review

## Code Quality Findings (1A)

### Critical
- **C-1. Dead inline-edit feature** — `src/detail/EditableTable.tsx:17` — `editableFields: string[] = []` never populated; `toggleEdit` always false → cells never editable; `editable: true` column flag never read. Enable or delete.

### High
- **Q-1. CornerstoneElement is a 1,122-line god component** (`src/detail/CornerstoneElement.tsx`) — 29 bound methods, mixes engine lifecycle, tools, keyboard (100+ line switch at 347-454), WS annotation sync (562-645), camera math, polling, mobile toolbar. Extract ViewportTools/AnnotationSync/ViewportCamera.
- **Q-2. Hl7Dashboard: three dashboards in one** (`src/hl7/Hl7Dashboard.tsx`, 660 lines) — 17 state vars, 6 near-identical fetch blocks with `catch {}`. Split into 3 tabs.
- **Q-3. Fetch layer triplicated** — `helpers.ts:31-48,119-174`, `hooks.ts:12-29,75-109` (verbatim copy), `dicomweb/dicomweb.ts:4-11` (third copy, no 401 handling). Already drifted (helpers handles tempKey/shareKeyError; hooks does not).
- **Q-4. `document.title` side effect in render, ×15 files** — breaks React 19 concurrent rendering guarantees. Use `useDocumentTitle` hook.
- **Q-5. `any` overuse: ~406 occurrences** — 315 `: any`, 39 `any[]`, 28 `(props: any)`, 19 `as any`, 5 `Promise<any>`. Root cause: `handleResponse(): Promise<any>` / `request(): Promise<any>`.

### Medium
- **Q-6. Worklist.tsx 676 lines, 15 state vars** — extract CalendarView/BatchActions.
- **Q-7. Double filtering** — Worklist.tsx:281-299 client-side filter on current server page + server query already passes status → wrong tab badges.
- **Q-8. `let [` vs `const [` — 186 `let` state bindings** (none reassigned).
- **Q-9. `withRouter` HOC + 28 `(props: any)` components** — migrate to useParams/useNavigate.
- **Q-10. hooks.ts near-dead** — `useFetch` 1 consumer (Login), `useFormInput`/`usePrevious` 0 consumers.
- **Q-11. Error-shape fragility** — helpers.ts:148-172 matches `error.error === 401` by shape; `throw Error(error.error || ...)` renders `"[object Object]"` for 400 bodies, bare `"500"` for statuses.
- **Q-12. `checkReady` polling loop** (CornerstoneElement.tsx:716-725) — 100ms chained setTimeout, no termination, no unmount cancellation.
- **Q-13. Detail.tsx `(window as any).ctinit` global + `setTimeout(() => setKey(2), 500)` remount hack** (122-128).
- **Q-14. WS: infinite reconnect loop, no backoff, single-subscriber design** (ws.ts:19-21, 36-42), hardcoded `ws://` (line 12), unguarded JSON.parse.
- **Q-15. NotificationBell unhandled rejections** — markRead/markAllRead/dismiss/dismissAll (78-105) no try/catch.
- **Q-16. Hl7Dashboard silent config-load failure enables destructive overwrite** — fetchConfig `catch {}` (96-107); Save overwrites server config with defaults.
- **Q-17. Batch ops report success when everything failed** — Worklist.tsx:235-267 `Promise.all(ids.map(...catch(() => {})))` then unconditional `message.success`.
- **Q-18. Empty `catch {}` ×14** — notable: Logs.tsx:245,285 (live tail dies silently), FhirMonitoring.tsx:65, Hl7Dashboard 90/103/114, Files.tsx:204 (QIDO failure hidden), Sidebar.tsx:109 (logout POST failure silent).
- **Q-19. `request()` can resolve `undefined`** (helpers.ts:170-173, error.code===20 path) → downstream `res.data` crashes.
- **Q-20. 7 eslint-disable missing-deps** — Files.tsx:146,154 depends on non-reactive `window.location.search`.
- **Q-21. `parseParams` reinvents URLSearchParams, no URL-decode** (helpers.ts:188-197) — `%20` leaks into searches.

## Architecture Findings (1B)

### High
- **A-1. API error contract broken end-to-end** — backend 400 `{'error': msg}` → handleResponse throws `{error: json}` → `Error(error.error||...)` → `"[object Object]"`; 403/404/500 → `Error(status)` → `"500"`. Every `message.error(e.message)` shows garbage. Fix: `ApiError` class with status + message; normalize in handleResponse once.
- **A-2. No typed API layer** — ~200 stringly-typed URL literals, `Promise<any>` transport, 300+ `any` despite `strict: true`. Model on the one good example: `dicomweb.ts` (Study/Series/Instance interfaces + mappers).
- **A-3. Duplicated transport/auth infrastructure already drifted** — helpers.ts vs hooks.ts; hooks' useFetch missing share-link semantics.

### Medium
- **A-4. `withRouter` fabricates legacy history API on React Router v7** — spread of location into history (withRouter.tsx:15-20), inconsistent composition order (`withRouter(withSidebar(X))` vs `withSidebar(withRouter(Detail))`), 16 consumers.
- **A-5. WS layer design** — single-slot module globals (only CornerstoneElement can subscribe), no backoff/cap, `ws://` hardcoded, vite proxy `/ws` config dead (clients hit `/api/ws`; `/api` proxy lacks `ws: true`), NotificationBell polls 30s despite backend LISTEN/NOTIFY infra.
- **A-6. Auth dual-write, divergent logout** — AuthContext.signOut removes 9 keys; Sidebar.handleLogout removes different subset (leaves username/role/permissions/tenant_id) → stale identity in localStorage.
- **A-7. Routing table** — 19 repeated `<ProtectedRoute>` wrappers, no `location.state.from` (post-login redirect lost), dead `/logout` route (Sidebar links to it; matches `*` → NotFound).
- **A-8. Render-phase side effects** — `document.title` ×15 pages; index.tsx:51-56 localStorage.setItem during render.
- **A-9. Response-envelope inconsistency** — backend `{data, meta, links}` (paginated) vs flat `{data, total, page, per_page}` (worklist); frontend pages each re-parse differently (Worklist res.total, Tenants res.data, Logs cursor).

### Low
- **A-10. request() returns undefined after failed refresh** → `.then` TypeError.
- **A-11. fetchWithRetry retries all 5xx up to 4 times incl. POST/DELETE** — mutation retry risk; off-by-one (final unconditional fetch).
- **A-12. X-Auth-Pacs custom header + localStorage tokens**; two auth schemes in play (Bearer for FHIR external clients).
- **A-13. Client permission gating trusts forgeable localStorage** — OK only if backend enforces all permissions.
- **A-14. Vendor chunking incomplete** — chart.js (only /metrics) ships in initial bundle.
- **A-15. Duplicated error reporting** — message.error + PageState error simultaneously (Worklist:96-100, Tenants:78-82).
- **A-16. Docs/convention drift** — CLAUDE.md says CSS Modules; codebase uses plain .css + inline styles with hardcoded hex.
- **A-17. navigator.ts global bridge** couples request() to router via hidden global.

## Strengths (verified)
- Feature-per-directory structure consistent across 19 dirs; no circular imports (verified acyclic)
- All 20 routes lazy-loaded; Cornerstone3D isolated behind one lazy boundary; vendor chunking for react/antd/cornerstone
- PageState/EmptyState/ErrorDisplay/ErrorBoundary shared primitives; 17/20 pages use PageState
- AuthContext/ThemeProvider well-typed with useMemo/useCallback
- Accessibility: skip-link, role=main, aria-live, aria-current
- dicomweb.ts proves the typed-API pattern works in this codebase

## Critical Issues for Phase 2 Context
- Error contract broken (A-1/Q-11): users see `"[object Object]"` / bare status codes — affects every page's error UX
- WS: infinite reconnect loop with no backoff (Q-14/A-5) — token re-fetch loop load + XSS-relevant localStorage tokens (A-12)
- X-Auth-Pacs header + localStorage tokens (A-12) — security review should assess XSS exposure
- unguarded `JSON.parse(event.data)` in ws.ts (Q-14) — malformed frame crashes handler
- Batch mutation retry on 5xx (A-11) — idempotency concern
- Files.tsx stale-closure pagination + non-reactive URL dep (Q-20)
- tempKey in localStorage never cleaned up; share tokens in URLs (helpers.ts:176-186 download helper)
