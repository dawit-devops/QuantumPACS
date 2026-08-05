# ADR-021: Testing Strategy — Integration-First + IHE Conformance + Load Gates

## Status
Accepted

## Date
2026-07-25

## Context

QuantumPACS v2.0 testing debt is severe (from `docs/PRODUCTION_READINESS_REVIEW.md`):

- **No integration tests**: 8 of 12 DB tables have zero tests. The only tests are unit tests that mock the database connection. No test exercises a real asyncpg query.
- **Flaky tests**: `time.sleep` in ratelimit tests, shared mutable `Table.tables` state across test modules, `importlib.reload()` in config tests.
- **No E2E tests**: Only the frontend has Playwright E2E (3 specs). Backend has no HTTP-level E2E tests.
- **No load tests**: No performance baseline. No CI load gate.
- **No conformance tests**: DICOM and DICOMweb standards conformance is untested.
- **No isolation tests**: Multi-tenant data isolation is untested.

The production readiness review identified 12 critical issues, many of which would have been caught by integration tests with a real database.

The v3.0 PRD specifies measurable test coverage targets:
- Backend integration coverage: ≥ 80%
- Frontend component coverage: ≥ 60%
- E2E critical flows: ≥ 10 Playwright specs
- Load test gates: p95 < 300ms at 50 RPS
- Security gates: 0 critical ZAP findings, 0 critical CVEs

## Decision

Adopt an **integration-first testing strategy** for v3.0. Specifically:

### 1. Test Pyramid (v3)

```
          ╱╲
         ╱  ╲           E2E (10 Playwright specs)
        ╱    ╲
       ╱────────╲       Integration (≥80% coverage)
      ╱          ╲
     ╱──────────────╲   Unit (fast, high-volume, no DB/Redis)
```

**Shift left to integration.** Every new v3 feature starts with an integration test that exercises real infrastructure (PostgreSQL, Redis, storage backends). Unit tests remain for pure logic (token encoding, DICOM tag parsing, permission evaluation) but the emphasis is on integration.

### 2. Infrastructure

| Component | Test Fixture | Library |
|-----------|-------------|---------|
| PostgreSQL | Ephemeral PG in Docker (or `testcontainers-postgres`) | `pytest-asyncio` + `asyncpg` |
| Redis | Ephemeral Redis via `testcontainers` or `aioredis` in-memory mode | `aioredis` |
| Storage backends | `TempDirStorage` (in-memory + tempfile) implementing the same interface | `pytest` `tmp_path` fixture |
| DICOM files | Synthetic DICOM file with known metadata | `pydicom` Dataset creation |
| DICOMweb client | `httpx.AsyncClient` against test server | `httpx` |
| OAuth IdP | Mock OIDC provider (httpx mock or local IdP) | `responder` or `respx` |

### 3. Test Organization

```
backend/tests/
├── conftest.py              # Global fixtures: test_db, test_redis, test_client, test_tenant
├── unit/                    # Fast unit tests (no DB, no Redis)
│   ├── test_tokens.py       # Existing, maintained
│   ├── test_validate.py     # Existing, maintained
│   ├── test_response.py     # Existing, maintained
│   ├── test_utils.py        # Existing, maintained
│   ├── test_rbac_permissions.py  # NEW: permission evaluation logic
│   └── test_dicom_tags.py   # NEW: tag parsing edge cases
├── integration/             # Integration tests (real DB, real Redis)
│   ├── test_api_v2_auth.py  # NEW: OAuth, local JWT, token blocklist
│   ├── test_api_v2_files.py # NEW: file upload, search, download via v2 API
│   ├── test_api_v2_tenants.py   # NEW: tenant provision, decommission, isolation
│   ├── test_api_v2_rbac.py      # NEW: role CRUD, permission enforcement
│   ├── test_dicomweb_qido.py    # NEW: QIDO-RS search
│   ├── test_dicomweb_stow.py    # NEW: STOW-RS store
│   ├── test_dicomweb_wado.py    # NEW: WADO-RS retrieve
│   ├── test_dicomweb_conformance.py  # NEW: IHE test suite assertions
│   ├── test_dicom_mwl.py        # NEW: MWL C-FIND
│   ├── test_dicom_cmove.py      # NEW: C-MOVE SCP
│   ├── test_hl7_adt.py          # NEW: ADT ingestion
│   ├── test_hl7_orm.py          # NEW: ORM → MWL mapping
│   ├── test_fhir_patient.py     # NEW: FHIR Patient resource
│   ├── test_fhir_imagingstudy.py    # NEW: FHIR ImagingStudy resource
│   ├── test_redis_streams.py    # NEW: Stream producer/consumer
│   ├── test_tenant_isolation.py # NEW: property-based isolation fuzz
│   ├── test_routing_rules.py    # NEW: study routing rule engine
│   └── test_observability.py    # NEW: health, metrics, structured logging
├── load/                   # Load test scripts
│   ├── study_search.js     # k6: QIDO-RS search
│   ├── dicom_store.js      # k6: C-STORE load
│   ├── dicomweb_store.js   # k6: STOW-RS upload
│   ├── viewer_sessions.js  # k6: WebSocket viewers
│   └── auth_flow.js        # k6: OAuth login flow
├── e2e/                    # (frontend has Playwright)
└── test_*.py               # Existing unit tests (maintained, not moved)
```

### 4. Coverage Gates

Enforced in CI via `--cov-fail-under`:

| Gate | Target | Command |
|------|--------|---------|
| Backend integration coverage | ≥ 80% | `pytest tests/integration/ --cov --cov-fail-under=80` |
| Backend total coverage | ≥ 70% | `pytest tests/ --cov --cov-fail-under=70` |
| Frontend function coverage | ≥ 60% | `vitest run --coverage --coverage.threshold.functions=60` |

Coverage is measured by line coverage for integration tests and function coverage for frontend.

### 5. E2E Tests (Playwright)

10 critical flows (from `IMPLEMENTATION_PLAN-v3.md` F7.6):

1. Login (local JWT) → search → open study → scroll slices → logout
2. OAuth login (mocked IdP) → verify role-based sidebar
3. Super admin provisions new tenant → verifies in dashboard
4. Admin creates custom role → assigns → user exercises permission
5. C-STORE upload → search → viewer
6. STOW-RS upload → verify same as C-STORE
7. HL7 ADT → FHIR Patient search
8. MWL C-FIND → verify worklist entry
9. Share link → incognito view
10. Mobile viewport: login → search → viewer

### 6. Load Test Gates

k6 scenarios run nightly (not on every commit, but on merge to main):

| Scenario | Target | Threshold |
|----------|--------|-----------|
| QIDO-RS search (10k studies) | 50 RPS | p95 < 500ms |
| C-STORE store (50 concurrent) | 150 MB/s | 0 errors |
| STOW-RS store (50 concurrent) | 50 RPS | p95 < 1s |
| WebSocket viewers (200 concurrent) | 200 conn | p95 < 100ms msg latency |
| Auth flow (10 RPS) | 10 RPS | p95 < 2s |

### 7. Security Scan Gates

| Tool | Frequency | Gate |
|------|-----------|------|
| OWASP ZAP baseline | Every merge to main | 0 high-risk findings |
| `pip-audit` | Every merge to main | 0 high-severity CVEs |
| `npm audit` | Every merge to main | 0 high-severity CVEs |
| Bandit (Python SAST) | Every merge to main | 0 high-confidence findings |

### 8. IHE Conformance

DICOMweb conformance is verified via:
1. **Self-certification test suite** — Run the IHE DICOMweb Test Tool against `/api/v2/dicomweb/*` endpoints. Converted to pytest tests that run in CI.
2. **IHE Connectathon** — Register for the next available Connectathon (target: Q1 2027 or Q3 2027). Pass the "Web Access to DICOM Objects" (WADO) and "Cross-Enterprise Document Sharing" profiles.
3. **Integration E2E** — The conformance tests are run as part of the nightly load test suite, ensuring no regression breaks DICOMweb compliance.

## Consequences

### Positive

- **Catch regressions early**: Integration tests with real DB catch the class of bugs that v2's unit-only tests missed (12 critical issues).
- **Confidence to refactor**: The modular monolith (ADR-014) can be safely refactored because integration tests verify behavior, not implementation.
- **Load baseline**: k6 nightly runs provide a performance trend. Regressions (p95 increases >20%) trigger alerts before reaching production.
- **Security baseline**: OWASP ZAP and dependency audits in CI prevent known-vulnerability regressions.

### Negative

- **CI time increase**: Integration tests with testcontainers take longer than pure unit tests. Estimated: 5–8 minutes (vs 30 seconds for unit-only). Mitigation: parallelism in pytest, fixture scoping (session-scoped DB/Redis), mtime-based test selection.
- **Testcontainers dependency**: CI requires Docker for testcontainers (PostgreSQL + Redis containers). Mitigation: CI runners already have Docker; fallback to external test DB for non-Docker CI.
- **Flaky test risk**: Integration tests with real infrastructure can flake (network timeouts, container startup delays). Mitigation: retry fixtures (3 attempts with backoff), health-check before test start.
- **Load test infra**: k6 scenarios require a staging environment with realistic data (10k+ studies). Mitigation: seed script creates test dataset; same script runs locally and in CI.

## References

- PRD-v3.md §6 — Success Evaluation (v3 Gates)
- IMPLEMENTATION_PLAN-v3.md Phase 7 — Verification
- Production Readiness Review (docs/PRODUCTION_READINESS_REVIEW.md) — §4.4 Testing Debt
- "Practical Test Pyramid" — Martin Fowler, 2018 (https://martinfowler.com/articles/practical-test-pyramid.html)