# ADR-029: Tenant Read Isolation — Pool Separation Is the Control

## Status

Accepted

## Date

2026-08-20

## Context

Branch-review findings (S4-21, S8-20, S10-15) flagged that cross-tenant
read assertions on the RIS tables (`ris_orders`, `ris_hl7_messages`,
`ris_interface_endpoints`, `ris_interface_events`, `ris_critical_results`,
`ris_report_templates`, …) were `xfail` with the reason "read-scoping by
tenant_id not yet enforced". The implied future mechanism — PostgreSQL Row
Level Security (RLS) on a shared schema, or application-level
`WHERE tenant_id = $1` filters on every read — was never actually needed,
because the system's tenant isolation boundary is elsewhere.

QuantumPACS isolates tenants by **database**: each non-default tenant is
provisioned its own PostgreSQL database (`TenantConnectionPool` in
`backend/db/tenants.py`, LRU-capped pools, per-slug creation locks,
migrations run at provision time). The HTTP `TenantMiddleware`
(`backend/api/tenant_middleware.py`) resolves the request's tenant (JWT
claim, gated `X-Tenant-ID` header) and scopes `get_conn()` to that tenant's
pool via the `set_request_tenant` ContextVar. The DICOM side applies the
same routing (`tenant_db_scope` in `backend/dcm/server.py`). A request for
tenant A physically cannot open a connection to tenant B's database.

The `tenant_id` columns on shared tables are **lineage and audit tags**,
plus the discriminator for the seeded `default` tenant whose data store IS
the main database (`uses_main_database`). They were never a read-isolation
control, and the xfail tests that asserted `WHERE tenant_id`-style read
filtering were testing a mechanism the architecture does not use.

## Decision

1. **Pool separation is the read-isolation control.** No RLS policies and
   no application-level `tenant_id` read filters will be added for RIS
   tables. Cross-tenant reads are prevented by connection routing: every
   tenant-scoped read happens on a pool bound to that tenant's own
   database.
2. **The xfail cross-tenant read tests are replaced** with real asserts of
   the routing contract (per-slug pool identity + `get_conn()` scoping),
   matching the existing `TestPoolIdentityIsolation` pattern in
   `tests/test_tenant_isolation.py`. Write-side `tenant_id` tagging tests
   stay real (they pin the lineage/audit contract and the shared-DB
   `default` tenant discriminator).
3. **RLS remains an option** if a shared-schema multi-tenant deployment is
   ever introduced (database-per-tenant → schema-per-tenant migration);
   that decision would be a new ADR and would bring the RLS policies with
   it. Until then, RLS policies would be dead code against per-tenant
   databases.

## Consequences

- No migration burden: no `ALTER TABLE ... ENABLE ROW LEVEL SECURITY`,
  no per-role policy sets, no `SET app.tenant` juggling on pooled
  connections.
- Read isolation is as strong as the provisioned database boundary —
  stronger than row filters (a missing filter clause cannot leak rows).
- New RIS tables must follow the existing conventions: write-time
  `tenant_id` tagging (lineage) and tenant-scoped pool access for reads
  (isolation). Tables owned by the shared-DB `default` tenant additionally
  rely on the tenant tag as a discriminator.
- Cross-tenant asserts in tests exercise the routing layer (mocked pools
  with distinct `db_name`), since the dev/CI environment provisions only
  the main database.
