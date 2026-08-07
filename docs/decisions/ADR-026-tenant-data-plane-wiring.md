# ADR-026: Tenant Data-Plane Wiring — Completing the DB-Per-Tenant Architecture

## Status
Accepted

## Date
2026-08-06

## Context
ADR-016 chose database-per-tenant isolation and defined the registry model, the
per-tenant databases, and the `TenantConnectionPool` router. The registry table,
provisioner, pool router, and `X-Tenant-ID` middleware exist, but the tenant data
plane is still dormant: request routing stops at `request.state` (only
middleware-managed handlers see it), no contextvar makes the tenant connection
available to plain `get_conn()` callers, no default tenant exists, tenant status
is not enforced at the request boundary, and usage/quota are unmeasured. This ADR
records how the dormant architecture is completed.

## Decision

### (a) Contextvar-based request-scoped tenant routing

`db/conn.py` gains a `contextvars.ContextVar` holding the current request's
tenant slug and pool. The middleware resolves the tenant, then calls
`set_request_tenant(slug, pool)` before invoking the handler; `get_conn()`
returns a connection from the tenant pool when the contextvar is set, and from
the platform registry pool otherwise. Every handler that already calls
`get_conn()` therefore becomes tenant-transparent — no per-handler plumbing.

### (b) Tenant resolution precedence

1. **JWT `tenant` claim** — web users' tokens carry `users.tenant`; this is the
   default tenant scope for the request.
2. **`X-Tenant-ID` header** — super admins (and programmatic callers) override
   the JWT scope with an explicit header; non-admin users are denied with 403
   when the header does not match their claim (`User.can_access_tenant`).
3. **Unscoped platform mode** — requests with neither claim nor header (super
   admins only) operate on the platform registry database.

### (c) Default tenant

A tenant with slug `default` is seeded at startup, backed by the main
`quantumpacs` database as its data store (registry row pointing `db_name` at the
platform DB). Existing users are **not** auto-assigned to it — `users.tenant`
stays NULL until an admin explicitly assigns it, so no existing session changes
meaning.

### (d) Tenant status lifecycle and gating

Status values: `provisioning` / `active` / `suspended` / `quarantined` /
`decommissioned`. The middleware gates non-`active` tenants: `suspended` and
`quarantined` → 403 with a machine-readable error; `decommissioned` → 404 (the
tenant is gone from the platform's point of view). `provisioning` short-circuits
routing (the DB may not exist yet).

### (e) Storage quota enforcement

Uploads check `files.size` against the tenant's `storage_quota_bytes` from the
registry before persisting; exceeding it returns the error code
`QUOTA_EXCEEDED`. When usage crosses 90% of quota, a breach notification is
created (existing notification channel) and `tenants.storage_used_bytes` is
updated.

### (f) Usage metering, backup, and health

- **Metering**: `tenant_usage_daily(slug, day, api_calls, storage_bytes,
  active_users)` in the platform registry DB, rolled up per request by the
  middleware (fire-and-forget, never raises) and on storage changes.
- **Backup**: per-tenant `pg_dump` via the backup script — each tenant DB is
  backed up independently (ADR-016 consequence).
- **Health**: `GET /api/v2/tenants/health` probes every non-decommissioned
  tenant DB (`SELECT 1`), returning per-tenant reachability, latency, storage
  percentage, and today's API-call count; one unhealthy tenant never fails the
  response.

### (g) Authentication stays on the registry DB

The registry (main) database remains the auth store: `users.tenant = slug`
scopes platform-level logins, and JWTs carry the `tenant` claim. Tenant
databases are **clinical data stores only** — the initial tenant admin created
at provisioning also exists in the registry DB with `tenant = slug` so the
admin can log in at the platform level. (Pre-ADR behavior inserted the admin
into the tenant DB; the registry-DB admin is the authoritative account.)

### (h) Billing is explicitly out of scope

External subscription billing (Stripe, etc.) is a backlog item, not part of this
work. Metering (`tenant_usage_daily`) is the foundation billing will consume —
it records per-tenant API calls, storage, and active users without being coupled
to any billing provider.

## Alternatives Considered

- Header-only routing (status quo): leaves `get_conn()` callers unscoped and
  requires every handler to opt in — rejected because it makes isolation
  accidental, not structural.
- Middleware rewriting `request.state` only: already done, but invisible to
  background tasks and non-HTTP entry points — rejected for the same reason.
- Enforcing quota at the database trigger level: possible but duplicates
  application-level error codes and notification logic — rejected as
  over-engineering for the current tenant scale.

## Consequences

- **Isolation becomes structural**: any handler using `get_conn()` inside a
  routed request hits the tenant DB; no cross-tenant leakage via forgotten
  plumbing.
- **Ingestion/sync run platform-scoped** (no tenant context): the DICOM
  ingestion worker and replica sync operate on the registry DB only. Per-tenant
  ingest routing is a **documented follow-up** — the contextvar routing layer
  must not be reused by the worker until per-tenant ingest is designed
  (tenant resolution for DICOM AE/store events differs from HTTP requests).
- **Operational cost per ADR-016**: N databases → N pools, N backups, N health
  probes. Bounded by `TENANT_MAX_POOLS` (LRU eviction after 5 min idle).
- **Registry row stays source of truth** for status and quota; tenant DBs carry
  no tenancy metadata.
- **Metering rows are cheap and bounded** by `tenant_usage_retention_days`
  (default 365).

## References

- ADR-016: Database-Per-Tenant Multi-Tenancy
- ADR-025: Token Storage — HttpOnly Cookies + Headers (naming/format
  convention)
- IMPLEMENTATION_PLAN-v3.md F1.3 (Tenant Registry), F2.3 (Connection Routing)
- PRD-v3.md §3.4 — Multi-Tenancy: Database-per-Tenant
