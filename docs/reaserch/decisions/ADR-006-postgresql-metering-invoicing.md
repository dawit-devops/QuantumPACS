# ADR-006: PostgreSQL Platform Database + Metering-to-Invoice Pipeline

## Status
Accepted

## Date
2026-08-04

## Context
The platform needs one transactional system of record shared by PACS, RIS, and EMR: relational clinical data (patient → study → series → instance, orders, reports), RLS-based tenancy (ADR-001), and a SaaS billing pipeline (meter → rate → invoice). Requirements: ACID transactions, declarative partitioning for hot tables (audit_log, hl7_messages, mpps_events, dicom_transactions, usage_metering), JSONB flexibility for structured payloads, and full-text/enterprise query capabilities.

## Decision
Use **PostgreSQL as the single platform database** with declarative partitioning and a metering-to-invoice pipeline:

- **Schema:** `research/pacs-ris-schema.sql` is the canonical DDL — RLS on clinical tables (ADR-001), `users`/`roles`/`permissions`/`user_roles` RBAC (ADR-004), `storage_tiers`/`retention_policies` (ADR-002), and tenant-management tables (`tenant_plans`, `tenant_subscriptions`, `tenant_feature_flags`, `usage_metering`, `tenant_invoices`, `tenant_provisioning`).
- **Partitioning:** hot append-heavy tables partitioned by month; `pg_cron` creates partitions 3–6 months ahead; per-partition autovacuum tuning.
- **Metering:** `usage_metering` (partitioned, append-only) captures `WADO_BYTES` (egress), `DICOM_TX` (transactions), `MWL_QUERIES` (worklist load); views `v_usage_daily` + `v_tenant_billable` aggregate for dashboards.
- **Invoicing:** rating rules (plan base + overage) in the app produce `tenant_invoices` (JSONB line items, `UNIQUE (facility_id, period_start, period_end)`); invoice line items must match metered usage exactly (PAC-SL-50).
- **Tenant lifecycle:** atomic stored procedures `provision_tenant()`, `suspend_tenant()`, `reactivate_tenant()`, `change_tenant_plan()`, `end_trial()` (schema §16/§17) with `tenant_lifecycle_events` audit.
- **Separation:** `tenant_invoices` (platform SaaS revenue) is intentionally separate from clinical billing (`charges`/`claims` — the patient revenue cycle).

## Alternatives Considered

### MySQL
- Pros: mature, widely deployed
- Cons: weaker JSON support, no native row-level security, weaker declarative partitioning + `set_config` tenancy pattern
- Rejected: RLS is the load-bearing isolation mechanism (ADR-001); MySQL lacks an equivalent

### Mongo / document DB
- Pros: flexible schema
- Cons: our data is inherently relational (patient → study → series → instance); manual relationship management
- Rejected: relational hierarchy + ACID state transitions are core

### Separate billing DB
- Pros: isolation of concerns
- Cons: cross-DB reconciliation, dual-write risk, no transactional guarantee between metering and invoicing
- Rejected: metering→invoice must be auditable to zero-variance (PAC-SL-50) in one system

## Consequences
- One schema version serves all tenants — no per-tenant migration drift (ADR-001 benefit realized).
- `usage_metering` partition window must be scheduled ahead; autovacuum tuning on hot tables is a Phase-4 ops item.
- Invoicing accuracy is a hard SLA (PAC-SL-50) verified by `T-SL-50` in the QA strategy; G6 pre-checks metering at Sprint 6.
- JSONB line items keep rating flexible without schema churn.
- Known gap: per-tenant backup is logical (row-scoped `COPY`/`pg_dump --table`), not physical — acceptable for shared-schema tenants; schema-per-tenant escape hatch gets its own cadence.

## Sources
`research/pacs-ris-schema.sql` (esp. §15–§17) · `research/pacs-ris-multitenancy.md` §7–§8 · `requrements/PACS/05_metrics_and_slas.md` PAC-SL-50/51/52 · sprint1 (S1-24 metering hooks, S1-26 invoice view) · sprint6 (E-PAC-09) · `requrements/qa_test_strategy.md` (T-SL-50)
