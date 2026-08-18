# Phase 2: Security & Performance Review

## Security Findings (2A)

### Critical
- **S-C1. Full-privilege JWT in URL query strings for image loading** (CVSS 8.1, CWE-598/522) — `src/detail/ThumbnailStrip.tsx:53-54` appends `?token=<access JWT>` to thumbnail URLs; backend accepts `?token=` on **every** `/api` route (`backend/api/auth.py:200`), so a leaked token = full session (1h). Lands in nginx `$request_uri` logs, browser history, proxy logs. Fix: drop query token (HttpOnly session cookie already authenticates same-origin requests, users.py:76-83), restrict query-param auth to share-token flow, strip query from logs.
- **S-C2. WS plaintext `ws://` + JWT in query + infinite reconnect** (CVSS 7.5, CWE-319/400) — `src/ws.ts:12-21`: hardcoded `ws://` (never wss), 1-min full-permission token (`backend/api/ws.py:106`) over cleartext on LAN; close → `init()` infinite loop, each iteration POSTs fresh `ws_token` (401/asyncpg storm); unguarded `JSON.parse(event.data)` at 17/40. Fix: derive scheme from `API_URL`, exp. backoff + cap, try/catch parse, origin check server-side (`ws.py:113`).
- **S-C3. Tokens in localStorage defeat the HttpOnly-cookie design** (CVSS 7.5, CWE-522/539) — `helpers.ts:50-66`, `AuthContext.tsx:94-112`: 9 keys incl. **14-day refresh token**; app has no CSP (S-H1) → one XSS = full PHI exfil for 2 weeks. Fix: keep JWT in cookie + in-memory copy; never persist refresh token; add CSP.

### High
- **S-H1. SPA served with no security headers, no TLS, CSP only on JSON responses** (CVSS 7.0, CWE-693/523) — `frontend/nginx.conf:1-21`, `Dockerfile:8-11`: SecurityHeadersMiddleware (`backend/app.py:48-57`) only hits `/api`. nginx: no CSP/XFO/HSTS/nosniff on the document, `listen 80` only, `proxy_set_header Connection $http_connection` (not `upgrade` — breaks WS through proxy), access log logs `$request_uri` incl. query tokens (feeds S-C1).
- **S-H2. Logout incomplete + inconsistent — server session survives** (CVSS 6.5, CWE-613) — `common/Sidebar.tsx:105-114` never calls `AuthContext.signOut()`, leaves `username/role/permissions/tenant_id/tempKey`; stale privileges in-memory (`ProtectedRoute.tsx:11`); logout POST 403s (see S-H3) → `catch {}` → `block_token()` never runs; `tempKey` (share credential) survives logout.
- **S-H3. Frontend never sends `X-CSRF-Token: 1` — every mutation 403s** (CVSS 7.5 availability, CWE-304) — `backend/app.py:103-123` CSRFMiddleware requires it on POST/PUT/DELETE; zero matches in `frontend/src` (grep). Uploads, shares, worklist ops, notifications, HL7 save, CRUD, password change all fail 403 in practice. Fix: add header globally in `request()`/`useFetch`/UploadZone XHR.
- **S-H4. Supply chain: 21 npm advisories** (20 high, 1 moderate) — `react-router-dom 7.18.1` → react-router GHSA-qwww-vcr4-c8h2 (RSC-mode CSRF, direct dep; upgrade ≥8.3.0); `dcmjs → adm-zip <0.6.0` GHSA-xcpc-8h2w-3j85 (crafted ZIP → 4 GB alloc — relevant: DICOMs parsed client-side); vite-plugin-pwa/workbox ejs+jake build-time; uuid <11.1.1. Fix: upgrades + npm audit in CI.
- **S-H5. Client permission gating trusts forgeable localStorage — verified safe only because backend enforces everything** (CWE-807, not exploitable today) — JWT-carried permissions, `requires_permission` on every data route (rbac.py:9-21), tenant checks server-side (auth.py:119-124, files.py:219/363), token-version + active-user checks, blocklist on logout/password change. Add a regression test: forged `admin=true` → 403.
- **S-H6. Hl7Dashboard silent config-load failure enables destructive overwrite** (CVSS 6.5, CWE-754) — `Hl7Dashboard.tsx:96-107` `catch {}` → form at hardcoded defaults (mllpPort 12579, empty allowed_ips) → Save PUTs defaults over real server config, wiping MLLP port + IP allow-list (HIPAA-relevant). Fix: disable Save until config loads.

### Medium
- **S-M1. Share credential `tempKey` persisted in localStorage, never cleaned** (CVSS 5.3, CWE-922) — `index.tsx:51-56`, `ShareView.tsx:8-10`; outlives logout; ShareView does `history.replace("/")` (good) but localStorage copy remains. Fix: sessionStorage + delete on logout + client expiry check. `Share.tsx:176` fragile string-mangling of hash.
- **S-M2. PHI in URL query strings + unguarded JSON.parse** (CVSS 5.3, CWE-359/598) — `Files.tsx:31-38`: advanced searches JSON-encoded into URL (`?{"query":"P001",...}`) → history/referrer/proxy logs; `decodeUrl` unguarded `JSON.parse` on URL data → malformed query crashes app (self-DoS). Fix: sessionStorage; try/catch.
- **S-M3. fetchWithRetry retries non-idempotent mutations up to 4× on 5xx** (CVSS 5.3, CWE-841) — `helpers.ts:31-48` (+ duplicate `hooks.ts:12-29`): retry only GET; never re-issue POST/DELETE on received 5xx; cap 2; honor Retry-After.
- **S-M4. NotificationBell unhandled rejections + server-controlled navigation** (CVSS 4.3, CWE-754) — `NotificationBell.tsx:78-113`: no try/catch, optimistic updates on failure; validate `n.link` starts with `/`.
- **S-M5. CORS needs production verification** (CVSS 4.3, CWE-942) — `backend/app.py:210`: `allow_credentials=True` + custom headers; tests default `cors_origins` to `*` (`test_app.py:221`) — ensure production is explicit origin list, never `*`.
- **S-M6. Error contract leaks nothing but renders garbage; can surface server exception text** (CVSS 3.7, CWE-209) — `helpers.ts:4-19,170-172`: 400 treated as success-path; `Error(error.error||...)` may show backend exception text. Client console usage minimal/clean (verified).

### Low
- **S-L1.** Client login lockout cosmetic (`Login.tsx:26-60`) — server `login_bucket` (users.py:59-63) is the real control. Keep both.
- **S-L2.** Vite dev binds `0.0.0.0` (`vite.config.js:42`) — documented dev setup, gate on shared networks.
- **S-L3.** `window.open(url)` without `noopener` (`helpers.ts:184`) — same-origin, low risk; add anyway.
- **S-L4.** `parseParams` lacks `decodeURIComponent` (`helpers.ts:188-197`) — no injection (React escapes).
- **S-L5.** WS single-subscriber design (`ws.ts:36-42`) — last-registered listener wins (availability).
- **S-L6.** Thumbnail `new Image()` relies on cookie — fine once S-C1 fixed.
- **S-L7.** `dist/sw.js` self-destroying (dev artifact) — verify prod build runs real Workbox precache (static only, no API caching — good).

### Verified Safe
- **No XSS sinks**: zero `dangerouslySetInnerHTML` in src, no eval/new Function/postMessage/document.cookie writes; all PHI renders via React text nodes (auto-escaped): EditableTable.tsx:60-66, Files.tsx:322-329, NotificationBell.tsx:191-224, Hl7Dashboard.tsx:173-227. Cornerstone annotation text is canvas-rendered.
- **Backend authorization is the enforcement point** (JWT permissions, requires_permission, tenant checks, token-version, blocklist).
- **Session cookie hardened**: HttpOnly, Secure, SameSite=Strict, path=/api (users.py:76-83).
- **CSRF posture server-side strong** (SameSite + custom header + custom-header auth = defense in depth) — S-H3 is a client-contract bug.
- **No hardcoded secrets** in frontend; production-secret assertion (app.py:140-143); TrustedHostMiddleware (app.py:202); rate limiting on login/password/API keys; Pydantic `parse_body` validation; int-cast file IDs (no path traversal); `encodeQuery` uses encodeURIComponent; OAuth idp slug server-validated.
- **No PHI in client console logging.**

## Performance Findings (2B) — measured via real production build to /tmp/opencode/qvite-build

### Critical
- **P-C1. Cornerstone3D is NOT lazy in practice — 985 kB gzip in initial load** — Rolldown hoisted `__vitePreload` helper into `vendor-cornerstone` (3,586 kB / 985 kB gzip) which the entry chunk statically imports → every visit incl. `/login` downloads/executes the whole engine. Initial JS graph ≈ 5.15 MB min / 1.49 MB gzip, ~78% for routes never opened. Fix: `manualChunks` rule `__vite/preload → vendor-preload` (vite.config.js:33), re-verify build, add bundle-size CI check.
- **P-C2. chart.js (~70 kB gzip) bundled into `vendor-react` initial chunk** — `Metrics.tsx:36-47` only importer; react-chartjs-2 dragged in via `node_modules/react` rule; lazy Metrics chunk only 7.4 kB. Fix: `chart.js`/`react-chartjs-2 → vendor-chart` rule.

### High
- **P-H1. WS reconnect storm** — `ws.ts:19-21` close→init() no backoff/cap + fresh `ws_token` HTTP request per attempt; sustained 1+ req/s/tab indefinitely against asyncpg pool. Fix: capped exp. backoff + jitter, terminate after N, gate on `navigator.onLine` (code sample in 02b).
- **P-H2. WS single-slot subscriber global** — `ws.ts:36-42`: 2nd viewer kills 1st's annotation sync; listeners accumulate per mount, never removed. Fix: `Set<fn>` registry + unsubscribe in componentWillUnmount.
- **P-H3. 401-refresh thundering herd** — `helpers.ts:146-169`: N parallel `/auth/refresh` per failing request, no in-flight dedup, stale-write race → cascade logout. Fix: module-level single-flight promise.
- **P-H4. fetchWithRetry 4× on 5xx incl. mutations** — up to 80 requests per worklist batch when backend failing (amplifies exactly when pool fragile); double-applied POSTs. Fix: GET-only retries, cap 2, never on received 5xx for mutations.
- **P-H5. Replicas polls full table every 2 s forever** — `Replicas.tsx:58-64`: 0.5 req/s, 1,800 req/h/admin tab, unpaginated, full re-render each tick. Fix: 15-30s or WS `replica.sync_status_changed` event-driven + AbortController.
- **P-H6. Worklist params silently dropped** — `Worklist.tsx:73-103` → `request("worklist", query)`; helpers only honors `options.query`/`data` → status/page/filters never reach server; unfiltered page-1 refetch + **1 request per keystroke** (Worklist.tsx:479-481). Fix: proper query building + 300ms debounce + stale-response guard.
- **P-H7. Detail fetches same DICOM instance 2–3×** — wadouri→wadors switch re-`setStack` (`CornerstoneElement.tsx:744-760`) + `setKey(2)` remount hack (`Detail.tsx:122-128`) → 2nd/3rd fetch+decode (30-100 MB instances), 500ms flicker. Fix: delete remount hack, mount after metadata resolved, update stack in place on SOP UID change.
- **P-H8. checkReady 100ms loop never cancelled** — `CornerstoneElement.tsx:716-725`: infinite 10×/s even after unmount (no `this.mounted` guard), touches annotation manager + setState on detached component. Fix: bound attempts (~50), gate on mounted + visibility, clear timer in unmount.

### Medium
- **P-M1. NotificationBell polls 30s despite WS channel existing** — 2 req/min/user/tab of full DB COUNT; 100 users ≈ 3.3 req/s idle. Fix: WS event-driven + 60s fallback.
- **P-M2. Logs live-tail unbounded DOM growth** — `Logs.tsx:164-175,212-246` prepend never trimmed; antd Table not virtualized. Fix: cap backlog ~200 or virtualize.
- **P-M3. Files duplicate fetch on mount + stale-closure pagination** — two mount effects both call fetch (2 identical requests, ×4 under 5xx); page resets land in dead closure; search while on page 3 refetches page 3. Fix: single mount effect + URL as page source of truth.
- **P-M4. QIDO results unbounded, unfilterable client-side** — no limit/offset (backend full scan), `dicomJsonToFlat` maps every row synchronously on main thread, antd renders all rows. Fix: `limit=100` server-side + virtualization.
- **P-M5. ThumbnailStrip eager-fetches every thumbnail** — 200 GETs for 200-instance series; `?token=` defeats HTTP cache. Fix: IntersectionObserver/loading=lazy + LRU cache + cookie auth.
- **P-M6. Column/Table config rebuilt every render** (Files:380-439, Worklist:301-411, Logs:326-382, FhirMonitoring:97-128) — useMemo columns, hoist render fns.
- **P-M7. Worklist batch ops: N concurrent requests, errors swallowed** — 20 rows = 20 parallel DELETE/POSTs, up to 80 with retries; `catch(()=>{})` + unconditional success toast. Fix: backend batch endpoint or concurrency cap + `Promise.allSettled` + warning toast.
- **P-M8. `document.title` side effect in render, 15 files** — React 19 concurrent render violation; move to useEffect.
- **P-M9. Cornerstone image cache never purged** — `RenderingEngine(ENGINE_ID)` singleton never destroyed, no `imageCache.purgeCache()` anywhere; GB-scale RAM pins + GPU context survives logout. Fix: purge on study change, destroy engine on session end.
- **P-M10. Hl7Dashboard fetches all 4 admin endpoints on mount** — incl. 24h metrics aggregation on idle tab. Fix: lazy per-tab fetch.

### Low
- **P-L1.** WS init attempted on every load incl. `/login` (index.tsx:57-59) — guard with auth state.
- **P-L2.** `parseAnnotations` recomputed every render (Detail.tsx:75) — memoize.
- **P-L3.** `request()` mutates caller's options object (helpers.ts:126-137) — clone at entry.
- **P-L4.** UploadZone setTimeout chains no unmount cleanup (UploadZone.tsx:125-249) — clear in effect cleanup.

### Verified Good
- Route-level code splitting: 21 lazy routes, 5-19 kB each ✅
- Decoders/workers load on demand (computeWorker 2.9 MB, wasm, decode workers not in initial graph) ✅
- vendor-antd/vendor-react cached chunks with stable names ✅
- Logs cursor-based incremental polling, self-cleaning highlight set ✅
- All intervals except H5/H1/H8 clean up on unmount; Files search debounced 300ms ✅
- AuthContext memoized; ThemeProvider cleanup proper; UploadZone XHR progress+abort ✅
- VitePWA selfDestroying avoids stale-SW trap ✅

## Critical Issues for Phase 3 Context
- S-H3 (missing X-CSRF-Token) + S-H2 (incomplete logout) + S-C3 (localStorage refresh token) — auth flow defects; tests should assert logout clears all keys and CSRF header is sent
- P-H6 (worklist params dropped) — Worklist.test.tsx may pass while prod behavior is broken (stale tests); P-H3 refresh race — auth tests needed
- No XSS sinks verified — keep it that way; tests exist for render escaping?
- S-H5 — regression test forged localStorage permissions → 403
- Files.tsx stale-closure pagination (P-M3) — existing Files tests may not catch it
- Coverage questions: are ws.ts reconnect/backoff, CornerstoneElement unmount cleanup, Hl7Dashboard config-failure, NotificationBell rejections tested?
