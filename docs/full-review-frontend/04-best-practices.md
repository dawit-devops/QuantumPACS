# Phase 4: Best Practices & Standards

## Framework & Language Findings (4A)

### High
- **B-H1. ESLint 9 is installed but linting is dead** — `eslint: 9.39.5` with legacy `.eslintrc.json` (ignored by ESLint 9 — flat config required); no `lint` script; `eslint-plugin-react@7.13` is React 17-era; **no `eslint-plugin-react-hooks`** → `react-hooks/exhaustive-deps` never runs (would have caught the Files.tsx missing-deps bugs). Prettier also not installed despite "prettier gate" claims. Fix: delete eslintrc, add flat config with react-hooks + react-refresh plugins, add lint script, wire into pre-commit + CI.
- **B-H2. `@cornerstonejs/metadata` declared but zero imports** — package.json:28; no MetadataProvider wired in `ensureGlobalInit()` (CornerstoneElement.tsx:57). Either wire the dicomweb metadata provider (needed for WADO-RS metadata parsing) or remove the dep — every KB counts in the 978 kB gzip cornerstone chunk.
- **B-H3. vendor-cornerstone chunk 978 kB gzip** — measured: 3,586,085 B raw / 978,285 B gzip + computeWorker 777 kB gzip + ~2.7 MB wasm. First detail-view open downloads ~1 MB gzip. Fix: `target: 'esnext'`, `chunkSizeWarningLimit: 1200` (explicit, not ignored), keep cornerstone lazy; long-term split `@cornerstonejs/tools` annotation libs into second lazy chunk. (Note: the Phase-2 `__vitePreload` claim was **not reproducible** in current build — Vite 8/Rolldown emits the preload helper differently — but the oversized-chunk problem stands regardless.)
- **B-H6. `document.title` side effect in render, 15 files** (+ `localStorage.setItem("tempKey")` in render at index.tsx:54-56) — React 19 concurrent violation. Fix: single `useDocumentTitle` hook.
- **B-H7. CornerstoneElement: 1,122-line class component, 30 `.bind()` calls, interval stored **in state** (line 199/207 → re-render every tick), 500 ms polling, 13 manual listeners** — React 19 supports class components (no removed APIs used — verified), but the cost is correctness risk. Fix: refactor to hooks with `useReducer` force-render replacing poll-based state sync, `disposed` flag pattern in useEffect cleanup. `ErrorBoundary.tsx:13` (getDerivedStateFromError) is the correct class use — keep.

### Medium
- **B-H4. chart.js inside vendor-react (empirically confirmed in dist)** — `destroy:function` signature found in vendor-react chunk; manualChunks function form partitions only matched modules; unmatched shared deps merge into first vendor chunk. Fix: object-form manualChunks or add chart.js/react-chartjs-2 → vendor-charts rule.
- **B-H5. Unpinned `node:22-alpine` vs Vite 8 engine `^20.19.0 || >=22.12.0`** — floating tag may resolve to 22.0-22.11 → engine error. Fix: `node:22.12-alpine` + `"engines": {"node": ">=22.12"}`.
- **B-H8. ws.ts single-slot listener + unbounded reconnect recursion** — `messageFunc = func` one slot; close→init() recursion stacks; onOpen duplicates listener (28-34 vs 13-15). Fix: `Set<listener>` + unsubscribe; useSyncExternalStore for React consumers.
- **B-H9. `request(): Promise<any>` with zero generics; 451 `any` (417 src, 34 test)** — top offenders: Files 43, CornerstoneElement 26, Worklist 25, Detail 21... Fix: `request<T>(url, options): Promise<T>` removes most chains at once; types.d.ts is light (4 Window globals) — not a major contributor; `[key: string]: any` index signatures in CEProps/RequestOptions mask the rest.
- **B-H10. Duplicated transport: fetchWithRetry verbatim in helpers.ts + hooks.ts; useFetch re-implements headers/auth/401-refresh that request() already has** — useFetch has exactly 1 consumer (Login.tsx). Fix: delegate useFetch internals to `request<T>()` or drop useFetch for a useAsync wrapper.
- **B-H11. withRouter fabricates legacy history API** (withRouter.tsx:15-20 builds fake `history` object, spreads `...location` as props) — 16 consumers, untyped. All consumers are function components → migrate to useNavigate/useParams directly; keep navigator.ts (justified for non-component call sites like helpers.ts:167).
- **B-H12. antd v6: 94 static `message.*` calls in 28 files, zero `App.useApp`** — static API bypasses ConfigProvider theme/locale (documented antd limitation). Fix: wrap `<App>` in ConfigProvider + `App.useApp()`.

### Low
- **B-L1.** `import React from "react"` in 37 files (jsx: react-jsx) — only real uses React.Key (Worklist.tsx:68), React.ComponentType (withRouter.tsx:4).
- **B-L2.** 186 `let [` state destructures should be `const`.
- **B-L3.** `(tg as any).setToolActive` + `.call(tg,...)` workaround (CornerstoneElement.tsx:96-100) — 5.6 API is typed; drop cast.
- **B-L4.** `interval` in component state (CornerstoneElement.tsx:207) → re-render per tick; use ref.
- **B-L5.** tsconfig `types: ["node"]` excludes vite/client → `import.meta.env` untyped; `noUnusedLocals/Parameters: false`.
- **B-L6.** vite.config.js `.js` with `/// <reference types="vitest" />`; `define: {'process.env': {}}` band-aid — no source reads process.env, could drop.
- **B-L7.** tsconfig `target: ES2020` vs esnext build — modernize to ES2022+.
- **B-L8.** Stray files: `frontend/test-login-temp.js`, `frontend/test-results/`, committed `frontend/dist/` (incl. sw.js stale-cache footgun) — gitignore/remove.
- **B-L9.** vite-plugin-pwa 1.3.0 + selfDestroying + registerType autoUpdate — good config; workbox maxFileSize 6MB covers wasm; ejs/jake advisories need audit/overrides.

### Verified Good
- `strict: true` both tsconfigs; isolatedModules, moduleResolution: bundler, esModuleInterop
- createRoot + React.lazy/Suspense for all 21 routes; no ReactDOM.render misuse
- **Zero removed React 19 APIs**: no componentWillMount/UNSAFE_*/PropTypes/defaultProps/string refs/legacy context
- Context discipline exemplary (AuthContext/ThemeProvider: null-default + throwing guards, memoized values, useCallback actions, lazy useState initializers); ProtectedRoute minimal
- Vitest config modern (jsdom 29 pretendToBeVisual, v8 coverage provider + thresholds, fork pool caps, e2e exclusion); RTL 16 + user-event 14 + jest-dom + Playwright 1.61
- nginx.conf clean SPA try_files, API/WS proxy, $http_upgrade/Connection headers correct (contradicts Phase-2 H1 concern — WS proxy is fine)
- No useMemo/useCallback misuse (30/22 usages, correct deps); only 2 `window as any` casts; chart config memoized; theme via data-theme attr with proper matchMedia cleanup

## CI/CD & DevOps Findings (4B)

### High
- **D-H1. Node version three-way skew** — CI `node-version: '20'` (ci.yml:17,24,45, security.yml:29), Docker `node:22-alpine` (floating), dev systemd `node v24.18.0`. Vite 8/Vitest 4/TS 6 across 20/22/24. Fix: `.nvmrc`/engines + CI reads it, pin Docker to specific minor (`node:22.14-alpine` or digest).
- **D-H2. Coverage thresholds configured but never enforced in CI** — vite.config.js:69-74 (lines 50, branches 40, functions 60); CI runs plain `npx vitest run` (ci.yml:46); `vite build` chunk-size regression has no gate (only warning). Fix: coverage job with thresholds enforced + build with fail-on-warning budget.
- **D-H3. Playwright E2E absent from CI** — 11 spec files + playwright.config.ts exist; config has no webServer/reuseExistingServer → requires manual app+DB. Auth/RBAC flows — highest-risk area of a medical system — never tested in CI. Fix: CI job with webServer + postgres service, `playwright/install` browsers; nightly fallback.
- **D-H4. App images are never deployed — throwaway builds** — ci.yml builds both images, discards them; docker-compose has only postgres + ES (no backend/frontend services); real dev runs systemd from source; "production deployment" undefined; rollback impossible (no tags, no registry). nginx `proxy_pass http://backend:8080` hostname assumes a compose network that doesn't exist in the repo. Fix: compose services with health-gated depends_on, registry push with git-sha tags, release workflow per ADR-022.
- **D-H5. systemd units unmanaged, untracked** — `~/.config/systemd/user/quantumpacs-{backend,frontend}.service` not in repo; dev.sh `systemctl start || restart` swallows missing-unit errors; machine-specific paths (/home/dev, nvm v24.18.0). Fresh machine has no way to restore services. Fix: version units under `deploy/systemd/` + `scripts/install_units.sh`, fail loudly, `systemd-analyze verify` in CI.

### Medium
- **D-M1. npm audit effectively disabled; pip-audit version skew** — security.yml:34 `continue-on-error: true` hides the 21 known advisories (incl. ejs/jake build-time RCE chain); pip-audit runs Python 3.12 vs app 3.14. Fix: fail on critical, `--omit=dev`, pin 3.14.
- **D-M2. ci.yml no caching/concurrency/path filters** — every push runs 6 jobs, ~3 npm ci + 2 pip install from scratch; stale runs pile up; no docs-only skip. Fix: concurrency group + cancel-in-progress, `cache: 'npm'`, paths-ignore, branch filter mirroring security.yml.
- **D-M3. Trivy scan superficial** — `@master` unpinned, `scan-type: fs` backend only, `format: table`, no exit-code/severity gate (never fails), no frontend, no image scan. Fix: pin release tag, `--severity HIGH,CRITICAL --exit-code 1`, scan frontend + images.
- **D-M4. Frontend image runs nginx as root; no HEALTHCHECK on either app image** — backend Dockerfile has no healthcheck though docs/ops-guide.md:166 claims one. Fix: `USER nginx`, HEALTHCHECK on both (wget for slim/alpine).
- **D-M5. Hardcoded DB creds in version-controlled compose** — `POSTGRES_PASSWORD: pa55w0rd` (docker-compose.yaml:46) + same literal in backup_db.sh:6, setup_dev.sh, verify_config.sh. Fix: `${POSTGRES_PASSWORD:-...}` + gitignored .env.
- **D-M6. Frontend Docker build context unfiltered** — no frontend/.dockerignore (backend has one); `COPY . .` pulls node_modules/dist/e2e; stale dist bleed-through risk. Fix: .dockerignore (node_modules, dist, e2e, coverage, test).
- **D-M7. Generated "secret" is a hardcoded repo-visible constant** — `quantum-local-dev-secret-replace-in-prod-2026-07-28` embedded in dev.sh:43, verify_config.sh:30,62,64, setup_dev.sh:100,118,120; assert_production_secret would accept it. Fix: `openssl rand -hex 32` at first run; extend blocklist.
- **D-M8. config.local.yaml creation paths diverge** — verify_config.sh creates if missing; dev.sh's inline verify returns early if missing (dev.sh:21) → confusing failure on clean checkout. Fix: dev.sh calls verify_config.sh as single source.
- **D-M9. No alerting; health checks pull-based/manual** — /api/health rich (6 components) but no Prometheus/Grafana despite ADR-020; systemd Restart=always but no WatchdogSec/OnFailure; backup_db.sh timer "recommended" only. Fix: ship backup timer files, OnFailure units, scrapeable metrics.
- **D-M10. backup_db.sh drift-prone defaults** — hardcodes localhost:5432 + pa55w0rd; env uses 5433 when 5432 taken; silently backs up wrong DB. Fix: port discovery like dev.sh, DATABASE_URL, retention.
- **D-M11. Dev and "prod" run entirely different runtimes** — systemd source (Node 24, Python 3.14 venv) vs built images (Node 22, 3.14-slim) that never run; QUANTUMPACS_DOCKER=true config branches unexercised. Fix: full `docker compose up -d` smoke in CI.
- **D-M12. Pre-commit and CI run different test sets** — pre-commit pytest runs tests/ incl. integration (needs Postgres); CI ignores it. tsc hook needs pre-existing node_modules. Fix: mirror CI ignore list; npm ci in hook if missing.
- **D-M13. No rollback story** — zero tags, no registry, no release workflow; ops-guide has RTO/RPO table but no artifacts. Fix: git-sha tags, `git checkout <prev> && systemctl restart` runbook, quarterly restore drill script.

### Low
- **D-L1.** `npm ci` flags differ: CI plain vs Dockerfile `--legacy-peer-deps` — standardize.
- **D-L2.** Floating base tags (node:22-alpine, nginx:1.27-alpine, python:3.14-slim); pip install without hashes; ES pinned 9.4.4 (good).
- **D-L3.** Compose gaps: no mem_limit for postgres, no ulimits; local image untagged-with-sha; db_password duplicated across 3 scripts.
- **D-L4.** dev.sh `docker compose up -d 2>&1 || true` swallows real postgres failures; `cleanup_port` kills any process on 8080/11112; status uses inline Python.
- **D-L5.** Missing hygiene hooks (trailing-whitespace, end-of-file, check-yaml); eslint dead config.
- **D-L6.** package.json test:fast/test:slow/e2e:*/coverage/build scripts unused in CI; no lint script.

### Verified Good
- Backend Dockerfile: multi-stage, dedicated non-root `quantumpacs` user (uid 10001), nologin shell, chown'd
- docker-compose: restart unless-stopped, ES healthcheck (curl, retries 15, start_period 30s), pg_isready healthcheck, ES mem limits + ulimits, named volumes, ES pinned 9.4.4
- security.yml: branch filters, pip-audit fails build (no continue-on-error), push + PR
- ci.yml test-backend: real Postgres 16 service container with DB_HOST/DB_PORT wiring
- Pre-commit: ruff + ruff-format backend, prettier frontend/src, tsc, pytest, pre-push protected-branch guard (rare, CI-independent); ruff version matches CI exactly
- Health endpoints: two versioned, per-component status (db/redis/es/storage/dicom/ingestion) used by dev.sh status + verify_config.sh
- Self-healing scripts: port auto-detection, default-secret rejection, idempotent sed fixes (truncated-config incident genuinely handled)
- nginx SPA fallback (try_files) works for deep links
- backup_db.sh: pg_dump custom format, timestamped, DATABASE_URL override
- Vite test config: v8 coverage + thresholds configured (just never invoked), pool forks bounded
- config.local.yaml gitignored; env-var overrides; assert_production_secret at boot
