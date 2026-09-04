# ADR-031: App-Level Rate Limiting for the RIS Surface

## Status

Accepted

## Date

2026-08-23

## Context

Sprint plan S1-04 required per-tenant rate limiting on the RIS HTTP
surface, but `backend/api/ratelimit.py` only governed the `/login`
endpoint. Nothing wired budget enforcement into the `app.py` middleware
stack for `/api/v2/ris/*`, leaving every RIS handler (scheduling, billing,
check-in, orders, prior-auth) effectively unbounded per client.

Two candidate mechanisms were considered:

- **Reverse-proxy limiting** (nginx `limit_req` / API gateway): would push
  enforcement out of the app and require per-tenant rule generation at the
  edge. The project has no dedicated edge tier in the documented topology
  (`docker-compose.yaml` runs the Starlette app directly on the host
  network), so this would not be portable across the documented dev,
  container, and production topologies.
- **Application middleware reusing the existing bucket primitives**:
  `TokenBucket` (in-memory) and `RedisTokenBucket` (sliding-window zset)
  already exist for login. Wrapping them in a Starlette middleware mounted
  in the same stack keeps one limiter implementation, one config surface,
  and works identically whether Redis is present or absent.

## Decision

Add `backend/api/ratelimit_middleware.py` exposing `RisRateLimitMiddleware`
and mount it in the `app.py` middleware stack. It:

- Governs only the `/api/v2/ris/*` prefix. All other routes (login, DICOM,
  FHIR, admin, `/health`) pass through untouched.
- Buckets per tenant + client IP, using `RedisTokenBucket` when Redis is
  reachable (sliding window, shared across workers) and falling back to the
  in-memory `TokenBucket` otherwise. Redis key namespace is derived from the
  middleware `key_prefix` so RIS buckets never collide with the login
  limiter's `ratelimit:login:*` keys — and tenants cannot consume each
  other's budget.
- Reads budgets from `default_config`:
  `ris_rate_limit_per_minute` (default 120) and
  `ris_rate_limit_kiosk_per_minute` (default 60).
- Exempts `/api/v2/ris/checkin/*` from the standard budget and instead
  applies the kiosk budget, so a busy self-check-in lobby cannot starve
  normal clinic traffic (and a rogue client cannot use kiosk paths as a
  proxy to bypass the RIS limit).
- Returns `429` with a `Retry-After: 60` header when a bucket is exhausted.

To support this, `RedisTokenBucket.__init__` gained a `key_prefix`
parameter (default `'login'`, backward compatible) replacing the hardcoded
`ratelimit:login:*` keys.

## Consequences

- All RIS REST traffic now has a bounded per-tenant, per-IP budget with a
  standard, cacheable `429` response.
- The login limiter is unchanged (default `key_prefix='login'`).
- Operators tune budgets via config/env without code changes; invalid
  values fall back to the defaults.
- Kiosk self-check-in traffic is explicitly carved out with its own budget.
- The middleware is intentionally prefix-scoped; if other surfaces later
  need limiting (e.g. FHIR), the same class is reusable with a different
  prefix rather than a new limiter implementation.
