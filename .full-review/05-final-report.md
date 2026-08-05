# Comprehensive Code Review Report

## Review Target

`frontend/` — QuantumPACS React SPA (105 files, ~19.6k LOC; React 19.2, Vite 8/Rolldown, Ant Design v6.5, Cornerstone3D 5.6, TypeScript strict) plus its deployment surface (frontend Dockerfile/nginx.conf, CI workflows, scripts) and backend integration points (auth, response envelope, WS). Review: 2026-07-31.

## Executive Summary

The frontend has a strong architectural skeleton — disciplined lazy routing, exemplary context discipline, zero XSS sinks, a clean test-hygiene baseline — but it ships with three systemic defects: (1) the auth/session design is internally contradictory (HttpOnly cookie + localStorage JWTs + CSRF enforcement that the client never satisfies), (2) the DICOM viewer bundle defeats its own lazy boundary (~1 MB gzip on every first load) and its lifecycle code is untestable (1,122-line class component, never-cancelled loops), and (3) the error contract between backend and frontend is broken such that users see `[object Object]` and the Worklist silently drops all query parameters. Every layer (code, tests, docs, CI) contains traps where the current green pipeline gives false confidence.

## Findings by Priority

### Critical Issues (P0 — Must Fix Immediately)

**Security:**
- **S-C1 (CVSS 8.1, CWE-598/522)** — Full-access JWT in thumbnail URLs: `src/detail/ThumbnailStrip.tsx:53-54` appends `?token=<access JWT>`; backend accepts `?token=` on every `/api` route (`backend/api/auth.py:200`). Token lands in nginx `$request_uri` logs, browser history, proxy logs → full session takeover (1h window). Fix: rely on the existing HttpOnly cookie; restrict query-param auth to the share-token flow; log `$uri` only.
- **S-C2 (CVSS 7.5, CWE-319/400)** — WS plaintext `ws://` + 1-min JWT in query + infinite reconnect loop (`src/ws.ts:12-21`): cleartext token on LAN, auth/asyncpg storm on outage, unguarded `JSON.parse` at 17/40. Fix: `wss://` derivation, capped backoff, try/catch parse, server origin check.
- **S-C3 (CVSS 7.5, CWE-522/539)** — 14-day refresh token in localStorage (9 keys) with no CSP on the SPA document; one XSS = full PHI exfil. The HttpOnly cookie design (users.py:76-83) is undermined by the client. Fix: cookie + in-memory copy, never persist refresh token, add CSP.
- **S-H3 (CVSS 7.5)** — Frontend never sends `X-CSRF-Token: 1`; every POST/PUT/DELETE 403s in practice (CSRFMiddleware app.py:103-123, zero matches in src). Includes logout → server session survives "logout". Fix: header in the two fetch wrappers + UploadZone XHR.

**Performance (measured):**
- **P-C1** — Cornerstone3D 985 kB gzip executes on every first load (vendor-cornerstone anchored to entry chunk); initial JS graph 5.15 MB min / 1.49 MB gzip, ~78% unused on most routes. Fix: manualChunks rules + bundle-size CI gate.
- **P-C2** — chart.js (~70 kB gzip, used only on /metrics) bundled into initial vendor-react chunk. One-line chunk rule fixes.

**Data-correctness:**
- **P-H6** — Worklist request params silently dropped (`Worklist.tsx:73-103` → helpers only honors `options.query`): status filters/pagination never reach the server; 1 unfiltered request per keystroke; pagination is a no-op.
- **Q-C1** — Dead inline-edit feature (`EditableTable.tsx:17`): 400+ lines of dead code around never-enabled editing.
- **S-H6 (CVSS 6.5)** — Hl7Dashboard silent config-load failure → Save overwrites real server MLLP config with defaults (`catch {}` at 96-107).

### High Priority (P1 — Fix Before Next Release)

**Auth/session:** S-H2 incomplete+inconsistent logout (Sidebar leaves 5 keys, never calls signOut, tempKey survives); S-H4 21 npm advisories (direct react-router GHSA-qwww-vcr4-c8h2, adm-zip via dcmjs, workbox ejs/jake); T-C1 no CSRF/logout tests; T-C2 Worklist contract test passes trivially; H3 (perf) 401-refresh thundering herd (N parallel /auth/refresh, no dedup).

**Viewer lifecycle:** P-H7 Detail triple-fetches same DICOM instance (wadouri→wadors + 500ms remount hack Detail.tsx:122-128); P-H8 checkReady 100ms loop never cancelled even after unmount (CornerstoneElement.tsx:716-725); T-H3 CornerstoneElement tested as inert shell (lifecycle bugs invisible); T-H4 ws.ts zero tests; T-H5 retry/backoff/refresh-dedup untested (no fake timers anywhere).

**Transport/retry:** P-H4/S-M3 fetchWithRetry retries non-idempotent mutations up to 4× on 5xx (up to 80 reqs per batch click); P-H5 Replicas full-table poll every 2s (1,800 req/h/tab); P-H2 WS single-slot subscriber (2nd viewer kills 1st's annotation sync).

**Tooling dead code:** B-H1 ESLint 9 dead (legacy eslintrc ignored, no script, no react-hooks plugin); B-H2 `@cornerstonejs/metadata` declared, zero imports; B-H3 978 kB gzip cornerstone chunk with no chunkSizeWarningLimit.

**Docs/CI contradictions:** D-C1 no API contract for frontend consumers (openapi.json covers 13/92+ routes, referenced nowhere — the `[object Object]` bug survived because no doc states the error envelope); D-C2 README claims CSP via Caddy but Docker ships nginx with zero security headers; D-H1 CLAUDE.md conventions drift (CSS Modules claim false, AntD v5 claim vs v6, ES version stale, pa55w0rd claim unverifiable); D-H4 IMPLEMENTATION_PLAN-v3 Phase 6 status stale.

**CI/CD:** D-H1 Node 3-way version skew (CI 20 / Docker 22 float / dev 24); D-H2 coverage thresholds configured but never enforced; D-H3 Playwright E2E (11 specs) never runs in CI; D-H4 app images built then discarded (no registry/tags, compose has no app services — `backend:8080` proxy target doesn't exist anywhere); D-H5 systemd units untracked, dev.sh swallows missing-unit failures.

### Medium Priority (P2 — Plan for Next Sprint)

- **Code quality:** Q-1 CornerstoneElement god component (1,122 LOC, 30 binds); Q-2 Hl7Dashboard three-in-one (660 LOC, 6 near-identical fetch blocks); Q-3 fetch layer triplicated (helpers/hooks/dicomweb, already drifted); Q-4 `document.title` in render ×15 (React 19 violation); Q-5 ~406 `any`; Q-6–Q-21 (Worklist 676 LOC, double filtering, `let`×186, hooks.ts near-dead, error-shape fragility, WS/Detail hacks, NotificationBell rejections, batch-op false success, `catch {}`×14, request() undefined, parseParams no decode)
- **Architecture:** A-1 error contract (backend envelope vs `Error(status)` strings); A-2 no typed API layer (~200 stringly-typed URLs); A-3 helpers/hooks drift; A-4 withRouter legacy HOC over RR7; A-5 WS design (single-subscriber, dead /ws proxy config); A-6 auth dual-write divergent logout; A-7 routing table (19 ProtectedRoute wrappers, dead /logout route); A-8 render-phase side effects; A-9 response-envelope inconsistency
- **Security (M1–M6):** tempKey lifecycle; PHI in URL search params + unguarded JSON.parse; CORS `*` in tests; NotificationBell server-controlled navigation; error contract may leak server text
- **Performance (M1–M10):** NotificationBell 30s poll vs WS channel; Logs unbounded DOM; Files duplicate mount fetch + stale-closure pagination; QIDO unbounded results; ThumbnailStrip eager 200-GET; column configs rebuilt per render; batch ops N-concurrent; title effects; Cornerstone image cache never purged (GB-scale RAM); Hl7Dashboard 4 endpoints on mount
- **Testing (M1–M4):** useFetch untested + mocked everywhere; NotificationBell error paths; permission-gating backend contract; empty/denied/error UI paths
- **Docs (M1–M4):** why-comments absent in 92/105 files incl. the three most complex; README inaccuracies (paths, counts, quick start, dev workflow undocumented); `docs/version-3 plans/` stale duplicate; no frontend migration/changelog
- **Best practices (H4–H12):** chart.js chunk rule; unpinned node:22-alpine vs Vite 8 engine; ws single-slot; `request<T>` generics; useFetch delegation; withRouter migration; antd 94 static `message.*` vs App.useApp
- **CI/CD (M1–M13):** npm audit continue-on-error; no caching/concurrency/path filters; Trivy superficial + @master; nginx as root + no HEALTHCHECKs; hardcoded pa55w0rd in compose/scripts; no frontend .dockerignore; repo-visible dev secret constant; config.local.yaml creation divergence; no alerting/backup timer; backup_db.sh wrong-port defaults; dev/prod runtime divergence; pre-commit vs CI test-set mismatch; no rollback story

### Low Priority (P3 — Track in Backlog)

- Code: A-10–A-17 (request() undefined after refresh, mutation retries, auth schemes, client gating trust, vendor chunking, duplicated error reporting, CSS convention drift, navigator global)
- Security L1–L7 (cosmetic lockout, 0.0.0.0 dev bind, noopener, parseParams encoding, WS single-subscriber, thumbnail cookie reliance, self-destroying sw.js in dist)
- Performance L1–L4 (WS init pre-auth, parseAnnotations recompute, options mutation, UploadZone timer cleanup)
- Testing L1–L4 (implementation-detail selectors, App.test duplication, phantom fetch fallback, matchMedia desktop lock)
- Docs L1–L2 (WS transport undocumented, R-08 untracked)
- Best practices L1–L9 (React default imports ×37, `let[`, setToolActive cast, interval in state, vite/client types, define band-aid, ES2020 target, stray files, PWA audit)
- CI/CD L1–L6 (npm ci flag mismatch, floating base tags, compose gaps, dev.sh over-broad || true / cleanup_port, missing hygiene hooks, unused package.json scripts)

## Findings by Category

- **Code Quality**: 22 findings (1 Critical, 5 High, 16 Medium)
- **Architecture**: 17 findings (0 Critical, 3 High, 14 Medium)
- **Security**: 22 findings (3 Critical, 6 High, 6 Medium, 7 Low)
- **Performance**: 24 findings (2 Critical, 8 High, 10 Medium, 4 Low)
- **Testing**: 15 findings (2 Critical, 5 High, 4 Medium, 4 Low)
- **Documentation**: 12 findings (2 Critical, 4 High, 4 Medium, 2 Low)
- **Best Practices**: 21 findings (0 Critical, 5 High, 7 Medium, 9 Low)
- **CI/CD & DevOps**: 24 findings (0 Critical, 5 High, 13 Medium, 6 Low)

**Totals: 157 findings — 10 Critical, 41 High, 74 Medium, 32 Low**

## Recommended Action Plan

1. **Sprint 1 — Auth & session (P0, small):** S-C1 (drop thumbnail query token) → S-H3 + S-H2 (X-CSRF-Token in `request()`/`useFetch`/UploadZone; logout via signOut clearing all 9 keys) → S-C2 (wss scheme, backoff, JSON.parse guard) → S-C3 (retire localStorage refresh token, in-memory copy) → CSP + security headers in nginx.conf. Effort: small. Effect: fixes the "logout doesn't log out", all-mutations-403, and token-leak classes at once.
2. **Sprint 1 — Fixes with regression tests (P0/P1, small):** P-H6 Worklist query plumbing + contract test (T-C2); S-H6 Hl7Dashboard Save-guard + test (T-H1); T-C1 CSRF/logout tests. Tests first where a known bug exists — the suite must have caught these.
3. **Sprint 2 — Bundle & load (P0, small):** manualChunks rules (preload/vendor-cornerstone/chart.js) + `chunkSizeWarningLimit` + bundle-size CI gate (D-H2 coverage + build gates); verify with `vite build`. Reclaims ~1.05 MB gzip initial.
4. **Sprint 2 — Transport hardening (P1, medium):** P-H3 single-flight refresh; P-H4 GET-only capped retries; P-H5 Replicas event-driven polling; P-H2 WS subscriber Set; P-H7/P-H8 Detail/CornerstoneElement lifecycle (remove remount hack, mount-after-metadata, bounded checkReady with unmount guard).
5. **Sprint 3 — Viewer refactor (P1, large):** decompose CornerstoneElement (viewport/tools/annotation-sync/camera), hooks conversion with disposed-flag effect cleanup — enables T-H3 lifecycle tests; purge image cache on study change.
6. **Sprint 3 — CI/CD truth (P1, medium):** Node version alignment (.nvmrc), coverage + build gates, Playwright CI job, npm audit fail, systemd units + install script in repo, compose app services + registry tags (D-H1..5, D-M1..3).
7. **Sprint 4 — Typed API layer (P2, large):** `request<T>` generics + migrate top-10 `any` offenders; consolidate helpers/hooks transport; withRouter → hooks; antd App.useApp; useDocumentTitle hook. Document the dicomweb.ts pattern as the standard (D-C1 contract doc, D-H3 real frontend dev guide, B-H1 lint react-hooks enabled to keep it that way).
8. **Ongoing:** update CLAUDE.md/ADR-006/README (D-H1/D-H2/D-M2), IMPLEMENTATION_PLAN-v3 as-built markers (D-H4), ADRs for WS/share-link/token-storage (D-H2), why-comments on the 3 most complex files (D-M1), admin CRUD tests pattern extended to ws/notifications/share (T-M2/T-H4).

## Review Metadata

- Review date: 2026-07-31
- Phases completed: 1A/1B Code Quality & Architecture, 2A Security, 2B Performance (with real production build to /tmp/opencode/qvite-build), 3A Testing, 3B Documentation, 4A Best Practices, 4B CI/CD — all 5 phases, checkpoint approved
- Flags: framework=react-vite-antd; performance findings measured, not estimated
- Output files: `00-scope.md`, `01-quality-architecture.md`, `02-security-performance.md`, `02b-performance.md` (measured build evidence), `03-testing-documentation.md`, `04-best-practices.md`, this report
