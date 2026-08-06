# Multi-Tenant Architecture for the PACS + RIS Platform

**Team:** `pacs-ris-research` · **Compiled:** 2026-08-04 · Companion to `research/pacs-ris-schema.sql` (§15) and `research/pacs-ris-schema.md`

This document applies the multi-tenant SaaS patterns (isolation strategies, tenant resolution, provisioning, metering, billing) to the PACS + RIS platform whose PostgreSQL schema lives in `pacs-ris-schema.sql`. It explains the isolation decision, how the schema implements it, and the operational model for running imaging as a multi-tenant SaaS.

---

## 1. Executive Summary

The platform serves **facilities** (hospitals, imaging centers, outreach clinics) as tenants. The schema currently implements the **shared-schema (discriminator) strategy**: every clinical table carries `facility_id` and is protected by row-level security (RLS) scoped to `app.facility_id`. The generic multi-tenant guidance ranks this strategy as the *weakest* isolation and flags it as risky under HIPAA.

**This document's position:** for medical imaging specifically, a **hardened shared-schema + RLS design is the right primary strategy**, because the platform's most valuable capabilities are inherently cross-tenant:

- **Enterprise priors sharing** (XDS-I.b) means a patient's historical studies may live under another facility's tenant - a merged health system needs read-across, which shared schema makes natural.
- **Enterprise Master Patient Index (MPI)** reconciliation spans facilities.
- **Consolidated analytics** across a health system (our KPI and cost tools) are first-class requirements.

The "weak isolation" label applies to naive `WHERE tenant_id = ?` filtering. Database-enforced RLS with `NOBYPASSRLS` + `FORCE ROW LEVEL SECURITY` and audit triggers closes the leak channel at the storage layer, not the app layer. **Schema-per-tenant is the documented escape hatch** for deployments that demand stronger operational isolation; **DB-per-tenant** is reserved for air-gapped/federated extremes. Section 3 scores this decision explicitly.

Section 15 of `pacs-ris-schema.sql` adds the tenant-management tables this strategy needs: `tenant_plans`, `tenant_subscriptions`, `tenant_feature_flags`, `usage_metering` (partitioned), `tenant_invoices`, and `tenant_provisioning`.

---

## 2. Where the Platform Stands Today

| Concern | Implementation in `pacs-ris-schema.sql` |
| :--- | :--- |
| Tenant root | `facilities` (the RLS scope; one legal entity per row) |
| Tenant column | `facility_id` on every clinical row (patients, orders, studies, reports, charges, ...) |
| Enforcement | `ENABLE ROW LEVEL SECURITY` + `facility_id = app_current_facility_id()` policies on 24+ tables (30 after the §15/§17 tenant tables) |
| Identity | `users` are global; `user_roles` grants are facility-scoped (a user can be a Radiologist at NGH and a Technologist at the outreach clinic) |
| Session context | `SET app.facility_id` per request; `app_current_facility_id()` helper |
| Audit | `audit_log_change()` triggers write facility-scoped, partitioned audit rows |
| Platform tables | `users`, `roles`, `permissions`, `role_permissions`, `tenant_plans` deliberately have NO RLS (cross-tenant by nature) |

This already satisfies the multi-tenant skill's **Phase 1 (Tenant Awareness)**: tenant column everywhere, tenant lookup table, tenant-aware middleware (`SET CONFIG`), all queries tenant-filtered via RLS, and audit with tenant context. Phases 2-4 are the new material in section 15 and sections 5-7 below.

---

## 3. Isolation Strategy Decision

### 3.1 Scorecard (weighted for medical imaging)

Scoring 1-5; weights reflect what matters for a HIPAA-governed, multi-site imaging platform.

| Criterion | Weight | Shared schema + RLS | Schema-per-tenant | DB-per-tenant |
| :--- | ---: | :---: | :---: | :---: |
| Isolation strength | 20% | 3 | 5 | 5 |
| Cross-facility priors (XDS-I.b) | 15% | 5 | 2 | 1 |
| Enterprise MPI reconciliation | 10% | 5 | 2 | 1 |
| Consolidated analytics / KPIs | 10% | 5 | 3 | 2 |
| Migration / ops cost (schema per facility) | 15% | 5 | 2 | 1 |
| Connection / infra cost | 10% | 5 | 4 | 2 |
| Per-tenant backup & restore | 10% | 2 | 4 | 5 |
| Regulatory comfort (HIPAA) | 10% | 3 | 4 | 5 |
| **Weighted total** | | **4.10** | **3.30** | **2.80** |

**Recommendation: shared schema + hardened RLS** for the metadata tier, with **schema-per-tenant** as the documented escalation path for tenants that demand stronger operational isolation (e.g. a trauma center that wants its own backup cadence). The two "low" shared-schema scores are directly mitigable: per-tenant backup via row-level logical dumps keyed on `facility_id` (see §8), and regulatory comfort via the controls matrix in §9.

### 3.2 Why "shared schema is weak for HIPAA" is mitigated here

The generic warning targets **app-layer filtering** (`WHERE tenant_id = ?` in every query - one missed filter leaks). This schema moves enforcement to the **database**:

```sql
ALTER TABLE patients ENABLE ROW LEVEL SECURITY;
CREATE POLICY rls_all ON patients
  FOR ALL USING (facility_id = app_current_facility_id())
          WITH CHECK (facility_id = app_current_facility_id());
```

- An app bug can no longer leak a row: the planner applies the policy regardless of the query.
- `WITH CHECK` also blocks cross-tenant *writes* (a query cannot insert a row for another facility).
- Production adds `FORCE ROW LEVEL SECURITY` on clinical tables and grants the app role `NOBYPASSRLS`, so even the app's own DBA-tier SQL is constrained.
- The vendor **operations role** (billing, metering, cross-facility analytics) gets `BYPASSRLS` deliberately - a single, auditable escalation path instead of many ad-hoc queries.

### 3.3 Imaging-specific complications shared schema solves

1. **Priors across facilities.** A stroke patient scanned at the main campus arrives at the outpatient center with a CTA. The reading physician needs the priors. With schema-per-tenant this requires a cross-schema query (or a federation layer); with shared schema it is a deliberate, policy-gated read-across (e.g. an `XDS-I.b` service that runs as a `BYPASSRLS` role under audit).
2. **MPI deduplication.** `patient_identifiers` already models enterprise identity; consolidating duplicate MRNs after a merger is a simple upsert, not a data migration across schemas.
3. **One codebase, one schema.** Every tenant runs the same schema version - no per-tenant migration drift (the multi-tenant skill's schema-per-tenant con: "migration must iterate all tenants").

### 3.4 The escape hatches (documented, not deployed)

| Trigger | Action |
| :--- | :--- |
| A tenant demands dedicated backup/DR or has unique retention law | Promote that `facility_id` to **schema-per-tenant**: copy the template schema, point a connection router at it. `tenant_provisioning.strategy` records the per-tenant choice. |
| Air-gapped / federated deployment (VA-style) | **DB-per-tenant**; connection routing at the API layer, federation for reporting. |
| Observed RLS policy drift or a cross-tenant incident | **Incident response**: quarantine the tenant via `tenant_subscriptions.status = 'SUSPENDED'` (RLS still works, reads become blocked by an app-level gate) while migrating to schema-per-tenant. |

---

## 4. Object Storage Tenancy (PACS-specific)

The metadata tier is only half of a PACS; pixels live in object storage (`storage_objects.object_key`). Tenancy there follows the same principle: **one shared bucket, tenant-scoped key prefixes, IAM boundary policies** - not a bucket per tenant.

```
s3://vna/{tenant_code}/{facility_id}/1.2.826.0.1.3680043...dcm
        ^^^^^^^^^^^ shared bucket    ^^^^ tenant prefix (matches facilities.code)
```

- **Shared bucket + prefixes**: near-zero cost for new tenants, no bucket-limit exhaustion, simple lifecycle tiering.
- **Isolation** via IAM: each app role gets `s3:GetObject` on `arn:aws:s3:::vna/{tenant_code}/*`; the metadata database (the actual index) is already RLS-scoped.
- **Immutable object keys** (UID-derived) mean a tenant can never overwrite another's object even with a misconfigured policy.
- A **bucket-per-tenant** variant is the documented escape hatch for extreme isolation, at the cost of tiering-policy duplication.

---

## 5. Tenant Resolution

### 5.1 Web/API layer

The multi-tenant skill lists five resolution strategies; the platform maps them as:

| Strategy | Use | Notes |
| :--- | :--- | :--- |
| Subdomain (`ngh.portal.example.com`) | Primary for the web console | The frontend's facility selector sets `app.facility_id`; a host-based router derives it in production |
| Custom domain (`imaging.northgate.org`) | Enterprise tenants | CNAME to the portal, verified certificate |
| `X-Tenant-ID` header | API clients (FHIR, DICOMweb) | Validated against the JWT's facility claim before use |
| JWT claim (`"facility_id": 1`) | Auth'd API sessions | The canonical source after login; header only hints |
| Path (`/api/v1/facilities/1/...`) | Billing/ops endpoints | Mostly internal |

Resolution order (mirroring the skill's middleware): **JWT claim wins, then header, then subdomain**; a mismatch between header and JWT is rejected, not silently merged. The schema's `app.facility_id` is set from the resolved tenant for the duration of the request.

### 5.2 DICOM/HL7 layer (the imaging wrinkle)

Modalities and HL7 senders do not do web auth. Tenant resolution for machine traffic is **AE-title + IP allow-list** (the `modalities.station_ae_title` + `interface_endpoints.host/port/ae_title` tables already carry `facility_id`). A modality is *assigned* to a facility at provisioning time; a C-STORE from an unknown AE title is rejected and logged - a tenant boundary that DICOM itself does not provide.

---

## 6. Provisioning Lifecycle (Skill Phase 2)

`tenant_subscriptions.status` implements the lifecycle:

```
TRIAL ──► ACTIVE ──► PAST_DUE ──► SUSPENDED ──► CANCELLED
              ▲                       │
              └──────── reactivate ───┘
```

`tenant_provisioning` records the isolation strategy and stage for each tenant (`QUEUED → PROVISIONING → MIGRATING → SEEDING → READY`), so a mixed deployment (mostly shared-schema, one schema-per-tenant outlier) stays auditable.

**Provisioning flow for a new facility:**

1. Insert `facilities` row (tenant root) + `tenant_subscriptions` (TRIAL, plan from signup).
2. Create `user_roles` for the tenant admin; seed `departments`, `modalities`, `rooms`, `retention_policies` from defaults.
3. Set `tenant_provisioning.strategy = 'SHARED_SCHEMA'`; stage to `READY` after seed.
4. If the tenant chose the escape hatch, a provisioning job clones the template schema instead (stage `MIGRATING`), and the connection router pins that facility.

**Implemented atomically in schema §16:** the `provision_tenant()` stored procedure runs steps 1-3 in a single transaction - it validates inputs (code format, plan, billing cycle, admin tuple), inserts the facility, scopes RLS to the new facility via `set_config('app.facility_id', ..., true)` so the tenant-scoped tables accept the seed, creates the TRIAL subscription with correct period/trial dates, seeds departments/modalities/rooms/retention policies/report template, optionally creates the tenant admin (`users` + facility-scoped `user_roles`), walks `tenant_provisioning` through PROVISIONING → SEEDING → READY, and returns a JSONB receipt (`facility_id`, `subscription_id`, `provisioning_id`, `trial_ends_at`, ...). Any failure rolls the whole thing back - no half-provisioned tenants. It runs under the vendor ops role (BYPASSRLS) or with `app.facility_id` set.

**Implemented atomically in schema §17:** the lifecycle transitions are stored procedures too - `suspend_tenant()` (TRIAL/ACTIVE/PAST_DUE → SUSPENDED), `reactivate_tenant()` (SUSPENDED → TRIAL if the trial window hasn't lapsed, else ACTIVE), `change_tenant_plan()` (rebases the current OPEN invoice onto the new plan's price; no proration in the demo), and `end_trial()` (TRIAL → ACTIVE and opens the first OPEN invoice the moment billing begins). Each updates `tenant_subscriptions`, writes an immutable row to the new `tenant_lifecycle_events` audit table, stamps `tenant_provisioning.state`, and rolls the whole thing back on any failure. The `require_tenant_scope()` guard refuses cross-facility operations from a scoped session, and `provision_tenant()` opens the trail with a `TRIAL_STARTED` event.

**Suspension semantics:** `SUSPENDED` blocks the *app* (login gate + read gate in middleware); RLS continues to protect data. On `CANCELLED`, retention policies still govern the legal hold before any purge (see `retention_policies.legal_hold`).

---

## 7. Usage Metering & Billing (Skill Phase 4)

The skill's pipeline maps directly onto the schema:

```
Metering ─────► Aggregation ────► Rating ────► Invoicing
usage_metering   v_usage_daily     (SQL / pricing    tenant_invoices
(partitioned)                      rules in app)
```

| Meter | Source in this platform | Why it matters |
| :--- | :--- | :--- |
| `WADO_BYTES` | `dicom_transactions` (WADO-RS) | Egress is the dominant imaging cost (the cost worksheet's egress line) |
| `DICOM_TX` | `dicom_transactions` | Traffic volume / capacity planning |
| `MWL_QUERIES` | `worklist_entries.query_count` | Scanner load, a Phase-0 KPI |
| `STUDIES_STORED` | `studies` inserts | Storage growth metering |
| `API_CALLS` | API gateway | General SaaS metering |
| `ACTIVE_USERS` | `user_roles` + session logins | Seat-based billing |

**Billing model:** per-tenant invoicing (each facility pays its plan + overage). `tenant_invoices.line_items` holds the rated breakdown; `base_amount` from the plan, `overage_amount` from egress/storage over limits. For a health system that owns several facilities, the skill's *consolidated* question is answered by billing the parent org at the platform level while retaining per-facility `tenant_invoices` for internal chargeback.

The existing clinical billing (`charges`, `claims` - the *patient* revenue cycle) is intentionally separate from `tenant_invoices` (the *platform* revenue). The former bills insurers for exams; the latter bills facilities for SaaS usage. Both are metered from the same underlying tables.

---

## 8. Operations

| Concern | Shared-schema approach |
| :--- | :--- |
| Partition maintenance | `pg_cron` creates monthly partitions ahead for `audit_log`, `hl7_messages`, `mpps_events`, `dicom_transactions`, `usage_metering` |
| Per-tenant backup | Logical, tenant-scoped: `COPY (SELECT * FROM patients WHERE facility_id = X)` style dumps, or `pg_dump --table` + filter for the escape-hatch tenants |
| Per-tenant monitoring | Aggregates in `v_tenant_billable` + `v_usage_daily`; interface health already facility-scoped |
| Cross-tenant analytics | `v_usage_daily` / `v_tenant_billable` (vendor ops, `BYPASSRLS`) instead of per-tenant queries |
| Vacuum / bloat | Per-partition autovacuum tuning on the hot tables; watch `usage_metering` writes |

---

## 9. Security Controls Matrix

| Isolation surface | Control | Status |
| :--- | :--- | :--- |
| Clinical rows | RLS policy on `facility_id` (SELECT/INSERT/UPDATE/DELETE) | ✅ schema |
| App role | `NOBYPASSRLS` + `FORCE ROW LEVEL SECURITY` in production | ⚠️ deployment step |
| Writes across tenants | `WITH CHECK` clause on all policies | ✅ schema |
| Vendor ops escalation | Single `BYPASSRLS` role, audited | ✅ documented |
| Machine traffic (DICOM/HL7) | AE-title + IP allow-list per facility | ✅ schema (`modalities`, `interface_endpoints`) |
| Credentials | `users.password_hash` readable by any role today | ⚠️ known gap - restrict via column GRANT to auth service (see schema §5.1 note) |
| Audit | Facility-scoped `audit_log` via triggers | ✅ schema |
| Tenant lifecycle | `SUSPENDED` blocks app reads; RLS persists | ✅ schema + middleware |

---

## 10. New Tables (Schema §15)

| Table | Purpose | Key design |
| :--- | :--- | :--- |
| `tenant_plans` | Plan catalog | Feature map as JSONB; storage/user/modality limits; platform-level (no RLS) |
| `tenant_subscriptions` | One row per facility | Status lifecycle CHECK; `UNIQUE (facility_id)`; seats + storage counters |
| `tenant_feature_flags` | Per-tenant feature overrides | `UNIQUE (facility_id, flag)` |
| `usage_metering` | Metered usage events | Partitioned by month; `UNIQUE` not needed (append-only events) |
| `tenant_invoices` | Invoicing output | Line items as JSONB; `UNIQUE (facility_id, period_start, period_end)` |
| `tenant_provisioning` | Isolation-strategy provenance | Records shared vs. schema-per-tenant choice per facility |

Views: `v_usage_daily` (aggregation step) and `v_tenant_billable` (current-period posture per tenant, for the SaaS ops dashboard).

---

## 11. Migration Roadmap (Today → Multi-Tenant SaaS)

The current schema is effectively at the skill's Phase 1. Remaining steps:

1. **Provisioning automation (Phase 2):** done - `provision_tenant()` in schema §16 implements the "new facility" flow (section 6) as one atomic transaction; wire the tenant-ops console's "Provision tenant" action to call it.
2. **Tenant middleware (Phase 1 completion):** the API layer resolves the tenant (section 5), validates it against the JWT, and executes `SET app.facility_id = :id` per request; reject unset tenant IDs for clinical routes.
3. **Force RLS (Phase 3 hardening):** create the `NOBYPASSRLS` app role, `FORCE ROW LEVEL SECURITY`, grant DML, and add the audited `BYPASSRLS` ops role.
4. **Metering instrumentation (Phase 4):** write meters from `dicom_transactions` (WADO bytes), `studies` inserts, and API gateway logs into `usage_metering`; schedule the monthly partition window.
5. **Billing integration (Phase 4):** rating rules (plan + overage) produce `tenant_invoices`; integrate with a payment provider for invoicing.
6. **Object storage tenancy (section 4):** apply tenant-prefix IAM policies to the VNA bucket.

---

## 12. Sources

- `pacs-ris-schema.sql` §15 - multi-tenant tables, RLS, views, seed
- `pacs-ris-schema.sql` §16/§17 - tenant provisioning + lifecycle stored procedures (atomic, audited)
- `pacs-ris-schema.md` §5.1 - RLS pattern and the documented `users.password_hash` control gap
- `pacs-ris-research.md` §7 - why merged health systems need enterprise identity and cross-facility workflows
- `pacs-ris-architecture-deep-dive.md` §1, §4 - VNA / object storage reference architecture
- Multi-tenant SaaS patterns skill - isolation strategies, tenant resolution, provisioning, metering/billing pipeline
