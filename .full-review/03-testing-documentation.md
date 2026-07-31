# Phase 3: Testing & Documentation Review

## Test Coverage Findings

| Severity | Count | Key Areas |
|----------|-------|-----------|
| **Critical** | 3 | SQL injection test gaps (FHIR _quote()), token version invalidation untested, encryption fallback logging untested |
| **High** | 6 | Redis fallback untested, WebSocket pubsub untested, app.py middleware/CORS untested, routing engine untested, storage adapters (B2/S3/local) untested, module globals isolation |
| **Medium** | 4 | E2E test skeleton missing, no conftest fixture consolidation, load tests target frontend not backend, migration/tenant tests missing |
| **Low** | 3 | DICOM C-MOVE/C-GET stubs untested, ES graceful disable untested, Worker shutdown edge case |
| **Total** | **16** | |

### Critical Gaps
1. **SQL injection vectors never probed**: FHIR `_quote()` function (`api/fhir.py:145,452,456`) and OAuth role SQL (`api/oauth.py:144`) — no injection test cases exist. Tests mock the DB layer entirely, so injection would never surface.
2. **Token version invalidation untested**: `api/auth.py:198-200` compares `jwt_version` vs DB `token_version` — no test covers this path.
3. **Encryption failure logging unchecked**: `api/encryption.py` silently returns plaintext on Fernet failure — no test asserts that `log.warning` is called.

### Coverage Ratio
- ~85 test files covering ~65% of source files
- Unit: ~55 files (65%) — good
- Integration: ~17 files (20%) — adequate but heavily mocked
- E2E: 0 files — **MISSING** (no test spins up full stack)
- Load: 3 JS (k6) files — frontend-focused, no backend API load tests

### Test Quality Issues
- 5-6 levels of nested `with patch(...)` blocks in many integration tests
- Module-level globals (`_active_cache`, `local_clients`, `_fernet`) shared across tests — isolation risk
- `_FakeAuth`, `_make_app()`, `_mock_conn()` redefined in every test file — no shared conftest fixtures
- Mirror of E2E (`integration.spec.ts`) uses backend's `/health` endpoint; back-end has no E2E tests at all

## Documentation Findings

| Severity | Count | Key Areas |
|----------|-------|-----------|
| **Critical** | 2 | OpenAPI spec covers <20% of endpoints; no CHANGELOG or UPGRADING.md exists |
| **High** | 4 | README metrics inaccurate (says 13 ADRs, actual 22); ADR index missing ADRs 014-022; SECURITY_AUDIT.md describes already-fixed issues; API schemas lack field-level descriptions |
| **Medium** | 7 | 70% of modules lack docstrings; no DATA_DICTIONARY.md; migration docstrings too brief; README missing 40+ config keys; REST_API_REVIEW recommendations untracked; DICOM server zero inline docs; no observability runbooks |
| **Low** | 2 | Admin guide references deprecated RPC endpoints; persona flows lack ADR cross-references |
| **Total** | **15** | |

### Critical Gaps
1. **OpenAPI spec (`backend/static/openapi.json`)**: 13 paths documented out of 50+ registered routes. Missing FHIR, DICOMweb, HL7, OAuth, worklist, routing, webhooks, tenants, roles. All response schemas are generic `object` — no error schema defined.
2. **No CHANGELOG or upgrade guide**: Despite 33 Alembic migrations, multiple breaking changes, and v2→v3 evolution, zero release documentation exists.

### Documentation Quality Issues
- Pydantic models in `api/schemas/` (16 files) have zero `Field(description=...)` — root cause of poor OpenAPI spec
- Only 7 of ~40 backend modules have proper module-level docstrings (`log.py`, `response.py`, `validate.py`, `auth.py`, `ratelimit.py`, `database.py`, `conn.py`)
- README config table documents 10 of 55 config keys — 80% invisible to operators
- SECURITY_AUDIT.md lists 3 findings as "Open" that are already fixed in code
- Migration docstrings are single-line — no why, data migration, or rollback info
