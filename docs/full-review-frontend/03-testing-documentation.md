# Phase 3: Testing & Documentation Review

## Test Coverage Findings (3A)

**Overall**: 243 test cases across 34 files (3.9k LOC vs 15.7k LOC source). Healthy quantity, uneven quality: ~40% of source files untested, including every security-critical and complex module (ws.ts, NotificationBell, Detail, Share, helpers retry/refresh, Worklist wiring, Files pagination). Coverage thresholds configured (vite.config.js:64-75) but non-functional (`@vitest/coverage-v8` not installed); CI runs bare `vitest run` without coverage or e2e.

### Critical
- **T-C1. No test asserts X-CSRF-Token; logout integration untested** — helpers.test.ts:140-154 asserts X-Auth-Pacs only; Sidebar.test.tsx never clicks Logout → the broken `handleLogout` call site (never calls signOut, leaves 5 keys incl. tempKey) is invisible. Test recommendations with code in 3A output.
- **T-C2. Worklist test passes while filter/pagination params never reach server** — `Worklist.test.tsx:144-148` asserts `toHaveBeenCalledWith("worklist", expect.any(Object))` → trivially passes; no test asserts URL/params. Fix: contract test asserting `{ query: { status, page, limit } }`.

### High
- **T-H1. Hl7Dashboard config-load failure → destructive overwrite untested** — 9 tests, success path only; mockRequest always resolves config. Need: reject config → Save disabled + error surfaced.
- **T-H2. Files stale-closure pagination untested** — duplicate mount fetch (144-155), stale closure (168-210) invisible to suite; FilesQido.test.tsx covers QIDO search only.
- **T-H3. CornerstoneElement tested as inert shell** — @cornerstonejs mocks replace real engines → checkReady never-cancelled loop (716-725), missing disableElement/removeViewports on unmount, listener leaks untestable. Detail remount hack (122-128) has zero tests. Need: unmount-cleanup test asserting `disableElement` called + `vi.getTimerCount() === 0`; Detail single-fetch test advancing past the 500ms hack.
- **T-H4. ws.ts has zero tests** — reconnect loop, single-subscriber, unguarded JSON.parse, silent send when unconnected all untested. Need: `vi.stubGlobal("WebSocket", ...)` contract test (malformed frame → no crash, no reconnect storm).
- **T-H5. Retry/backoff, 401-refresh dedup, malformed JSON untested** — `vi.useFakeTimers` used nowhere; thundering-herd race untested (existing 401 test is single-caller happy path); invalid JSON on 200 propagates opaque error. Need: fake-timer backoff test (4 attempts), concurrent-401s → single refresh test.

### Medium
- **T-M1. `useFetch` — the most complex hook — untested and mocked away everywhere** — every component test mocks `../hooks`; real behavior (abort-on-re-exec hooks.ts:52-54, LOADING_DELAY, 401-refresh retry 88-98) is dead code from suite's perspective.
- **T-M2. NotificationBell error paths untested** — no test file exists; optimistic updates on failed markRead/dismiss assert nothing.
- **T-M3. Permission-gating backend contract not locked** — AuthContext.test.tsx:145-177 tests forged-localStorage UI behavior only; no regression test asserting forged admin=true → 403 at API layer.
- **T-M4. Empty states / permission-denied UI / network-error UI rarely asserted** — only FilesQido (3 error tests) and Metrics exercise failure render paths.

### Low
- **T-L1. Test-quality issues** — implementation-detail selectors (Worklist.test.tsx:200 `querySelectorAll(".anticon-edit")`), App.test.tsx duplicates Login.test.tsx verbatim, Pwa.test.ts regex-greps vite.config.js, dangerous global fetch fallback in setup.ts:57-65 (phantom `{ok:true}` success), matchMedia stub hardcodes `min-width: 992` (all tests "desktop").
- **T-L2. Pyramid is a two-layer sandwich** — unit (243 jsdom) + shallow e2e (11 Playwright specs, 433 LOC, navigation/URL-level only); e2e **not run in CI** (no Playwright job); `test:fast`/`test:slow` split unused.
- **T-L3. Coverage configured but non-functional** — thresholds at vite.config.js:64-75 but `@vitest/coverage-v8` missing → `npm run test:coverage` fails; CI enforces nothing.
- **T-L4. Maintainability signals** — no fake timers (120s testTimeout masks hangs), localStorage cleared in only 4/34 files, `renderWithAuth` copy-pasted into ~10 files (extract to src/test/utils.tsx), two diverging fetchWithRetry copies.

### What's Good
- Auth core solid: AuthContext.test.tsx (12 behavioral tests: signIn/signOut storage, RequirePermission both ways, admin bypass, ProtectedRoute redirect)
- helpers.test.ts right transport-level pattern (real fetch stubs, 401→refresh→retry happy path)
- Admin CRUD pages each have 4-10 behavior-first tests; FilesQido covers QIDO→v2 fallback incl. network-error path; ErrorBoundary properly behavioral; Worklist create-entry full UI flow
- No snapshots; assertions mostly behavioral; `vi.hoisted` isolation; deterministic in practice

## Documentation Findings (3B)

### Critical
- **D-C1. No API contract documentation for frontend consumers** — `backend/static/openapi.json` hand-maintained, covers 13 of 92+ routes, versioned 2.0.0, referenced nowhere; ~80 endpoints via ~200 stringly-typed URLs undocumented; error envelope `{"error": msg}` only in response.py docstring + REST_API_REVIEW.md R-08 (Open) → explains why `[object Object]` bug survived. Fix: auto-generate OpenAPI from Pydantic schemas, publish "API Contract for Frontend" (envelope, auth headers, ws_token flow).
- **D-C2. Security documentation contradicts real deployment** — README claims "CSP + security headers (Caddy) ✅" + Caddy diagram, but frontend/Dockerfile ships nginx:1.27-alpine with nginx.conf that has **no CSP/XFO/security headers**; root Caddyfile CSP unused by the Docker path. Fix: headers in nginx.conf or document Caddy as mandatory edge; update README + SECURITY_AUDIT.md.

### High
- **D-H1. CLAUDE.md conventions drift from implementation** — "CSS Modules" false (17 plain .css, zero *.module.css); "AntD v5" vs actual ^6.5.1 (echoed in ADR-006); ES notes stale (docker-compose now defines elasticsearch 9.4.4, xpack off; "cannot be pulled" may be stale); README "default credentials admin/pa55w0rd" conflicts with random-password `manage db init`.
- **D-H2. ADR-006 stale + frontend decision gaps** — says AntD v5 (v6 actual), claims chunk splitting reduces initial load (but vendor-cornerstone lands in initial bundle), omits React.lazy strategy; **no ADR covers**: WebSocket design (ws_token handshake, reconnect, ws:// scheme), share-link/tempKey auth, PWA strategy, localStorage JWT storage (ADR-003 documents header only), withRouter HOC, bundle budget.
- **D-H3. `frontend/docs/*` are AI agent personas, not project docs** — frontend-developer.md describes Next.js 15/Tailwind/Zustand (none used); nothing documents how to add a page/route/API call in this codebase; the known-good typed pattern (dicomweb.ts) never identified as the pattern.
- **D-H4. IMPLEMENTATION_PLAN-v3 Phase 6 status stale** — Phases 1-3 have ✅ as-built markers; Phase 6 items (F6.1a/b/c, F6.3 OAuth SSO) shipped with boxes unchecked.

### Medium
- **D-M1. Inline *why*-comments convention unmet** — only 13/105 files have any comment; zero in helpers.ts (230 lines: refresh timer, base64 JWT expiry, silent catch {}), hooks.ts, ws.ts, CornerstoneElement.tsx (1,122 lines), dicomweb.ts. No stale comments — just absence.
- **D-M2. README inaccuracies** — `frontend/test/` vs actual `frontend/src/test/`; "30 E2E tests" vs 42+ across 12 specs; Quick Start `docker compose up -d` only runs elasticsearch+postgres (backend/frontend not in compose); real dev workflow (scripts/dev.sh, systemd) undocumented in README; Caddy diagram vs nginx reality.
- **D-M3. `docs/version-3 plans/` misnamed stale duplicate** — PRD.md v2.0.0 Draft + Roadmap.md alongside canonical docs/PRD-v3.md / ROADMAP-v3.md.
- **D-M4. No frontend migration/changelog documentation** — withRouter removal, helpers/hooks consolidation, React 19/AntD v6/Vite upgrades, localStorage→httpOnly-cookie migration (planned F6.3b) untracked.

### Low
- **D-L1. WS transport undocumented** — ADR-002 lists "WebSocket support" as requirement; nothing documents ws_token handshake, `ws://${au}/ws?token=` construction, reconnect design, scheme break under HTTPS.
- **D-L2. Error envelope fix untracked** — REST_API_REVIEW.md R-08 remains Open with no link from IMPLEMENTATION_PLAN-v3 Phase 8.

### What's Good
- ADR corpus exemplary: 22 ADRs, indexed README status table, consistent Context/Decision/Alternatives/Consequences
- ADR-018 (DICOMweb) a model ADR matching shipped code (typed Study/Series in dicomweb.ts)
- ADR-003/ADR-008 document X-Auth-Pacs matching usage
- REST_API_REVIEW.md / SECURITY_AUDIT.md honest about gaps
- README broad (50+ env vars, testing commands); IMPLEMENTATION_PLAN-v3 Phases 1-3 as-built pattern excellent
- Pre-commit config matches CLAUDE.md claims; zero TODO/FIXME/HACK in frontend/src
