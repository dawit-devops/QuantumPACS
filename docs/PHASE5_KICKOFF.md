# Phase 5 — Observability Kickoff (Logging + Metrics + Health + Tracing)

Status: **verification in progress** · Target branch: `phase/5-observability` (off `v3-dev`)
Sources: `docs/IMPLEMENTATION_PLAN-v3.md` §Phase 5, `ADR-020` (observability stack).

## Headline: features already exist — this phase verifies and closes gaps

F5.1 (structured logging), F5.2 (Prometheus metrics), F5.3 (health checks) and
F5.4 (OTel tracing) were implemented in earlier phases (production-hardening
sprints). The Phase 5 gate suites already pass locally:

```bash
cd backend && .venv/bin/python -m pytest tests/integration/test_observability.py tests/integration/test_tracing.py tests/test_logging.py tests/test_dashboard_health.py tests/test_dashboard_metrics.py -q
# 62 passed
```

This phase is therefore: **live verification end-to-end (health + metrics
endpoints against the running stack), fixing anything those expose, and
checking off the plan** — not greenfield build.

## What already exists (verified in dev env, Aug 2026)

| Feature | Code | Status |
|---|---|---|
| JSON formatter with ISO-8601 timestamp, level, logger, message, request_id, tenant, user_id, trace_id, span_id, `error.stack` | `backend/log.py` (`JSONFormatter`, ContextVars) | Present; `test_logging.py` green |
| Structured error logging (500 → JSON log entry with `error.stack`) | error middleware + `record_exception` | `test_observability.py::TestErrorLogging` green |
| Prometheus metrics: `http_requests_total`, `http_request_duration_seconds`, `http_requests_in_progress`, `db_connections_available/in_use`, `db_query_duration_seconds`, `redis_stream_lag_seconds`, `dicom_cstore_throughput_bytes`, `dicomweb_requests_total` | `backend/api/telemetry.py` (prometheus_client) | Present; live `/api/v2/metrics` returns exposition format (admin-gated) |
| `GET /api/v2/metrics` (Prometheus text, admin only) | `telemetry.metrics_endpoint` + `routes.py` | Live-verified 200 with admin token; 401 unauthenticated; 403 non-admin (tested) |
| `GET /api/v2/health` component probes: database, redis, storage, elasticsearch, dicom_listener, ingestion_service, hl7, fhir, auth, token_blocklist | `telemetry.health_endpoint`, `tenant_health.py` | Live-verified; all `ok` except elasticsearch `degraded` (ES not running in dev — by design, search fallback active) |
| AsyncPG query tracing (`db.query` spans, `db.statement` attribute) | `api/tracing.py` `traced_connection`/`_TracedPool` | `test_tracing.py::TestAsyncpgTracing` green |
| Redis Streams tracing (`redis.publish`/`redis.consume` spans, `messaging.destination`/`consumer_group`) | `services/redis_streams.py` | `test_tracing.py::TestRedisStreamTracing` green |
| Tracing middleware (HTTP span per request) | `api/tracing_middleware.py` | Present |

## Verification checklist

### F5.1 — Structured Logging
- [x] Live: `journalctl --user -u quantumpacs-backend.service` shows JSON lines with timestamp/level/logger/message.
- [x] RED/GREEN: `tests/test_logging.py` (JSON shape, required fields) — 7 passed.
- [x] F5.1b: 500 → structured JSON with `error.stack` (`test_observability.py::TestErrorLogging`) — 2 passed.

### F5.2 — Prometheus Metrics
- [x] Live: `curl -H "Authorization: Bearer <admin>" http://localhost:8080/api/v2/metrics` → valid exposition format (153 metric families), incl. `http_requests_total`, `db_query_duration_seconds`, `redis_stream_lag_seconds`, `dicom_cstore_throughput_bytes`.
- [x] Auth: 401 unauthenticated, 403 non-admin, 200 admin — all tested.
- [x] **Bug found & fixed (live)**: `_sample_db_pool()` read `db.pool` but `Database` stores the traced pool as `_pool` → `db_connections_available/in_use` gauges never appeared. Also `get_active_size()` does not exist on asyncpg Pool — active = `get_size() - get_idle_size()`. Fixed in `api/telemetry.py` + test mock updated (also patched `fake_db._pool`, matching `_TracedPool` attribute layout).
- [x] Live re-verify after fix: `db_connections_available{tenant="default"} 2.0`, `db_connections_in_use{tenant="default"} 0.0`.

### F5.3 — Health Checks
- [x] Live: `curl http://localhost:8080/api/v2/health` → ADR-020 structure with all 10 component keys; database/redis/storage/dicom_listener/ingestion_service/hl7/fhir/auth/token_blocklist `ok`; elasticsearch `degraded` (ES down in dev, search fallback active — expected).
- [x] Down-state behavior tested: `test_observability.py` (redis down → `redis: down`).

### F5.4 — OpenTelemetry Tracing
- [x] AsyncPG: `traced_connection()` wraps the pool; query spans carry `db.statement` (tested).
- [x] Redis streams: publish/consume spans with `messaging.destination`, `messaging.consumer_group` (tested).
- [x] Middleware HTTP span per request (present).

### Gate + CI
- [x] Observability suites: **62 passed** (`test_observability.py` 27, `test_tracing.py`, `test_logging.py`, `test_dashboard_health.py`, `test_dashboard_metrics.py`, `test_dicomweb_logging.py`).
- [x] Check off F5.1–F5.4 boxes in `docs/IMPLEMENTATION_PLAN-v3.md`; note deviations (features pre-existing, phase = verification).

## Deviations / notes

- Metric names differ slightly from plan prose: `db_connections_available/in_use` (plan said `db_pool_*`), `http_requests_in_progress` (plan said `http_request_in_progress`). ADR-020 is authoritative; plan wording updated in check-off note.
- `/api/v2/health` reports `degraded` while ES is down — intentional: search degrades gracefully, everything else stays `ok`.
- `dicomweb_requests_total` only increments on real proxied traffic (counter starts at 0 until first DICOMweb request — normal for counters).

## Risks

| Risk | Impact | Mitigation |
|---|---|---|
| Metrics endpoint cardinality leak | High label cardinality from `path` label | Path is the route template, not raw path (verified in `record_request`) |
| Health probes hammering DB | Extra load per poll | Probes run on request only (no background poller) |
| ES down shows `degraded` | Health gate "all OK" check fails | Documented expected state in dev; CI runs ES |

## Suggested commit sequence (branch `phase/5-observability`)

1. `fix(observability): db pool gauges — _pool attr + get_size-idle active count` (code + test)
2. `docs(plan): check off F5.1–F5.4 boxes in IMPLEMENTATION_PLAN-v3.md`
3. `docs(kickoff): phase 5 verification results + deviations`