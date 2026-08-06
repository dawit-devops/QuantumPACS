# ADR-001: Shared Schema + Hardened RLS for Multi-Tenant Isolation

## Status
Accepted

## Date
2026-08-04

## Context
The platform is a multi-tenant SaaS serving PACS, RIS, and EMR across institutions (hospitals, imaging centers, IDNs, teleradiology groups). We must isolate tenant data in a way that is HIPAA-defensible, operationally simple, and does not break the platform's most valuable cross-tenant capabilities:

- **Enterprise priors sharing (XDS-I.b)** — a patient's historical studies may live under another facility's tenant; merged health systems need read-across.
- **Enterprise Master Patient Index (MPI)** reconciliation spans facilities.
- **Consolidated analytics** (KPI dashboards, metering, chargeback) are first-class requirements.
- One codebase, one schema — no per-tenant migration drift.

The classic alternatives are: app-layer `WHERE tenant_id = ?` filtering (weak), schema-per-tenant, and database-per-tenant (both operationally heavy).

## Decision
Use a **hardened shared-schema + Row-Level Security (RLS)** design for the metadata tier, with **schema-per-tenant** and **DB-per-tenant** documented as escape hatches:

- Every clinical table carries `facility_id` and has `ENABLE ROW LEVEL SECURITY` with a policy `facility_id = app_current_facility_id()`; `WITH CHECK` clauses block cross-tenant writes.
- The app sets `app.facility_id` per request via `set_config()`; production uses a `NOBYPASSRLS` app role with `FORCE ROW LEVEL SECURITY` so even app-level bugs cannot leak rows.
- A single audited **vendor operations role with `BYPASSRLS`** is the escalation path for billing, metering, and cross-facility analytics.
- `tenant_provisioning.strategy` records the isolation choice per facility; `provision_tenant()` creates tenants atomically (schema §16/§17).
- Escape hatches: promote a facility to schema-per-tenant on demand (dedicated backup cadence / unique retention law); DB-per-tenant only for air-gapped/federated deployments.

**Object storage tenancy** follows the same principle: one shared bucket with tenant-prefixed, UID-derived immutable keys (`s3://vna/{tenant_code}/{facility_id}/…`) and IAM prefix policies — see ADR-002.

## Alternatives Considered

### App-layer filtering (`WHERE tenant_id = ?`)
- Pros: simplest to start; no schema features needed
- Cons: one missed filter leaks a row; not auditable per query; cannot protect against app bugs
- Rejected: the single most common cause of multi-tenant PHI breaches

### Schema-per-tenant
- Pros: strong operational isolation; per-tenant backup; regulatory comfort for demanding tenants
- Cons: cross-tenant priors/MPI/analytics become cross-schema federation; migrations must iterate every tenant; connection routing complexity
- Rejected as primary: breaks the platform's core cross-tenant value; kept as the documented escape hatch

### DB-per-tenant
- Pros: maximum isolation; air-gap friendly
- Cons: highest ops cost; per-tenant maintenance, patching, monitoring; federation layer required
- Rejected as primary: reserved for air-gapped/federated extremes

## Consequences
- A single database safely serves many facilities; RLS enforcement lives in the database, not the app.
- RLS-critical code (tenant middleware, policy functions, grant checks) requires **100% decision-point test coverage** (see `qa_test_strategy.md` §6).
- Known gaps to close in production: `users` has no RLS (identity works across facilities) — `password_hash` must be column-GRANT-restricted to the auth service; `audit_log` is permission-gated rather than RLS-scoped so cross-facility audit reviews remain possible.
- `BYPASSRLS` ops role must be the single, audited escalation path — never ad-hoc `SET ROLE`.
- Suspension blocks the app layer (login/read gate) while RLS continues to protect data; retention still governs purge on cancel.

## Sources
`research/pacs-ris-multitenancy.md` §1–§3, §8–§9 · `research/pacs-ris-schema.sql` §5.1, §15–§17 · `requrements/RBAC_matrix_spec.md` §6 · `docs/specs/tenants_design.md` · sprint1 detail (S1-07 tenant middleware)
