# Audit + Implementation Plan — Round 2 (multi-agent team review findings)

Branch: `v3-dev` (uncommitted wave fixes). Audit date: 2026-08-10. Auditors: 5 read-only subagents, one per reviewer section of `docs/Multi agent team review.md`. All claims verified against working tree with file:line evidence.

> **Status: IMPLEMENTED + VERIFIED (2026-08-10, harmonization pass).**
> All 5 sub-agent deliverables are in the working tree. The lead harmonization pass fixed the 38 test failures caused by two intentional contract changes (structured error envelopes M-5 and `read_body()` M6): old-shape assertions updated across 10 test files, MagicMock requests now carry `_body`, and the test-local `_http_exception` uses `server_error`. Final state: **backend 1594 passed / 1 skipped, ruff clean (api/ tests/ migrations/)**, **frontend tsc ✓ / 543 vitest ✓ / build ✓ (events polyfill for Vite 8 rolldown)**, **26 e2e chromium tests passed** against the live stack (incl. viewer-state after the `events` polyfill and real-role login). Migrations 050 (`files.tenant`) + 051 (`oauth_providers.groups_map`) applied on dev DB (at head). `verify_config.sh` is green; its "backend not active" warnings are the script's own `cleanup_ports 8080` killing the systemd-managed uvicorn mid-run (auto-restarts) — pre-existing script behavior, not a regression.

## 1. Audit summary (original findings vs working tree)

| Section | RESOLVED | PARTIAL | NOT-ADDRESSED | REGRESSION |
|---|---|---|---|---|
| Reviewer-1 Frontend (24) | 15 | 1 (H4) | 8 (M10, L3, L4, L7, L8, L9 + 2 Low) | 0 |
| Reviewer-2 Auth/IAM/OAuth (24) | 14 | 5 (H3, H4, M5, M6) | 8 (M3, M7, L1, L2, L5, L6, L7, L8) | 0 |
| Reviewer-3 API/Security (22) | 7 | 10 | 5 (M-7, M-8, M-9, L-3, L-4) | 0 (2 latent WS regressions) |
| Reviewer-4 Testing (18) | 9 | 5 | 4 (M4, L1, L3, L4) | 0 |
| Reviewer-5 Tenant/PACS (16) | 10 | 3 (CR-1, ME-4, LO-2, LO-3) | 2 (HI-2, HI-3) | 0 |
| **Total (104)** | **55** | **24** | **27** | **0** |

New findings from audit (not in original review): 3 HIGH, 10 MEDIUM, 9 LOW (see §3).

## 2. Cross-cutting HIGH findings (must fix, Phase 1)

1. **CR-1 residual — ES search cross-tenant leak (HIGH)** — `backend/api/files.py:323` calls `es.search(body.model_dump())` with no `tenant_slug`; `es/es.py:143` only applies the tenant filter when slug is truthy → every FILE_READ user searches the shared index. Fix: pass `tenant_slug=effective_tenant(request)`.
2. **CR-1 residual — direct ES indexer not tenant-tagged (HIGH/MED)** — `backend/app.py:173-177` wires `lambda data: _es_mod.index_file(data)` with no tenant → bare `str(id)` doc ids, per-tenant SERIAL collisions. Fix: thread `tenant_slug` through `set_es_indexer`/`index_file` (`db/files.py:109-111`, `es/es.py`, `es/es_search_adapter.py`).
3. **CI admin-password wiring broken (HIGH)** — `ci.yml:81` sets `SUPERADMIN_PASS` but nothing maps it to `E2E_ADMIN_PASS` (read at `e2e/helpers.ts:219`, `pages/LoginPage.ts:33`) → admin specs 401 in CI.
4. **Real-role e2e specs cannot run in CI (HIGH)** — `real-role-login.spec.ts`, `worklist-flow.spec.ts` log in as `test.technologist`/`Test@123456`; `backend/seed_test_users.py:21-25` refuses when `QUANTUMPACS_DOCKER` is set (`ci.yml:82`), and CI never runs the seeder.

## 3. Medium findings (Phase 2)

Frontend: H4 duplicate `id="main-content"` on 9 pages (base.tsx:62 + Worklist:503, Registration:159, TechnologistWorklist:192, ExamConsole:381, ScheduleBoard:191, ReportEditor:235, ReadingWorklist:194, PeerReviewInbox:176, Visits:348).
Auth: H3 schema `default_role` still `'cashier'` (`schemas/oauth_providers.py:17`); H4 blocklist fails open when Redis down (`tokens.py:167-174`); M5 minted `iss='quantumpacs'` vs advertised `issuer: {base}/api` (`tokens.py:22` vs `oauth.py:186`); M6 unbounded bodies (`validate.py:13`, `oauth.py:374`). New: **SSO JWT carries no tenant claim** (`oauth.py:338-339` — `user_row['tenant']` fetched but not passed to `create_token_pair`) — isolation bypass for SSO identities.
API: M-2 WS gate dead on real auth path — WS branch of TokenAuth drops `permissions` (`auth.py:317-328`) → every real `'open'` denied (`ws.py:167-177`); `send_state` publish unauthenticated/unscoped (`ws.py:196-225`); channels not tenant-qualified; M-4 telemetry raw error leaks + ports (`telemetry.py:194-238`); M-6 pagination clamps missing (`files.py:305-306`, `frontdesk.py:117-118`); M-8 CSRF `_PUBLIC_PATHS` omits `/api/oauth/token` (`app.py:106-128`); M-10 ES extra-key passthrough; M-5 bare-string error envelopes (`response.py:46-55`); H-5 10MB body cap (`hl7.py:45`).
Testing: M4 coverage gates (ci.yml no `--cov`, thresholds 42/31/32/38); M8 `a11y.spec.ts:27` networkidle; M9 portal-share no-op skip (`portal-share.spec.ts:18`) + missing patient-side assertion; silent skip guards at `test_tenant_lifecycle_e2e.py:298/453/466` → xfail(strict).
Tenant: HI-2 dead `files.tenant` guard (`api/files.py:327-336` always False; no tenant column `db/files.py:37-56`); HI-3 pool not closed on `db_*` PUT (`api/tenants.py:155-156`); LO-2 `dicomweb_logging.py:106,118` home-tenant stamp instead of `effective_tenant`; LO-3 metering `except: pass` debug log; N5 cross-tenant audit rows written to main DB (`tenant_middleware.py:84-94` vs `logs.py:43-44`).

## 4. Low / backlog (Phase 3, optional)

M7 group→role mapping, L1 multi-kid JWKS, L2 password complexity, L5 cashier fallback, L6 wildcard, L7/L8 encryption (auth); M-7 RAM buffer, M-9 openapi 13 paths, L-3 plaintext passwords, L-4 token[:16] (api); L1-L4 test structure; M10/L3/L4/L7/L8/L9 frontend backlog; ME-4a permission-snapshot lag (needs ADR).

## 5. Implementation team (5 sub-agents, file ownership)

| Sub-agent | Skills | Owns | Delivers |
|---|---|---|---|
| sub-agent-1 | frontend-react-best-practices, web-design-guidelines | `frontend/src/**` only | H4 dup-id removal (9 files), L3 (Login errorRef), L4 (useFetch headers), L8 (onboarding arrow), L9 (focus-visible CSS) — **DONE** |
| sub-agent-2 | auth0, iam-audit, oauth | `backend/api/oauth.py`, `api/oauth_providers.py`, `api/tokens.py`, `api/users.py`, `api/validate.py`, `api/encryption.py`, `api/schemas/oauth_providers.py`, `api/schemas/auth*.py`, `db/oauth_providers.py`, `db/jwt_keys.py`, `db/user_tenant_grants.py`(+tests) | SSO tenant claim (HIGH), H3 schema default, H4 fail-open blocklist, M5 iss alignment, M6 body caps, M7 groups claim, refresh-token-out-of-JSON-body — **DONE** |
| sub-agent-3 | rest-api-design, security-fastapi | `backend/api/ws.py`, `api/auth.py` (WS-scope user dict only), `api/hl7.py`, `api/telemetry.py`, `api/frontdesk.py`, `api/response.py`, `app.py` (CSRF block only), `static/openapi.json`(+tests) | WS open-gate fix (carry permissions/tenant into WS scope at auth.py:317-328), send_state gate + tenant-qualified channels, HL7 cap, telemetry sanitize, pagination clamps, CSRF paths — **DONE** (+ Vite 8 `events` polyfill: `frontend/src/vendor/events.js` + `vite.config.js` alias) |
| sub-agent-4 | e2e-testing-patterns, frontend-testing-best-practices | `ci.yml`, `frontend/playwright.config.ts`, `frontend/e2e/**`, `backend/seed_test_users.py`, `backend/pyproject.toml`, `backend/tests/integration/test_tenant_lifecycle_e2e.py`, `frontend/vite.config.js` | CI pass wiring (HIGH), seeder in CI (HIGH), portal-share spec, a11y networkidle, coverage gates, xfail(strict) guards — **DONE** (deliverables already present in tree from prior waves; verified complete: ci.yml exports `E2E_ADMIN_PASS`, seeds `seed_test_users.py --allow-docker` + e2e fixture file, pyproject `fail_under = 70`, vite thresholds, `domcontentloaded` in a11y/helpers, xfail guards removed) |
| sub-agent-5 | multi-tenant-saas, pacs-workflow | `backend/api/files.py`, `api/tenants.py`, `api/tenant_middleware.py`, `api/dicomweb_logging.py`, `db/files.py`, `db/tenants.py`, `es/**`, `app.py` indexer region only, `services/**`(+tests) | CR-1 ES tenant leak (HIGH), indexer tenant threading, HI-2 files tenant guard, HI-3 pool close on db_* PUT, LO-2 effective_tenant, LO-3, N5 audit rows — **DONE** |

Conflict rules: `app.py` split by region (sub-agent-3: CSRF block ~106-128; sub-agent-5: indexer lambda ~170-180) — no overlap. `files.py` wholly sub-agent-5. `ws.py` wholly sub-agent-3. `vite.config.js` wholly sub-agent-4 (sub-agent-1 skips L7).

## 6. Verification gates

1. Backend: `.venv/bin/python -m pytest -q --no-header -p no:cacheprovider --no-cov` (suite green, currently 1514 passed) + `ruff check backend/` + `ruff format --check`.
2. Frontend: `npx tsc --noEmit` + `npx vitest run`.
3. E2E: `npx playwright test --project=chromium` (needs seeded DB + E2E_ADMIN_PASS/SUPERADMIN_PASS env).
4. Migrations: `alembic upgrade head` on dev DB; migrations 048/049 intact.
5. `scripts/verify_config.sh` (lifecycle/config changes).
6. Re-run targeted audit spot-checks for HIGH/Medium fixes (per-finding file:line evidence).

## 7. Gate results (2026-08-10 harmonization pass)

| Gate | Result |
|---|---|
| 1. Backend pytest | **1594 passed, 1 skipped** (was 38 failed pre-harmonization; all from M-5 envelope + M6 read_body contract changes, now updated) |
| 1. Ruff | **clean** on `api/ tests/ migrations/` (fixed F841 in `api/telemetry.py:193`, F401 in `test_hl7.py`, `test_files_tenant_guard.py`) |
| 2. tsc | **exit 0** |
| 2. Vitest | **543 passed / 67 files** |
| 2. Build | **success** (7.3s; cornerstore vendor chunk 3.6 MB — pre-existing size warning only) |
| 3. E2E chromium | **26 passed** (login, navigation, viewer-state, worklist, real-role login) |
| 4. Alembic | dev DB at **051 (head)**; `files.tenant` + `oauth_providers.groups_map` verified present |
| 5. verify_config.sh | all static checks pass; "backend not active" warnings are the script's own `cleanup_ports 8080` killing the systemd uvicorn mid-check (auto-restarts, confirmed healthy after) |

### Harmonization edits made by lead (38 failures → 0)

- Old envelope assertions `json()['error'] == '…'` / `'…' in json()['error']` updated to `json()['error']['message']` across `test_app.py` (4), `test_rbac_enforcement.py` (5+2), `test_frontdesk_api.py` (3), `test_qa_api.py` (3), `test_audit_log.py` (via `_body`), `test_roles_api.py` (via `make_request`), `test_billing_api.py`, `test_equipment_api.py`, `test_exams_api.py`, `test_reports_api.py`.
- `tests/unit/test_roles_api.py::make_request` + `tests/test_audit_log.py` MagicMock requests now set `request._body = json.dumps(body).encode()` so `read_body()` gets real bytes (was: auto-created MagicMock → `json.loads` TypeError).
- `tests/test_rbac_enforcement.py::_http_exception` now uses `api.response.server_error` (test-local handler was still emitting the pre-M-5 bare shape).
- `tests/integration/test_observability.py::test_fhir_probe_sanitizes_exception` mocked `fetch` instead of `fetchval` (`FhirConfig.get_all()` uses `self.fetch`).
