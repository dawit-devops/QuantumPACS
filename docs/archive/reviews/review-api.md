# REST API Review — QuantumPACS

- **Reviewer role**: API design specialist
- **Skill applied**: `rest-api-design` (resource modeling, status codes, envelopes, pagination, versioning)
- **Scope**: `backend/api/routes.py`, `backend/api/response.py`, `backend/api/validate.py`, handler modules, `API_CONTRACT.md`
- **Date**: 2026-08-03
- **Verdict**: Good REST discipline — plural resources, nested sub-resources, action verbs for non-CRUD operations, consistent auth, and an automated versioning mechanism. Main issues are envelope inconsistency and unbounded pagination.

---

## 1. Strengths

| Area | Observation |
|---|---|
| Resource modeling | Plural collections (`/users`, `/exams`, `/qa/incidents`), nested (`/files/{id}/shares`, `/exams/{id}/acquisitions/{aid}/decision`), action verbs for state transitions (`/exams/{id}/complete`, `/reports/{exam_id}/sign`, `/qa/incidents/{id}/resolve`) — clean REST+RPC hybrid. |
| Versioning | Dual-prefix mechanism (`routes.py:84-87`, `_build_v2_aliases`) mirrors every `v2()`-marked route under `/api/v2/*` without drift-prone duplication; alias paths are excluded correctly (`_V2_EXCLUDE_PREFIXES`). |
| Validation | Pydantic v2 schemas with structured 422 `VALIDATION_ERROR` details (`validate.py:38-46`); malformed/empty JSON yields 422, never 500. |
| Authn/Authz | Permission-gated endpoints via `@requires_permission` (`api/rbac.py`), API keys, OAuth/OIDC, rate-limited login. |
| Docs | `docs/API_CONTRACT.md`, static OpenAPI spec, versioning contract test (`test_api_versioning.py`). |

---

## 2. Findings

### A1 (Medium) — Two conflicting error-response shapes
`api/response.py`: `not_found`/`unauthorized`/`forbidden`/`validation_error` return `{"error": "<string>"}`, while `api_error` returns `{"error": {"code", "message", "details"}}`. `validate.py` raises 422 through the structured shape; handlers mix both (e.g., `exams.py` imports both `not_found` and `validation_error`, and `api_error`).
- **Scenario**: Any client that parses `error` as an object breaks on a 404; any client that expects a string breaks on 422. Every handler author must remember which shape to use.
- **Recommendation**: Standardize on `api_error` (code/message/details) for all error paths; keep the string helpers only if the contract explicitly documents them as legacy v1.

### A2 (Medium) — Pagination is unbounded (deep offsets, huge pages)
`api/response.py:93-114`: `paginated()` accepts any `page`/`per_page` from the query string. `?per_page=1000000` produces a multi-MB payload and an expensive `LIMIT`; `?page=9999999` forces a deep offset scan (O(offset) on PostgreSQL).
- **Scenario**: A careless client or a crawler hits `/api/files?page=100000&per_page=50000` → heavy DB scans and memory spikes.
- **Recommendation**: Clamp `per_page` (e.g., max 200) and `page` (e.g., max 10000), and document; consider keyset pagination for the largest collections (`files`, `logs`).

### A3 (Low) — 204 responses carry a body
`api/response.py:40-42`: `no_content()` returns `{}` with status 204. HTTP 204 must have no body; most clients drop it, but some tooling/fetch implementations warn or mishandle it.
- **Recommendation**: Return `Response(status_code=204)`.

### A4 (Low) — Public-path lists are duplicated in three places
`TokenAuth._PUBLIC_PATHS` (`auth.py:139-158`), `CSRFMiddleware._PUBLIC_PATHS` (`app.py:104-111`), and route-level decisions all enumerate public endpoints independently.
- **Scenario**: Adding a new public endpoint (e.g., a password-reset flow) and forgetting one of the lists → 401s or CSRF 403s in production only after a subtle session-type mismatch.
- **Recommendation**: Single source of truth (e.g., module-level `PUBLIC_PATHS` imported by both) + a contract test that asserts every public route is present in both lists.

### A5 (Low) — Versioning placement is inconsistent in a few spots
`routes.py:150,213`: `/api/v2/wado` and `/v2/dashboard/metrics` are hardcoded as standalone routes while everything else is alias-generated; `/docs` and `/docs/openapi.json` are unversioned. Harmless functionally, but the contract's "all endpoints exist under both prefixes" claim has exceptions a client can't infer.
- **Recommendation**: Move `dashboard/metrics` into the `v2()` convention or document the exceptions in `API_CONTRACT.md`.

### A6 (Low) — Static OpenAPI spec can drift from implementation
`routes.py:77-78` serves `static/openapi.json` as a static file. With ~100 endpoints, hand-maintained specs go stale; the existing `test_api_versioning.py` pattern could be extended to assert the spec's route set matches `routes.py`.

### A7 (Info) — No `X-RateLimit-*` response headers
Rate limiting exists (login, API keys) but clients can't observe quotas (429 has no `Retry-After`). Not a defect; worth adding for API-key consumers.

### A8 (Info) — Permissions ride inside the JWT
`requires_permission` reads `user.permissions` from the token claims (`rbac.py:17`), so permission changes take effect only after the next refresh (≤1h for v2). Acceptable; note in contract.

---

## 3. Recommendations (priority order)

1. **A1** — unify error envelopes (one `error: {code, message, details}` shape).
2. **A2** — clamp pagination bounds (quick win against accidental load).
3. **A4** — centralize public-path lists with a contract test.
4. **A3/A5/A6** — clean-up items; low effort, real polish.

*Reviewed with skill: `rest-api-design` — naming, status codes, envelope, pagination, versioning sections applied.*
