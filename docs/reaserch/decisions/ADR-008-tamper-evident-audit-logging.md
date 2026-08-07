# ADR-008: Tamper-Evident Audit Logging for HIPAA & Platform Observability

## Status
Accepted

## Date
2026-08-04

## Context
HIPAA and the platform's own SLAs require **100% of view/retrieve/export/delete/share/access events** to be logged (PAC-SL-60), including cross-tenant access and denials (ADR-005). The audit log must be tamper-evident (a user with DB access must not be able to silently edit history), queryable for investigations, and cost-controlled at scale (it is one of the hottest tables).

## Decision
Implement a **structured, append-only, tamper-evident audit log**:

- **Schema:** `audit_log` (permission-gated admin-only, intentionally NOT RLS-scoped so cross-facility audit reviews remain possible — a documented exception to ADR-001) with structured columns: timestamp, actor, event type, resource, facility/tenant context; partitioned by month.
- **Coverage:** view/retrieve/export/delete/share/access events, login/tenant-lifecycle events (`tenant_lifecycle_events`), cross-tenant grant events (`cross_tenant.grant.created`/`denied`), and token/role changes (PAC-AC-P19-02).
- **Tamper-evidence:** append-only writes (app role has INSERT-only grants; no UPDATE/DELETE on closed partitions), hash-chaining of events (each row references the prior row's hash) **or equivalent integrity mechanism** — a new mechanism to be added at implementation time (not yet in `pacs-ris-schema.sql`), so future readers should not assume it exists today — plus WORM object-store mirror for long-term evidence (ADR-007).
- **Queryability:** admin audit viewer with structured filters (event type/date/actor/tenant), cursor pagination, and CSV export — per `docs/specs/audit-logs_design.md` (PAC-UI-32).
- **Observability hook:** audit completeness is itself monitored (100% target, PAC-SL-60) and verified by `T-SL-60` in the QA strategy; G6 evidence includes audit completeness checks.

## Alternatives Considered

### App-level logging to application logs
- Pros: trivial
- Cons: not structured/queryable per event type; tenants of the log rotate/delete; no tamper evidence
- Rejected: cannot satisfy HIPAA or investigation workflows

### External SIEM only
- Pros: aggregation + alerting
- Cons: same capture problem — depends on what the app forwards; cost at imaging volume
- Rejected as sole store: a canonical platform store is needed; SIEM can consume a feed from it

### Full RLS scoping of audit rows
- Pros: consistent with ADR-001
- Cons: cross-facility audit reviews (the point of an audit log for a SaaS operator) would be blocked
- Rejected: admin-gated access + partition immutability gives the right balance (documented deviation)

## Consequences
- Every sensitive event is reconstructable per tenant — the basis for HIPAA breach-response and the G6 gate.
- Partition immutability + hash-chaining make retroactive edits detectable (tamper-evident).
- The audit table is hot: monthly partitions, autovacuum tuning, and an archive/retention policy for evidence are ops responsibilities (ADR-006).
- Audit viewer ships in sprint1 (S1-16) and the console (PAC-UI-32); evidence artifacts in the go-live checklist cite audit queries per gate.

## Sources
`docs/specs/audit-logs_design.md` · `research/pacs-ris-schema.sql` (`audit_log` §, partitions) · `research/pacs-ris-multitenancy.md` §5.1 note · `requrements/PACS/05_metrics_and_slas.md` PAC-SL-60/61 · `requrements/PACS/06_acceptance_criteria.md` PAC-AC-P20-03 · sprint1 (S1-14 triggers, S1-16 viewer) · `requrements/qa_test_strategy.md` T-SL-60
