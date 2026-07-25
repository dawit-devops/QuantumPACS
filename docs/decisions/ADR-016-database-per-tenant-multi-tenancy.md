# ADR-016: Database-Per-Tenant Multi-Tenancy

## Status
Accepted

## Date
2026-07-25

## Context

QuantumPACS v2.0 is single-organization: one PostgreSQL database, one set of users, one storage namespace. Multiple hospital sites require separate deployments. v3.0 must support multi-tenancy with strong data isolation, as hospitals will not accept cross-tenant data leakage.

Three common multi-tenancy isolation strategies exist:

1. **Shared schema + tenant_id column** — All tenants share tables; every row carries a `tenant_id`. Row-Level Security (RLS) enforces isolation at the database level.
2. **Schema-per-tenant** — Same database, separate PostgreSQL schemas per tenant (e.g., `tenant_a.files`, `tenant_b.files`).
3. **Database-per-tenant** — Each tenant gets its own PostgreSQL database.

## Options Considered

| Option | Isolation | Operational Cost | Scaling | Migration Complexity |
|--------|-----------|-----------------|---------|---------------------|
| Shared schema + RLS | Weak (one bug = leak) | Low (one DB) | Best (shared resources) | Low |
| Schema-per-tenant | Medium (schema boundary, but same DB) | Medium (N schemas) | Good (shared connection pool) | Medium |
| **Database-per-tenant** | Strong (separate DB, separate connection) | Highest (N DBs, N pools) | Most complex (per-DB resource mgmt) | High |

The decision criteria for QuantumPACS:

- **Regulatory requirement**: Hospitals require contractual guarantees of data isolation. A bug in RLS policy could expose patient data across tenant boundaries — a HIPAA breach. Database-per-tenant provides the strongest guarantee because application code cannot accidentally cross databases; it connects to a different host/port/user.
- **Tenant count**: QuantumPACS targets hospital systems — a single deployment serves tens of tenants (hospital sites), not thousands. At this scale, the operational cost of N databases is linear and manageable.
- **Upgrade path**: Each tenant can be upgraded independently, allowing per-tenant maintenance windows.

## Decision

Use **database-per-tenant** isolation for v3.0 multi-tenancy.

### Architecture

1. **Tenant Registry Database** (`quantumpacs_tenants`) — Separate PostgreSQL database storing one row per tenant:
   - `id UUID`, `name TEXT`, `slug TEXT UNIQUE`, `domain TEXT`
   - `db_name TEXT`, `db_host TEXT`, `db_port INT`, `db_user TEXT`, `db_password_encrypted TEXT`
   - `status TEXT` (`provisioning` / `active` / `quarantined` / `decommissioned`)
   - `storage_quota_bytes BIGINT`, `storage_used_bytes BIGINT`
   - `created_at TIMESTAMPTZ`, `updated_at TIMESTAMPTZ`

2. **Per-Tenant Database** — Each tenant gets a full PostgreSQL database with the complete QuantumPACS schema. Created by `CREATE DATABASE <slug>` followed by Alembic migrations.

3. **Connection Pool Router** — `TenantConnectionPool` maintains a `dict[slug, asyncpg.Pool]`. Pools are created lazily on first request, evicted after 5 minutes of inactivity. Max pools configured via `TENANT_MAX_POOLS` (default 50).

4. **Tenant Resolution** — Extracted from `X-Tenant-ID` header (for programmatic access) or from the JWT `tenant` claim (for web users). Super-admins operate on the registry database and can switch tenant context.

5. **Tenant Provisioning Flow**:
   ```
   1. Super admin calls POST /api/v2/tenants {slug, domain, admin_email, storage_quota}
   2. TenantProvisioner creates PG database: CREATE DATABASE <slug>
   3. Runs alembic upgrade head on the new database
   4. Creates initial tenant_admin user
   5. Inserts registry row with status=active
   6. Returns tenant ID and admin credentials
   ```

### Tenant Isolation Guarantees

- **Connection-level isolation**: Tenant A's database connection can only query Tenant A's database. The pool router never returns a connection for a different tenant.
- **No shared sequences**: Each tenant has independent auto-increment sequences.
- **No cross-tenant foreign keys**: The registry database and tenant databases are completely separate — no FK references cross the boundary.
- **Fuzz-tested**: Property-based tests verify that N tenants with concurrent queries never observe each other's data (see `IMPLEMENTATION_PLAN-v3.md` F7.5).

## Consequences

### Positive

- **Strongest isolation** — Only database-per-tenant prevents accidental data leaks at the application level.
- **Independent backups** — Each tenant can be backed up and restored independently (`pg_dump per-tenant`).
- **Independent maintenance** — Alembic migrations can be applied per-tenant, allowing rolling upgrades.
- **Per-tenant configuration** — Storage backends, auth providers, and feature flags are per-tenant.

### Negative

- **Higher operational cost** — N databases mean N connection pools, N backups, N monitoring dashboards. At 50 tenants with 8 connections each = 400 total PG connections.
- **No cross-tenant queries** — Aggregating data across tenants requires querying the registry DB plus N tenant DBs. The super-admin dashboard polls each tenant's stats endpoint (sequential or batched).
- **Storage accounting** — `storage_used_bytes` must be updated by a periodic aggregation job or by a trigger on each tenant's `files` table.
- **Migration coordination** — `alembic upgrade --tenant <slug>` must run against each tenant. `./manage tenant migrate` iterates all tenants; one failure pauses the rollout.

## References

- ADR-004: PostgreSQL Database
- PRD-v3.md §3.4 — Multi-Tenancy: Database-per-Tenant
- IMPLEMENTATION_PLAN-v3.md F1.3 — Tenant Registry, F2.3 — Connection Routing
- "Multi-Tenant Data Isolation with PostgreSQL" — Crunchy Data, 2024