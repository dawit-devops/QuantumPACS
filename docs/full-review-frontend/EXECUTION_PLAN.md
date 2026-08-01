# Execution Plan: Frontend Review Remediation

**Branches:** `fix/sprint{N}-frontend-hardening` off `v3-dev` (Sprints 1-2 completed); `fix/sprint3-frontend-*` onward
**Total:** 6 sprints + ongoing, ~15-20 engineer-days
**Merges:** one PR per sprint; 18-check gate (incl. build-gate) must pass; admin merge (repo has no branch protection), branch deleted after merge
**Source:** `docs/full-review-frontend/05-final-report.md` (157 findings: 10 Critical, 41 High, 74 Medium, 32 Low)

Legend: ✅ done (merged PR) · 🔲 planned

---

## Sprint 1: Auth & Session (P0) — DONE

**PRs:** #73 `chore/frontend-tooling` · #74 `fix/sprint1-hardening` (commit `5c67863`)

| # | Issue | File(s) | Fix | Status |
|---|-------|---------|-----|--------|
| S-C1 | Full-access JWT in thumbnail URLs (`?token=`) | `src/detail/ThumbnailStrip.tsx:53-54`, `backend/api/auth.py` | Drop query token from thumbnails; backend query-param auth restricted to WS + share-token flow; tests | ✅ #74 |
| S-C2 | WS `ws://` + 1-min JWT + infinite reconnect loop | `src/ws.ts` | `wss://` scheme derivation, capped exponential backoff with jitter, guarded `JSON.parse` | ✅ #74 |
| S-C3 | 14-day refresh token in localStorage | `src/helpers.ts`, `frontend/nginx.conf` | Refresh token never persisted (HttpOnly cookie only, `getRefreshToken()` returns null); CSP + security headers added to nginx | ✅ #74 |
| S-H2 | Incomplete/inconsistent logout | `src/common/Sidebar.tsx`, `src/auth/AuthContext.tsx` | Logout via `signOut()` clears all keys incl. tempKey; tests | ✅ #74 |
| S-H3 | No `X-CSRF-Token: 1` → all mutations 403 | `src/helpers.ts`, `src/hooks.ts`, `src/files/UploadZone.tsx` | CSRF header in both fetch wrappers + UploadZone XHR; tests | ✅ #74 |
| P-H6 | Worklist params silently dropped | `src/worklist/Worklist.tsx` | Status/station/search/date/pagination → `options.query`; contract test | ✅ #74 |
| P-H2 | WS single-slot subscriber | `src/ws.ts` | Subscriber `Set` (multi-viewer annotation sync); 215-line test suite | ✅ #74 |
| P-C1 | Cornerstone 985 kB on every first load | `frontend/vite.config.js` | manualChunks rule anchoring vendor-cornerstone to lazy boundary | ✅ #74 (gate in S2) |
| P-C2 | chart.js in initial vendor-react chunk | `frontend/vite.config.js` | vendor-chart manualChunks rule | ✅ #74 |
| B-H1 | ESLint 9 dead config | `.pre-commit-config.yaml`, `.eslintrc.json`, `package.json`, `Makefile` | eslint hook wired, `lint`/`lint:fix` scripts, react-hooks plugin | ✅ #73 |
| B-H3 | No `chunkSizeWarningLimit` | `frontend/vite.config.js` | Limit aligned to actual chunk sizes | ✅ #74 |
| D-C2 | README claims CSP, nginx ships none | `frontend/nginx.conf` | CSP + X-Frame-Options + Referrer-Policy; `nginx.conf` now in repo | ✅ #74 |

---

## Sprint 2: Transport, Viewer Lifecycle, CI Gates (P1) — DONE

**PR:** #75 `fix/sprint2-hardening` (commits `a244c0e`, `85c8367`)

| # | Issue | File(s) | Fix | Status |
|---|-------|---------|-----|--------|
| S-H6 | Hl7Dashboard silent config-load failure | `src/hl7/Hl7Dashboard.tsx` | `configError` state; Save disabled when config missing; retryable alert; test | ✅ #75 |
| P-H3 | 401-refresh thundering herd | `src/helpers.ts` | Single-flight `tryRefreshToken` (shared `refreshPromise`); dedup test | ✅ #75 |
| P-H4 | Mutations retried up to 4× on 5xx | `src/helpers.ts` | `fetchWithRetry` exported; GET-only, capped retries; tests | ✅ #75 |
| P-H5 | Replicas poll every 2s (1,800 req/h) | `src/replicas/Replicas.tsx` | 10s visibility-aware interval + focus listener + in-flight guard | ✅ #75 |
| P-H7 | Detail triple-fetch + 500ms remount hack | `src/detail/Detail.tsx` | Removed `key`/`setKey(2)`/`window.ctinit`; viewer mounts after metadata | ✅ #75 |
| P-H8 | `checkReady` loop never cancelled | `src/detail/CornerstoneElement.tsx` | Bounded (50 attempts ~5s) + unmount guard | ✅ #75 |
| D-H2 | Coverage thresholds never enforced | `frontend/vite.config.js`, `.github/workflows/ci.yml`, `frontend/scripts/check-bundle-size.mjs` | New `build-gate` CI job: production build + bundle-size budget check + `vitest run --coverage`; thresholds set to current baseline (functions 32 / lines 42 / branches 31 / statements 38), raised as coverage grows; `@vitest/coverage-v8` added | ✅ #75 |

---

## Sprint 3: Viewer Refactor (P1, large) — DONE

**PR:** #77 `fix/sprint3-frontend-hardening`. Hardest sprint: the 1,122-line class component was the untested core of the app.

| # | Issue | File(s) | Fix | Status |
|---|-------|---------|-----|--------|
| Q-C1 | Dead inline-edit feature (400+ LOC) | `src/common/EditableTable.tsx:17` | Deleted the never-enabled editing machinery; replaced with read-only `src/detail/KeyValueTable.tsx` (last remaining P0) | ✅ #77 |
| Q-1 | CornerstoneElement god component (1,122 LOC, 30 binds) | `src/detail/CornerstoneElement.tsx` | Decomposed into `src/detail/viewer/` — `setup.ts` (one-time init), `tools.ts` (tool activation), `camera.ts` (viewport ops), `useAnnotationSync.ts` (annotations + WS send_state); component converted to hooks with disposed-flag effect cleanup; all listeners (keydown/resize/ws/eventTarget/annotation) now removed on unmount; added `ws.removeEventListener`/`removeOpenListener` | ✅ #77 |
| T-H3 | CornerstoneElement tested as inert shell | `src/test/CornerstoneElement.test.tsx` | Lifecycle tests added: stack enable on mount, initial stack load, persisted-annotation restore when viewport ready, stack swap + cache purge on image change, no purge on mount, full teardown on unmount (viewport, keydown, ws handlers) | ✅ #77 |
| P-M10 | Cornerstone image cache never purged (GB-scale RAM) | `src/detail/CornerstoneElement.tsx` | `cache.purgeCache()` on image change (skipped on initial mount) | ✅ #77 |
| Q-4 / P-M9 | `document.title` in render ×15 (React 19 violation) | `src/**/*.tsx` (15 sites) | `useDocumentTitle` hook in `src/hooks.ts`; all 15 pages migrated | ✅ #77 |

**Also in #77:** registered the `react-hooks` plugin in `.eslintrc.json` (B-H1 gap — disable comments referenced an unregistered rule); 16 test files' `../hooks` mocks extended with `useDocumentTitle`.

---

## Sprint 4: CI/CD Truth (P1/P2, medium) — PLANNED

~2-3 days. Fixes the pipeline/ops contradictions so CI reflects reality.

| # | Issue | File(s) | Fix | Status |
|---|-------|---------|-----|--------|
| D-H1 | Node 3-way version skew (CI 20 / Docker 22 float / dev 24) | `.github/workflows/ci.yml`, `frontend/Dockerfile` | `.nvmrc` at 22; CI uses it; Docker pinned digest | 🔲 |
| D-H3 | Playwright E2E (11 specs) never runs in CI | `.github/workflows/ci.yml`, `frontend/e2e/` | New `e2e` job (build → serve → playwright) | 🔲 |
| D-H4 | App images built then discarded; compose has no app services | `docker-compose.yaml`, `.github/workflows/ci.yml` | Compose app services + registry tags; nginx `backend:8080` proxy target exists | 🔲 |
| D-H5 | systemd units untracked; dev.sh swallows failures | `systemd/*.service`, `scripts/dev.sh` | Units + install script in repo; dev.sh errors on missing units | 🔲 |
| D-M1 | npm audit continue-on-error | `.github/workflows/ci.yml` | Fail on high/critical advisories | 🔲 |
| D-M2 | No caching / concurrency / path filters | `.github/workflows/ci.yml` | Setup-node cache, concurrency group, path filters | 🔲 |
| D-M3 / D-M4 | Trivy superficial + `@master`; nginx root, no HEALTHCHECKs | `.github/workflows/ci.yml`, `frontend/Dockerfile` | Pin Trivy action version, deeper scan scope; non-root nginx + healthchecks | 🔲 |
| D-M6 / D-M8 | Hardcoded `pa55w0rd` in compose/scripts; repo-visible dev secret | `docker-compose.yaml`, `scripts/*`, `backend/config.local.yaml` | Env-var driven secrets, dev secret out of repo | 🔲 |
| D-M7 | No frontend `.dockerignore` | `frontend/.dockerignore` | Exclude node_modules/dist/tests | 🔲 |
| D-M12 / D-M13 | dev/prod runtime divergence; no rollback story | `scripts/dev.sh`, `docs/ops-guide.md` | Parity docs; rollback procedure | 🔲 |

---

## Sprint 5: Typed API Layer + Architecture (P2, large) — PLANNED

~3-4 days. Removes the `[object Object]` class of bugs at the source.

| # | Issue | File(s) | Fix | Status |
|---|-------|---------|-----|--------|
| A-2 / H-7 / Q-3 | No typed API layer (~200 stringly-typed URLs); helpers/hooks/dicomweb triplicated | `src/helpers.ts`, `src/hooks.ts`, `src/dicomweb.ts` | `request<T>` generics; consolidate to one transport; typed `src/api/` modules | 🔄 3/4 done (client, studies, roles, users, notifications, logs, fhir, files; ~19 raw call sites left) |
| A-1 / A-9 / M-security | Error contract broken (envelope vs `Error(status)` strings); server text may leak | `src/helpers.ts`, `backend/api/response.py` | Client parses envelope; sanitize server text in errors | 🔲 |
| A-4 / H-8 | withRouter legacy HOC over RR7 | `src/withRouter.tsx` | Migrate to router hooks; delete HOC | 🔲 |
| H-10 | 94 static `message.*` calls | `src/**/*.tsx` | antd `App.useApp()` context | 🔲 |
| B-H2 | `@cornerstonejs/metadata` declared, zero imports | `frontend/package.json` | Remove unused dependency | 🔲 |
| Q-2 | Hl7Dashboard three-in-one (660 LOC, 6 near-identical fetch blocks) | `src/hl7/Hl7Dashboard.tsx` | Extract config/service/history subcomponents | 🔲 |
| D-C1 | No API contract for frontend consumers | `docs/` | Contract doc from openapi.json (error envelope, auth, WS); document dicomweb.ts pattern as standard | 🔲 |
| Q-5 | ~406 `any` | `src/**/*.ts` | Tighten top-10 offenders with the new typed layer | 🔲 |

---

## Sprint 6: P2/P3 Backlog Sweep (ongoing) — PLANNED

~4-5 days, highest-value rows first; remaining L-items fold in as time permits.

| # | Issue | File(s) | Fix | Status |
|---|-------|---------|-----|--------|
| A-5 / A-7 | WS design (dead `/ws` proxy config); routing table (19 ProtectedRoute wrappers, dead /logout) | `src/App.tsx`, `frontend/nginx.conf` | Consolidate; remove dead route | 🔲 |
| A-6 | Auth dual-write divergent logout | `src/auth/AuthContext.tsx`, `src/helpers.ts` | Single auth source of truth | 🔲 |
| M1 / M2 / M4 | tempKey lifecycle; PHI in URL params + unguarded parse; NotificationBell server-controlled navigation | `src/helpers.ts`, `src/common/NotificationBell.tsx` | Scoped storage, encoded params, client-side routing | 🔲 |
| P-M1 | NotificationBell 30s poll vs WS channel | `src/common/NotificationBell.tsx` | Subscribe to WS event channel | 🔲 |
| P-M2 / P-M3 / P-M4 | Logs unbounded DOM; Files duplicate mount fetch + stale-closure pagination; QIDO unbounded | `src/logs/`, `src/files/`, `src/detail/` | Virtualize; fix fetch/pagination; cap QIDO results | 🔲 |
| P-M5 / P-M6 / P-M8 / P-M11 | ThumbnailStrip eager 200-GET; column configs per render; batch ops N-concurrent; Hl7Dashboard 4 endpoints on mount | `src/detail/ThumbnailStrip.tsx`, `src/common/`, `src/files/` | Lazy thumbs; memoized configs; concurrency cap; coalesced loads | 🔲 |
| Q-6..Q-21 | Worklist 676 LOC / double filtering; `let`×186; hooks.ts near-dead; `catch {}`×14; `request()` undefined; parseParams no decode; batch false success | `src/worklist/Worklist.tsx`, `src/hooks.ts`, `src/**` | Code-quality batch, strongest by LOC-to-value | 🔲 |
| T-M1..T-M4 / T-L1..L4 | useFetch untested; NotificationBell error paths; permission-gating contract; empty/denied/error UI; selector/duplication/phantom-fetch/matchMedia fixes | `src/test/` | Test gaps for refactored components | 🔲 |
| D-M5 / D-M9..M11 | Config divergence; alerting/backup timer; backup_db.sh wrong ports | `scripts/*`, `docs/ops-guide.md` | Config templates; timer unit; port defaults | 🔲 |
| D-M1..M4 / D-H1..D-H4 | docs: why-comments in 92/105 files; README inaccuracies; `docs/version-3 plans/` stale; no changelog; CLAUDE.md/ADR-006 drift; IMPLEMENTATION_PLAN-v3 stale; ADRs (WS/share-link/token-storage) | `docs/`, `README.md`, `CLAUDE.md` | Doc refresh + ADRs + why-comments on 3 most complex files | 🔲 |
| L-* | All low-priority rows (code A-10..17, security L1-7, perf L1-4, testing L1-4, docs L1-2, best-practices L1-9, CI/CD L1-6) | `src/**`, `scripts/*`, `docs/*` | Backlog queue; fold into sprints opportunistically | 🔲 |

---

## Verification gates (every PR)

1. Pre-commit: ruff, prettier, tsc, pytest, eslint
2. CI (18 checks incl. build-gate): lint-backend, lint-frontend, security, test-backend ×2, test-frontend ×2, typecheck ×2, vuln-scan ×2, build-gate ×2, docker-build ×2
3. Manual smoke: backend `/api/health` 200, docker redis poll errors = 0, bundle script exit 0
