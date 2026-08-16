# QuantumPACS v3.0 — Implementation Plan

**Derived from:** `docs/PRD-v3.md`
**Prerequisite:** `docs/IMPLEMENTATION_PLAN.md` (Production Hardening S0–S8)
**Total phases:** 9 (Phase 0 = existing hardening + 8 new phases)
**Estimate:** 30–40 weeks from Phase 0 completion
**Parallel tracks:** Up to 4 concurrent agents per phase

---

## Dependency Graph

```
Phase 0: Hardening ─────────────────────────────────────────  (see IMPLEMENTATION_PLAN.md)
  │
  ▼
Phase 1: Foundation ✅ ────────────────────────────────────  (Redis Streams, module boundaries)
  │
  ▼
Phase 2: Auth & Tenancy ✅ ────────────────────────────────  (DB-per-tenant, OAuth, RBAC)
  │
  ├──────────────────────────────────────┐
  ▼                                      ▼
Phase 3: DICOM Core                 Phase 4: Integration
  (MWL, C-MOVE, DICOMweb)              (HL7 MLLP, FHIR R4)
  │                                      │
  └──────────┬───────────────────────────┘
             ▼
        Phase 5: Observability ─────────────────────────────  (Prometheus, OTLP, JSON logs)
             │
             ▼
        Phase 6: Frontend v3 ───────────────────────────────  (RBAC UI, tenant switcher, OAuth, mobile)
             │
             ▼
        Phase 7: Verification ──────────────────────────────  (k6 nightly, IHE, OWASP, dep audit)
             │
             ▼
        Phase 8: v1→v2 Migration ───────────────────────────  (dual-write, dep headers, docs)
             │
             ▼
        v3.0 GA ●
             │
             ▼
        Phase 9: v3.1 RIS ──────────────────────────────────  (scheduling, worklist, reporting, portal)
```

---

## TDD Workflow

Every feature in Phases 1–8 follows the vertical-slice TDD pattern established in the TDD skill:

```
RED:   Write one integration test for the behavior → test fails
GREEN: Write minimal code to pass → test passes
REFACTOR: Clean up, deepen modules, run tests after each change
```

**Test location conventions:**
- Integration tests for Phase 1–2 (infrastructure): `backend/tests/integration/test_redis_streams.py`, etc.
- Integration tests for Phase 3–4 (DICOM, HL7, FHIR): `backend/tests/integration/test_dicomweb.py`, etc.
- API endpoint tests: `backend/tests/integration/test_api_v2_*.py`
- Auth/RBAC tests: `backend/tests/integration/test_auth_v2.py`, `backend/tests/integration/test_rbac.py`
- Frontend tests per file: `frontend/src/<module>/<Component>.test.tsx`

**Test fixtures:**
- `conftest.py` at `backend/tests/` provides async fixtures:
  - `test_db` — temporary PostgreSQL database (via testcontainers or ephemeral PG)
  - `test_redis` — ephemeral Redis instance (via testcontainers)
  - `test_client` — Starlette TestClient authenticated as specific roles
  - `test_tenant` — provisioned test tenant with known data
  - `test_dicom_file` — synthetic DICOM file with known metadata

**Coverage gates:**
- Backend: `pytest --cov --cov-fail-under=80`
- Frontend: `vitest run --coverage --coverage.threshold.functions=60`

---

## Phase 0 — Production Hardening (Prerequisite)

**Reference:** `docs/IMPLEMENTATION_PLAN.md` (Sprints 0–8)
**Effort:** 9 sprints, ~15–25 engineer-days
**Gate:** All 12 critical and 32 high-severity findings fixed. Backend tests pass with `-W error::Warning`.

No v3 feature work begins until Phase 0 is complete. The hardening work is tracked in the existing `IMPLEMENTATION_PLAN.md` and is not duplicated here.

---

## Phase 1 — Foundation ✅ (Completed Jun 2026)

### Objective
Lay the infrastructure that all v3 features depend on: Redis Streams message bus, modular monolith internal service boundaries, tenant registry database, and the OpenTelemetry instrumentation foundation.

### Status: COMPLETE — All infrastructure in production

### As-Built Features

#### F1.1: Redis Streams Message Bus ✅
- `backend/redis_streams.py` with `StreamProducer` and `StreamConsumer` classes wrapping `aioredis`
- Streams: `events:ingestion`, `events:sync`, `events:notify`, `events:auth` with `maxlen=100000`
- `PgNotifyBridge` subscribes to PostgreSQL NOTIFY `events` channel and publishes to Redis Streams
- Consumer group lag gauges exposed via Prometheus at `/api/v2/metrics`
- Integration tests: `tests/integration/test_redis_streams.py`, `tests/integration/test_pg_notify_bridge.py`

#### F1.2: Modular Monolith Service Boundaries ✅
- Service interfaces defined as Protocols in `services/` package: `MetadataService`, `StorageService`, `SearchService`, `AuthService`, `NotificationService`
- `ServiceRegistry` class with `register()`/`get()` — initialized in `app.py` lifespan, injected via middleware into `request.state.services`
- Ingestion service scaffold at `services/ingestion/` with its own main entry point, subscribes to `events:ingestion`
- Integration tests: `tests/integration/test_ingestion_worker.py`, `tests/unit/test_service_registry.py`, `tests/unit/test_service_middleware.py`

#### F1.3: Tenant Registry Database ✅
- `tenants` table with schema matching plan spec (id, name, slug, domain, db_name, db_host, db_port, db_user, db_password, status, storage_quota/used, created/updated)
- `TenantProvisioner.provision()` — creates PG database, runs Alembic migrations, inserts registry row
- `TenantConnectionPool` singleton with per-tenant lazy pools, TTL-based eviction
- `TenantMiddleware` extracts tenant from `X-Tenant-ID` header, JWT claim, or domain
- Integration tests: `tests/integration/test_tenant_provisioner.py`, `tests/integration/test_tenant_lifecycle.py`, `tests/test_tenancy_gate.py`

#### F1.4: OpenTelemetry Foundation ✅
- OTel middleware installed in `app.py` with `opentelemetry-instrumentation-starlette`
- Spans exported via `OTEL_EXPORTER_OTLP_ENDPOINT` (console in dev, collector in prod)
- W3C Trace Context propagation across Redis Stream producer→consumer boundary and asyncpg queries
- Integration tests: `tests/integration/test_tracing.py`, `tests/test_tracing.py`

### Phase 1 Gate (Passed)

```bash
cd backend && python -m pytest tests/ -v --tb=short  # all tests pass
```

---

## Phase 2 — Auth & Tenancy ✅ (Completed Jul 2026)

### Objective
Replace the v2 `admin` boolean with full RBAC, add OAuth/OIDC SSO, and make all auth flows tenant-aware.

### Status: COMPLETE — All features implemented and hardened

Phase 2 infrastructure was built incrementally on the `v3-dev` branch, then audited and hardened in a dedicated `phase/2-auth-tenancy` sprint. Below is the as-built summary.

### As-Built Features

#### F2.1: RBAC Model ✅
- `roles` table with permissions JSONB, built-in flag, tenant_id; `users.role_id` FK, `oauth_sub`, `groups` JSONB
- `Permission` enum in `api/permissions.py` with 21 permissions across FILE/USER/REPLICA/LOG/TENANT/ROLE domains
- `@requires_permission` decorator on all v2 routes via `api/rbac.py`
- Role CRUD: `GET/POST /api/v2/roles`, `PUT/DELETE /api/v2/roles/{id}` in `api/roles.py`
- 7 built-in roles seeded via `db/roles.py:seed_built_in_roles()` (runs on startup + migration `008_rbac_roles.py`)

#### F2.2: OAuth/OIDC Provider Integration ✅
- `oauth_providers` table with pre-configured OIDC providers; CRUD at `api/v2/oauth/providers`
- `GET /api/oauth/login?idp=<slug>` → PKCE authorization redirect to IdP
- `GET /api/oauth/callback?code=...&state=...` → token exchange, JWKS verification, JIT user provision
- `POST /api/oauth/token` → token exchange endpoint
- `GET /api/.well-known/openid-configuration` → OIDC discovery document
- Redis-backed state management with 5-minute TTL
- **A1 fix:** `/api/oauth/token` route was pointing to wrong handler (`oidc_discovery`); fixed to `oauth_token_exchange` with `methods=['POST']`
- **A2 fix:** `oauth_callback` tuple unpacking crash — `_find_or_create_user` returns 2 values, handler expected 3
- **A3 fix:** `OAuthProviders.create()` NOT NULL violation on `slug` — auto-generated from issuer hostname via `_slug_from_issuer()`; added `slug` and `default_role` to create/update schemas
- **B1 fix:** `client_secret` encrypted at rest using Fernet (AES-256-GCM) via `api/encryption.py`; key derived from `oauth_secret_encryption_key` config

#### F2.3: DB-per-Tenant Connection Routing ✅
- `TenantConnectionPool` (singleton) with per-tenant pool lifecycle — lazy create, TTL-based eviction
- `TenantMiddleware` resolves tenant from `X-Tenant-ID` header, JWT `tenant` claim, or domain
- Tenant isolation enforced via `TenantGate` middleware — cross-tenant queries rejected
- `TenantAlembic` wrapper supports `target_metadata` per tenant database

#### F2.4: JWT Enhancements ✅
- JWT carries `role`, `permissions`, `tenant`, `jti`, `token_version` claims
- Token blocklist via Redis (db=1) — logout, password change, role change blocklist affected tokens
- Refresh token flow: `POST /api/auth/refresh` — rotates access+refresh tokens, blocklists old refresh
- **B2 fix:** `token_version` mechanism — `users.token_version INTEGER DEFAULT 0` (migration `024`); incremented on role/permission change, deactivation; auth middleware compares JWT `token_version` vs DB — rejects on mismatch with `AuthenticationError('Token invalidated')`

#### F2.5: Tenant Admin UI (Backend) ✅
- `GET/POST /api/v2/tenants`, `DELETE /api/v2/tenants/{id}` — super admin CRUD
- `GET /api/v2/tenants/{id}/stats` — storage used, user count, study count, last activity
- **C2 fix:** `TenantStatsHandler` used master DB password instead of tenant-specific `db_password`; added `Tenants.get_connection_info()` returning full row dict

### Phase 2 Audit & Hardening Sprint

A deep-dive audit of Phase 2 revealed 10 gaps across 3 priority levels:

| Priority | Count | Description |
|----------|-------|-------------|
| P0 (crash) | 3 | Route miswired, tuple unpacking crash, NOT NULL violation |
| P1 (functional) | 2 | Missing schema fields, plaintext secrets at rest |
| P2 (consistency) | 5 | Stale seed data, wrong DB password, cache bypass, token invalidation missing, etc. |

Fixes delivered in 7 vertical-slice sprints over 2 days:

| Sprint | Fix | Files Changed |
|--------|-----|---------------|
| A1 | `/api/oauth/token` route handler + method | `api/routes.py`, `api/oauth.py`, `tests/test_oauth.py` |
| A2 | `oauth_callback` tuple unpacking | `api/oauth.py`, `tests/test_oauth.py` |
| A3 | `OAuthProviders.create()` auto-slug + schema fields | `db/oauth_providers.py`, `api/schemas/oauth_providers.py`, `api/oauth_providers.py`, `tests/test_oauth_providers.py` |
| B1 | `client_secret` encryption at rest | `api/encryption.py`, `config.py`, `db/oauth_providers.py`, `api/oauth.py`, `tests/test_encryption.py` |
| B2 | `token_version` invalidation mechanism | `db/users.py`, `api/tokens.py`, `api/auth.py`, `api/users.py`, `api/oauth.py`, `api/roles.py`, `migrations/024_token_version.py`, `tests/` |
| C1 | Sync migration 008 seed data with code | `migrations/versions/008_rbac_roles.py` |
| C2 | `TenantStatsHandler` per-tenant password | `db/tenants.py`, `api/tenants.py` |

### Phase 2 Gate (Passed)

```bash
cd backend && python -m pytest tests/ -v --tb=short  # 623 passed
```

---

## Phase 3 — DICOM Core (Completed Jul 2026)

### Objective
Harden the DICOM infrastructure: fix P0 crash blockers, close P1 functional gaps, and deliver P2 quality improvements across C-STORE, WADO-URI, C-MOVE/C-GET, and the DICOM pipeline.

### Status: COMPLETE — All P0, P1, and P2 audit findings fixed

### As-Built Features

#### F3.1: C-STORE Reliability ✅
- **A1 fix:** `_start_dicom()` sets `_dcm_server._loop = asyncio.get_running_loop()` with `RuntimeError` fallback — eliminates `_loop is None` crash on reconnection
- **A2 fix:** Deduplication — `store_instance()` calls `Files.get_by_hash(hsh)` before UUID generation, returns early on hash match
- **A3 fix:** Migration `025_fix_notify_event.py` — `COALESCE(row_to_json(OLD), '{}'::json)` and `COALESCE(row_to_json(NEW), '{}'::json)` prevents NULL payload crash on DELETE/NULL-update triggers
- **B2 fix:** Two-phase commit — `store_instance()` split into Phase 1 (DB: `Files.insert_or_select`), Phase 2 (outside xact: `storage.copy`), Phase 3 (DB: `ReplicaFiles.add`); tracked via `_TxTracker`
- **B3 fix:** TOCTOU race — `Files.insert_or_select()` catches `asyncpg.UniqueViolationError` on `add()` and falls back to `self.get()`

#### F3.2: Storage Routing ✅
- **B4 fix:** `store_instance()` iterates `evaluate_routing_rules()` results, looks up destination replica via `Replica.get(dest_id)`, copies file to destination storage, and adds `ReplicaFiles.add()` for the destination; per-route try/except wrapper

#### F3.3: C-MOVE / C-GET SCP Stubs ✅
- Registered `PatientRootQueryRetrieveInformationModelMove`, `StudyRootQueryRetrieveInformationModelMove`, `PatientRootQueryRetrieveInformationModelGet`, `StudyRootQueryRetrieveInformationModelGet` in AE presentation contexts
- Added `handle_move()` and `handle_get()` stub handlers to `dcm/server.py` handlers list

#### F3.4: Modality Worklist C-FIND Context ✅
- Added `ModalityWorklistInformationFind` to AE `supported_contexts` via `ae.supported_contexts = StoragePresentationContexts + [ModalityWorklistInformationFind]`

#### F3.5: WADO-URI Priority Fix ✅
- **B1 fix:** `DicomWebWadoUri.get()` changed from `if series_uid` to `if object_uid` priority — `objectUID` now returns single instance even when `seriesUID` is also present; added study-level fallback path

#### F3.6: Orphan Cleanup ✅
- **D fix:** `Files.delete()` calls `Replica.get(master_id)` → `Storage.get(replica)` → `storage.delete(file_data)` before DB record cleanup; lazy `from db.replica import Replica as ReplicaModel` avoids circular import

#### F3.7: Modality Validation ✅
- **E fix:** `DicomWebStudies.post()` validates modality via `validate_modality()` against `VALID_MODALITIES` frozenset (46 codes); returns 400 `{'error': f'Invalid modality: {modality}'}`

### Phase 3 Audit & Hardening Sprint

An audit of DICOM Core infrastructure revealed 24 gaps across 3 priority levels:

| Priority | Count | Description |
|----------|-------|-------------|
| P0 (crash) | 3 | Loop None, Dedup crash, NULL payload in notify_event trigger |
| P1 (functional) | 8 | WADO-URI priority, two-phase commit integrity, TOCTOU race, no routing, MWL contexts, C-MOVE/C-GET contexts |
| P2 (quality) | 13 | Orphan cleanup, modality validation, missing C-STORE/bulkdata handlers, C-ECHO missing from contexts, etc. |

Fixes delivered in 6 vertical-slice sprints:

| Sprint | Fix | Files Changed |
|--------|-----|---------------|
| A1 | Loop init + MWL presentation context | `lifecycle.py`, `dcm/server.py`, `tests/test_dicom_lifecycle.py` |
| A2 | Dedup crash (store_instance hash check) | `dcm/store.py`, `tests/test_dcm.py` |
| A3 | notify_event NULL payload | `migrations/versions/025_fix_notify_event.py`, `tests/test_migrations.py` |
| B1 | WADO-URI objectUID priority | `api/dicomweb.py`, `tests/test_dicomweb_wado.py` |
| B2 | Two-phase commit integrity | `dcm/store.py`, `tests/test_dcm.py` |
| B3 | TOCTOU race (UniqueViolationError) | `db/files.py`, `tests/test_db_table.py` |
| B4 | Storage routing in store_instance | `dcm/store.py`, `tests/test_dcm.py` |
| C | C-MOVE/C-GET contexts + handlers | `lifecycle.py`, `dcm/server.py`, `tests/test_dicom_lifecycle.py` |
| D | Orphan cleanup on delete | `db/files.py`, `tests/test_db_table.py` |
| E | Modality validation on STOW-RS | `api/dicomweb.py`, `tests/test_dicomweb_stow.py` |
| F | End-to-end pipeline integration | `tests/integration/test_dicom_v3.py` |

### Phase 3 Gate (Passed)

```bash
cd backend && python -m pytest tests/ -v --tb=short  # 640 passed (↑17 from Phase 2)
cd backend && python -m pytest tests/integration/test_dicom_v3.py tests/test_dcm.py tests/test_dcm_file.py -v --tb=short
```

---

## Phase 4 — Integration (Weeks 17–22)

### Objective
Add HL7 v2.x MLLP listener and FHIR R4 API for external RIS/EHR integration.

### Features

#### F4.1: HL7 v2.x MLLP Listener
**Effort:** 3 weeks | **Parallel tracks:** 2

- [x] **F4.1a — MLLP server**
  - [x] Create `backend/services/ingestion/hl7_server.py` — TCP server with MLLP framing (start块 `0x0B`, end块 `0x1C0D`)
  - [x] Configurable port (default 12579), TLS support
  - [x] `hl7` library (or `python-hl7`) for message parsing
  - [x] RED: test that a raw HL7 ADT-A01 message sent to MLLP port results in a new patient record
  - [x] GREEN: implement MLLP receiver, basic HL7 parser, patient upsert logic

- [x] **F4.1b — ADT message handlers**
  - [x] ADT-A01 (admit) → create/update patient; `PatientClass` mapping
  - [x] ADT-A08 (update) → update patient demographics
  - [x] ADT-A03 (discharge) → mark patient inactive; optional `DischargeDatetime`
  - [x] ADT-A04 (registration), ADT-A05 (preadmit) → create patient if new
  - [x] RED: test each ADT event type produces correct DB state
  - [x] GREEN: implement per-event-type handlers with field mapping

- [x] **F4.1c — ORM message handler**
  - [x] ORM-O01 → create/update worklist entry (links to patient, stores requested procedure)
  - [x] Map HL7 ORC and OBR segments to DICOM MWL attributes
  - [x] RED: test that ORM-O01 creates a queryable MWL entry
  - [x] GREEN: implement ORM handler delegating to `worklist_entries` table

- [x] **F4.1d — Audit and error handling**
  - [x] Every received HL7 message logged with SHA-256 hash for non-repudiation
  - [x] Unknown segment types logged but non-fatal
  - [x] Malformed messages rejected with MLLP NACK
  - [x] RED: test each error path
  - [x] GREEN: implement error handling, audit logging

#### F4.2: FHIR R4 API
**Effort:** 3 weeks | **Parallel tracks:** 2

- [x] **F4.2a — FHIR server scaffold**
  - [x] Add `fhir.resources` or build minimal FHIR resource serializers
  - [x] CapabilityStatement at `GET /api/v2/fhir/metadata`
  - [x] RED: test that `GET /fhir/metadata` returns valid CapabilityStatement with `application/fhir+json`
  - [x] GREEN: implement CapabilityStatement builder (supported resources, interactions, operations)

- [x] **F4.2b — Patient resource**
  - [x] `GET /api/v2/fhir/Patient` — search by `identifier`, `name`, `birthdate`, `_lastUpdated`
  - [x] `GET /api/v2/fhir/Patient/{id}` — read by database ID
  - [x] RED: test search and read return FHIR Patient resources with correct fields
  - [x] GREEN: implement Patient→FHIR mapping (mapping table: `patients.name`→`Patient.name[0].text`, `patients.birth_date`→`Patient.birthDate`, etc.)

- [x] **F4.2c — ImagingStudy resource**
  - [x] `GET /api/v2/fhir/ImagingStudy` — search by `patient`, `accession`, `modality`, `started`, `_lastUpdated`
  - [x] `GET /api/v2/fhir/ImagingStudy/{id}` — read with nested `series` and `instance` entries
  - [x] `ImagingStudy.endpoint` references the DICOMweb WADO-RS base URL
  - [x] RED: test that ImagingStudy search returns studies with correct modality and date range
  - [x] GREEN: implement ImagingStudy→FHIR mapping

- [x] **F4.2d — DocumentReference resource (report placeholder)**
  - [x] `GET /api/v2/fhir/DocumentReference` — search by `patient`, `type`, `period`
  - [x] `GET /api/v2/fhir/DocumentReference/{id}` — read
  - [x] Initially returns references to share links or external report URLs (full SR integration in v3.1)
  - [x] RED: test DocumentReference search returns correct references
  - [x] GREEN: implement basic DocumentReference resource

#### F4.3: Study Routing Rules
**Effort:** 1 week

- [x] **F4.3a — Rule engine**
  - [x] Add `routing_rules` table: `id UUID PK`, `tenant_id TEXT`, `priority INT`, `condition JSONB` (e.g., `{"modality": "CT", "study_description": {"contains": "CHEST"}}`), `action JSONB` (`{"replica_target": "replica_2"}`), `enabled BOOL`
  - [x] RED: test that uploading a CT CHEST study routes to `replica_2`
  - [x] GREEN: implement rule evaluation triggered on file ingestion (in Redis Streams consumer)

- [x] **F4.3b — Rule CRUD API**
  - [x] `GET/POST /api/v2/routing-rules`, `PUT/DELETE /api/v2/routing-rules/{id}`
  - [x] RED: test admin creates, modifies, deletes rule
  - [x] GREEN: implement CRUD endpoints

### Phase 4 Gate

```bash
cd backend && python -m pytest tests/integration/test_hl7.py tests/integration/test_fhir.py tests/integration/test_routing.py -v --tb=short --cov --cov-fail-under=80
```

Live verification (Phase 4 kickoff — skipped when the target is unreachable):

```bash
cd backend && python -m pytest tests/integration/test_mllp_live.py tests/integration/test_mwl_cfind_parity.py -v --tb=short
```

---

## Phase 5 — Observability (Weeks 23–24)

### Objective
Structured JSON logging, Prometheus metrics in exposition format, OpenTelemetry tracing end-to-end, component health checks.

### Features

#### F5.1: Structured Logging
**Effort:** 0.5 week

- [x] **F5.1a — JSON formatter**
  - [x] Replace plain-text `logging.Formatter` with JSON formatter in `log.py`
  - [x] Fields: `timestamp` (ISO8601), `level`, `logger`, `message`, `request_id`, `tenant`, `user_id`, `trace_id`, `span_id`, `error` (if exception)
  - [x] RED: test that log output is valid JSON with required fields
  - [x] GREEN: implement JSON formatter; add `request_id` propagation (already scaffolded)

- [x] **F5.1b — Structured error logging**
  - [x] All unhandled errors logged with stack trace in the `error.stack` field (not in message)
  - [x] RED: test that a 500 error produces a structured JSON log entry
  - [x] GREEN: implement error middleware that captures exception context

#### F5.2: Prometheus Metrics
**Effort:** 1 week

- [x] **F5.2a — Standard metrics**
  - [x] Replace `backend/api/telemetry.py` in-memory counters with `prometheus_client` metrics
  - [x] `starlette_exporter` or manual metrics middleware:
    - `http_requests_total` (labels: method, path, status)
    - `http_request_duration_seconds` (histogram, labels: method, path)
    - `http_request_in_progress` (gauge)
    - `db_pool_available`, `db_pool_in_use` (per-tenant gauge)
    - `redis_stream_lag_seconds` (gauge per stream per consumer group)
    - `dicom_cstore_throughput_bytes` (counter)
    - `dicomweb_requests_total` (labels: method, resource)
  - [x] RED: test that `/api/v2/metrics` returns valid Prometheus exposition format
  - [x] GREEN: instrument all metric sources

- [x] **F5.2b — Metrics endpoint**
  - [x] `GET /api/v2/metrics` returns Prometheus text format
  - [x] Protected: admin/read-only access
  - [x] RED: test that non-admin gets 403 on metrics endpoint
  - [x] GREEN: add auth guard

#### F5.3: Health Checks
**Effort:** 0.5 week

- [x] **F5.3a — Component-level health**
  - [x] `GET /api/v2/health` returns JSON:
    ```json
    {
      "status": "ok",
      "components": {
        "database": { "status": "ok", "latency_ms": 2 },
        "redis": { "status": "ok", "latency_ms": 1 },
        "storage": { "status": "ok", "master": "local", "replicas": ["s3", "b2"] },
        "elasticsearch": { "status": "degraded", "message": "ES unavailable, search fallback active" },
        "dicom_listener": { "status": "ok", "port": 11112, "uptime_seconds": 86400 },
        "ingestion_service": { "status": "ok", "stream_lag": 0 }
      }
    }
    ```
  - [x] RED: test that component health reflects actual state (e.g., stop Redis → `redis` status `down`)
  - [x] GREEN: implement per-component health probes

#### F5.4: OpenTelemetry Tracing (Deepen)
**Effort:** 0.5 week

- [x] **F5.4a — AsyncPG tracing**
  - [x] Instrument `asyncpg` connection pool with OTel spans for each query
  - [x] RED: test that a DB query span appears in the trace with `db.statement` attribute
  - [x] GREEN: implement asyncpg tracing middleware (or use `opentelemetry-instrumentation-asyncpg`)

- [x] **F5.4b — Redis Streams tracing**
  - [x] Instrument each publish and consume operation with OTel spans
  - [x] Trace context propagation across stream producer→consumer boundary
  - [x] RED: test that consumer span has `messaging.destination` attribute
  - [x] GREEN: implement stream tracing

### Phase 5 Gate

```bash
cd backend && python -m pytest tests/integration/test_observability.py -v --tb=short --cov --cov-fail-under=80
curl -s http://localhost:8080/api/v2/health | python -m json.tool  # all components OK
curl -s http://localhost:8080/api/v2/metrics | head -20  # valid prom format
```

---

## Phase 6 — Frontend v3 (Weeks 25–32)

### Objective
Update the React SPA for v3: RBAC-aware UI, tenant switcher, OAuth login, mobile-responsive viewer, DICOMweb client, metrics dashboard.

### Features

#### F6.1: RBAC-Aware UI
**Effort:** 1.5 weeks | **Parallel tracks:** 3

- [x] **F6.1a — Auth store**
  - [x] Replace localStorage-based auth (`userId`, `admin`, `token`) with a React Context `AuthProvider`
  - [x] Context holds: `token`, `user`, `role`, `permissions`, `tenant`, `isAuthenticated`, `isLoading`
  - [x] Token refresh logic (intercept 401 → try refresh → redirect to login)
  - [x] RED (Playwright): test that a technician user does not see the "Admin" menu item
  - [x] GREEN: implement `AuthProvider`, `useAuth()` hook, `ProtectedRoute` with role/permission check

- [x] **F6.1b — Permission-gated components**
  - [x] Create `<RequirePermission perm="FILE_DELETE">` wrapper component
  - [x] Gate delete buttons, admin tabs, user management, replica management behind permissions
  - [x] RED (unit): test that `<RequirePermission perm="FILE_DELETE">` renders children for admin, null for technician
  - [x] GREEN: implement guard component reading from `AuthContext`

- [x] **F6.1c — Admin user/role management UI**
  - [x] Users page: show role column, dropdown to change role
  - [x] Roles page (new): list roles, create/edit/delete, permission checkboxes (grouped by resource)
  - [x] RED (Playwright): test that super admin can create a custom role with read-only files permission and assign it to a user
  - [x] GREEN: implement `Users.tsx` role management, `Roles.tsx` CRUD

#### F6.2: Tenant Switcher (Super Admin)
**Effort:** 1 week | **Parallel tracks:** 2

- [x] **F6.2a — Tenant selector**
  - [x] Sidebar header shows current tenant name; click opens tenant dropdown
  - [x] Dropdown lists all tenants with health indicator (green/yellow/red dot)
  - [x] Switching tenant re-fetches all data scoped to that tenant
  - [x] RED (Playwright): test that super admin switches tenant and dashboard shows that tenant's data
  - [x] GREEN: implement `TenantSwitcher` component, `TenantProvider` context

- [x] **F6.2b — Tenant management page**
  - [x] List view: tenants table with name, slug, domain, storage used/quota, study count, user count, status
  - [x] Provision tenant dialog: form with `slug`, `domain`, `admin_email`, `storage_quota`
  - [x] Decommission flow: confirmation dialog → soft delete → quarantine → purge after 30 days
  - [x] RED (Playwright): test provision→verify→decommission cycle
  - [x] GREEN: implement `Tenants.tsx`, `ProvisionTenant.tsx`

#### F6.3: OAuth Login Screen
**Effort:** 1 week | **Parallel tracks:** 2

- [x] **F6.3a — Login page update**
  - [x] Existing username/password form remains (for local JWT auth)
  - [x] Add "Sign in with SSO" section listing configured providers (Azure AD, Okta, Keycloak)
  - [x] Each provider has a branded button extracted from OIDC `issuer` metadata
  - [x] RED (Playwright): test that clicking "Sign in with Azure AD" redirects to IdP login
  - [x] GREEN: implement SSO button rendering from `/api/v2/oauth/providers` list

- [x] **F6.3b — OAuth callback handling**
  - [x] On return from IdP, the callback URL contains code in query params
  - [x] Frontend calls `POST /api/v2/oauth/token` with authorization code
  - [x] On success, stores httpOnly cookie (set by backend) and updates `AuthProvider`
  - [x] On failure, redirects back to login page with error message
  - [x] RED (Playwright): test full OAuth flow with mocked IdP
  - [x] GREEN: implement callback handler

#### F6.4: Mobile-Responsive Viewer
**Effort:** 2.5 weeks | **Parallel tracks:** 2

- [x] **F6.4a — Touch-optimized controls**
  - [x] Cornerstone3D touch gestures: pinch zoom, two-finger pan, tap-to-center, swipe-to-scroll-stack
  - [x] Custom toolbar for mobile: larger touch targets (min 44px), collapsible, bottom-anchored
  - [x] RED (Playwright mobile emulation): test that scroll tool works via swipe gesture
  - [x] GREEN: implement mobile interaction layer on top of Cornerstone3D tools

- [x] **F6.4b — Responsive layout**
  - [x] Below `768px`: sidebar collapses to bottom tab bar (Files, Patient, Viewer, Account tabs)
  - [x] Viewer: single-column layout, metadata table as collapsible drawer
  - [x] Thumbnail filmstrip for series navigation (horizontal scroll)
  - [x] RED (Playwright mobile): test responsive layout at 375×667 viewport
  - [x] GREEN: implement CSS Grid layout with breakpoint-aware component switching

- [x] **F6.4c — Progressive image loading**
  - [x] Load thumbnail first (JPEG, 256×256), then full-resolution viewport
  - [x] Configurable: always-thumbnail-first-on-mobile, optionally on desktop
  - [x] RED (Playwright): test that mobile viewport loads thumbnail before full-res
  - [x] GREEN: implement progressive loading in `CornerstoneElement` using `wadouri:` with `?viewport=` parameter

- [x] **F6.4d — PWA scaffold**
  - [x] Add `vite-plugin-pwa`, `public/manifest.json`
  - [x] Service worker caches static assets and recent study thumbnails
  - [x] "Install" prompt on supported browsers
  - [x] RED (Playwright): test that app registers service worker
  - [x] GREEN: implement PWA manifest, SW registration, basic cache strategy

#### F6.5: Metrics Dashboard
**Effort:** 1 week

- [x] **F6.5a — Dashboard page**
  - [x] `GET /api/v2/metrics` → render as dashboard cards: request rate, latency, active viewers, storage usage, DICOM throughput
  - [x] Charts: line chart for latency (p50/p95/p99) over last hour, bar chart for storage by tier
  - [x] RED (Playwright): test that dashboard loads and displays correct metrics
  - [x] GREEN: implement `Dashboard.tsx` with Chart.js or Ant Design Charts

- [x] **F6.5b — Health status summary**
  - [x] Component health pills (green/yellow/red) from `/api/v2/health`
  - [x] Click to expand: show component details and recent events
  - [x] RED: test that health pills reflect mock component states
  - [x] GREEN: implement health status display

#### F6.6: DICOMweb Client (Viewer)
**Effort:** 1 week

- [x] **F6.6a — WADO-RS retrieve in viewer**
  - [ ] Add option to retrieve study via WADO-RS (`/api/v2/dicomweb/studies/{uid}`) instead of WADO-URI per-file
  - [ ] Parse multipart DICOM response, load into Cornerstone3D stack
  - [ ] RED: test that viewer loads study from WADO-RS endpoint
  - [ ] GREEN: implement WADO-RS retrieve path in `CornerstoneElement`

- [x] **F6.6b — QIDO-RS search**
  - [ ] Replace v2 search POST (`/api/files` → ES) with QIDO-RS GET (`/api/v2/dicomweb/studies?...`)
  - [ ] Backward-compatible: keep v2 search as fallback
  - [ ] RED: test that search results match between v2 and QIDO-RS
  - [ ] GREEN: implement QIDO-RS search in `Files.tsx`

### Phase 6 Gate

```bash
cd frontend && npx tsc --noEmit && npx vitest run && npx vite build
cd frontend && npx playwright test --reporter=json  # all 11 specs (45 tests) pass
```

---

## Phase 7 — Verification (Weeks 33–35)

### Objective
Load testing, security scanning, IHE Connectathon preparation, and CI pipeline hardening.

### Features

#### F7.1: Load Testing (k6)
**Effort:** 1 week

- [ ] **F7.1a — API load test scenarios**
  - Create `backend/tests/load/` with k6 scripts:
    - `study_search.js` — QIDO-RS search at 50 RPS with 10k-study dataset
    - `dicom_store.js` — C-STORE load at 150 MB/s sustained
    - `dicomweb_store.js` — STOW-RS at 50 concurrent uploads
    - `viewer_sessions.js` — 200 concurrent WebSocket clients
    - `auth_flow.js` — OAuth login flow at 10 RPS
  - [ ] RED: run scenarios against staging → identify bottlenecks
  - [ ] GREEN: tune until p95 < 300ms at target RPS for all scenarios

- [ ] **F7.1b — CI pipeline integration**
  - [ ] k6 tests run nightly against staging environment
  - [ ] Slack/email notification on regression (p95 exceeds threshold by >20%)
  - [ ] RED: test that CI fails when latency exceeds threshold
  - [ ] GREEN: implement CI workflow for k6

#### F7.2: Security Scan (OWASP ZAP)
**Effort:** 1 week

- [ ] **F7.2a — Baseline scan**
  - [ ] OWASP ZAP baseline scan against all `/api/v2/*` endpoints
  - [ ] RED: scan reveals issues → fix or document as false positive
  - [ ] GREEN: 0 high-risk findings; medium/low findings have documented justification

- [ ] **F7.2b — CI integration**
  - [ ] ZAP scan runs on every merge to `main`
  - [ ] Fails build if any new high-risk finding introduced
  - [ ] RED: intentionally introduce a finding → verify CI blocks merge
  - [ ] GREEN: implement ZAP CI workflow

#### F7.3: Dependency Auditing
**Effort:** 0.5 week

- [ ] **F7.3a — pip-audit + npm audit in CI**
  - [ ] Already in CI from Phase 0 (hardening)
  - [ ] Add `pip-audit` to pre-commit hooks
  - [ ] RED: test that CI fails on known CVE dependency
  - [ ] GREEN: configure audit tooling

#### F7.4: IHE Connectathon Preparation
**Effort:** 2 weeks

- [ ] **F7.4a — DICOMweb self-certification**
  - [ ] Run [IHE DICOMweb Test Suite](https://github.com/IHE/dicomweb-test-tool) against `/api/v2/dicomweb/*`
  - [ ] RED: test suite reveals compliance gaps → fix before GA
  - [ ] GREEN: all QIDO-RS, STOW-RS, WADO-RS tests pass

- [ ] **F7.4b — Integration test suite**
  - [ ] Implement the test tool's scenarios as pytest integration tests
  - [ ] These tests run in CI, ensuring regression doesn't break conformance
  - [ ] RED: test that a regression in WADO-RS is caught by CI
  - [ ] GREEN: write pytest wrappers for all test tool assertions

#### F7.5: Cross-Tenant Isolation Property Test
**Effort:** 0.5 week

- [ ] **F7.5a — Property-based isolation fuzzing**
  - [ ] Using `hypothesis` (Python property-based testing):
    ```python
    @given(
      tenant_a=strategies.text(min_size=1),
      tenant_b=strategies.text(min_size=1).filter(lambda x: x != tenant_a)
    )
    async def test_isolation(tenant_a, tenant_b):
        # Insert known data in tenant_a
        # Query tenant_b's connection
        # Assert no tenant_a data visible
    ```
  - [ ] RED: fuzz discovers isolation leak → fix routing bug
  - [ ] GREEN: property test runs 1000 iterations, zero failures

#### F7.6: E2E Test Expansion (Playwright)
**Effort:** 1 week

- [ ] **F7.6a — Ten critical flows**
  1. Login (local JWT) → search → open study → scroll slices → logout
  2. OAuth login (mocked IdP) → verify role-based sidebar
  3. Super admin provisions new tenant → verifies in dashboard
  4. Admin creates custom role → assigns to user → user exercises permission
  5. Study upload via C-STORE → verify in search → verify in viewer
  6. STOW-RS upload (via API) → verify same as C-STORE
  7. HL7 ADT message → verify patient created → verify in FHIR /Patient
  8. MWL C-FIND (via DICOM tool) → verify worklist entry returned
  9. Share link generation → open in incognito → verify study accessible
  10. Mobile viewport: login → search → open study → verify responsive layout
  - [ ] RED: each flow starts as a failing test
  - [ ] GREEN: all 10 flows pass in CI

### Phase 7 Gate

```bash
cd backend/tests/load && k6 run study_search.js  # p95 < 300ms
cd backend && python -m pytest tests/integration/test_isolation.py -v --tb=short  # 1000 property iterations
cd frontend && npx playwright test --reporter=json  # 10/10 E2E specs pass
pip-audit --fail-on=high  # 0 high-severity findings
npm audit --audit-level=high  # 0 high-severity findings
```

---

## Phase 8 — v1→v2 API Migration (Weeks 36–37)

### Objective
Make the v2 API the default, add version prefixes, deprecation headers, and dual-write compatibility.

### Features

#### F8.1: API Version Aliasing
**Effort:** 1 week

- [ ] **F8.1a — v1 route aliasing**
  - [ ] Existing `/api/*` routes remain functional but now also register under `/api/v1/*`
  - [ ] Internal implementation: Starlette `Mount` at `/api/v1` with the same route table
  - [ ] New v2 routes under `/api/v2/*` using the new route modules
  - [ ] RED: test that existing client calling `/api/files` gets same response as `/api/v1/files`
  - [ ] GREEN: implement route aliasing in `routes.py`

- [ ] **F8.1b — Deprecation headers**
  - [ ] All `/api/v1/*` responses include `X-API-Deprecated: true` and `X-API-Sunset-Date: <v4.0 release date>`
  - [ ] Upgrade guide published: `docs/migration-v1-to-v2.md`
  - [ ] RED: test that v1 endpoints return deprecation headers
  - [ ] GREEN: implement middleware adding deprecation headers to v1 routes

#### F8.2: Dual-Write during Transition
**Effort:** 0.5 week

- [ ] **F8.2a — Shared data layer**
  - [ ] v1 and v2 write operations (file upload, patient update, etc.) write to the same underlying tables
  - [ ] No data duplication — v2 endpoints use the same `services/` interfaces as v1
  - [ ] RED: test that uploading via v1 POST `/api/files/upload` makes the study visible via v2 GET `/api/v2/dicomweb/studies`
  - [ ] GREEN: verify data sharing in integration tests

#### F8.3: Documentation
**Effort:** 0.5 week

- [ ] **F8.3a — OpenAPI specs**
  - [ ] `/api/docs` serves both v1 and v2 OpenAPI specs side by side
  - [ ] Each spec annotated with version, deprecation status, and sunset date where applicable
  - [ ] RED: test that both specs are valid OpenAPI 3.0
  - [ ] GREEN: generate specs from route decorators

### Phase 8 Gate

```bash
cd backend && python -m pytest tests/integration/test_api_v2.py tests/ -v --tb=short -W error::Warning  # all tests pass
curl -sI http://localhost:8080/api/v1/files | grep -i "X-API-Deprecated"  # header present
curl -s http://localhost:8080/api/v2/dicomweb/studies | python -m json.tool  # returns valid response
```

---

## v3.0 GA ●

**Release criteria (all must pass):**

```bash
# 1. All tests pass
cd backend && python -m pytest tests/ -v --tb=short -W error::Warning --cov --cov-fail-under=80
cd frontend && npx vitest run --coverage --coverage.threshold.functions=60
cd frontend && npx playwright test --reporter=json

# 2. TypeScript strict pass
cd frontend && npx tsc --noEmit --strict

# 3. Build pass
cd frontend && npx vite build

# 4. Security pass
pip-audit --fail-on=high
npm audit --audit-level=high

# 5. Load test pass
cd backend/tests/load && k6 run study_search.js && k6 run dicom_store.js && k6 run viewer_sessions.js

# 6. Multi-tenant isolation pass
cd backend && python -m pytest tests/integration/test_isolation.py -v --tb=short

# 7. DICOMweb conformance pass
cd backend && python -m pytest tests/integration/test_dicomweb_conformance.py -v --tb=short

# 8. Upgrade from v2.0 (dry-run)
./manage db backup
alembic upgrade head
./manage db restore --verify
```

---

## Phase 9 — v3.1 RIS (Post-GA)

**Scoped in `docs/ROADMAP-v3.md`:** Scheduling, worklist, reporting, billing-lite, physician portal.

Not detailed here — a separate `IMPLEMENTATION_PLAN-v3.1.md` will be written after v3.0 GA.

---

## Rollback Plan

| Scenario | Action |
|----------|--------|
| Phase 1 Redis Streams migration fails | `git revert` the Phase 1 branch; LISTEN/NOTIFY still works unmodified |
| Phase 2 tenant provisioning creates broken DB | `./manage tenant deprovision <slug>` drops DB, removes registry row |
| Phase 2 OAuth integration breaks login | Revert OAuth config; users fall back to local JWT login |
| Phase 3 DICOMweb breaks existing viewer | Remove `/api/v2/*` nginx location; existing `/api/*` still serves WADO-URI |
| Phase 4 HL7 integration corrupts patient data | `git revert` HL7 handler; restore patient data from pre-HL7 backup |
| Phase 6 frontend regressions | Revert frontend branch; old SPA still works with v1 API |
| Phase 8 API versioning confuses clients | Keep `/api/*` aliased to `/api/v1/*` indefinitely; extend sunset date |
| Cross-cutting: any phase | Each phase is a feature branch → `git revert` restores main to working state |

---

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Phase 0 hardening slips into v3 timeline | Medium | High | Hardening runs in parallel with Phase 1 planning; hard gate at Phase 2 |
| DB-per-tenant connection pool memory exhaustion at scale | Medium | High | Idle pool eviction (TTL: 5 min); max pools configurable; per-pool cap at 8 conns |
| OIDC integration failure with hospital IdP | High | High | Test against Azure AD + Okta + Keycloak before GA; maintain local JWT as fallback |
| Redis Streams consumer lag during ingestion burst | Medium | Medium | Monitor lag via Prometheus; auto-scale consumers; configure maxlen |
| DICOMweb spec interpretation differs from IHE expectations | Medium | High | Self-certification test suite runs in CI; external Connectathon before GA |
| FHIR mapping complexity exceeds estimate | Medium | Medium | Ship only Patient + ImagingStudy in v3; DocumentReference + DiagnosticReport deferred to v3.1 |
| Frontend v3 scope exceeds frontend capacity | High | Medium | Feature flags for mobile viewer and metrics dashboard; defer to v3.1 if needed |
| Single team context-switching across 8 phases | High | Medium | Parallel tracks with dedicated sub-branches; one phase owner per track |

---

*This implementation plan covers Phases 1–8 of the v3.0 delivery. Phase 0 is tracked separately in `IMPLEMENTATION_PLAN.md`. Phase 9 (v3.1 RIS) will be planned after v3.0 GA. Each feature block follows the TDD vertical-slice pattern: RED → GREEN → REFACTOR.*