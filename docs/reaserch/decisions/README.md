# Architecture Decision Records — Platform (PACS · RIS · EMR)

**Location:** `requrements/decisions/` · **Convention:** numbered `ADR-NNN-<slug>.md` · **First issued:** 2026-08-04

These records capture the *why* behind the platform's significant, expensive-to-reverse architectural decisions. Each ADR follows the same structure — **Status / Date / Context / Decision / Alternatives Considered / Consequences / Sources** — and links back to the source specs, schema, and sprint docs so the rationale is traceable.

> **How to use:** before re-deciding an architectural question (isolation model, storage tiering, protocol surface, auth, billing…), read the relevant ADR first. If a decision changes, **write a new ADR that supersedes the old one — never edit an Accepted ADR's decision in place.**

## Index

| # | Decision | Status | Supersedes |
| :-: | :--- | :--- | :--- |
| [ADR-001](ADR-001-shared-schema-rls-multitenancy.md) | Shared schema + hardened RLS for multi-tenant isolation (escape hatches: schema-per-tenant / DB-per-tenant) | Accepted | — |
| [ADR-002](ADR-002-hybrid-edge-cloud-tiered-archive.md) | Hybrid edge cache + cloud tiered archive (hot/warm/deep, WORM, tenant-prefixed keys) | Accepted | — |
| [ADR-003](ADR-003-dicomweb-gateway-dicom-dual-path.md) | DICOMweb gateway + DIMSE dual-path interoperability (one metadata index) | Accepted | — |
| [ADR-004](ADR-004-identity-rbac-authorization.md) | IHE IUA/OAuth2 identity + facility-scoped RBAC | Accepted | — |
| [ADR-005](ADR-005-cross-tenant-grants.md) | Cross-tenant grants (teleradiology / IDN priors) with RLS default-deny | Accepted | — |
| [ADR-006](ADR-006-postgresql-metering-invoicing.md) | PostgreSQL platform DB + metering-to-invoice pipeline | Accepted | — |
| [ADR-007](ADR-007-storage-commitment-retention-worm.md) | Storage Commitment + retention/legal-hold + WORM (0 accidental purges) | Accepted | — |
| [ADR-008](ADR-008-tamper-evident-audit-logging.md) | Tamper-evident audit logging (append-only, admin-gated) | Accepted | — |
| [ADR-009](ADR-009-zero-footprint-dicomweb-viewer.md) | Zero-footprint DICOMweb viewer with progressive streaming | Accepted | — |

## Lifecycle

```
PROPOSED → ACCEPTED → (SUPERSEDED | DEPRECATED)
```

- **PROPOSED** — drafted, under review; use for decisions being deliberated.
- **ACCEPTED** — decided; implementation proceeds against it.
- **SUPERSEDED by ADR-NNN** — a later decision changed this one; keep the old record (historical context), point the reader at the replacement.
- **DEPRECATED** — no longer applicable, not replaced.

**Rules:**
1. Never delete an ADR. They capture historical context.
2. A changed decision = a **new** ADR referencing the superseded one (e.g., `Superseded by ADR-012` in the old file, `Supersedes ADR-005` in the new).
3. Numbering is sequential and never reused; next free number after ADR-009 is **ADR-010**.

## Template

Copy the skeleton below for new records (matching this suite's conventions):

```markdown
# ADR-NNN: <Decision Title>

## Status
Accepted | Proposed | Superseded by ADR-XXX | Deprecated

## Date
YYYY-MM-DD

## Context
Why this decision matters: the requirements, constraints, and trade-offs at stake.
Link the driving requirements (AC/SL IDs) and source docs.

## Decision
What was decided, concretely and implementably.

## Alternatives Considered
### <Alternative A>
- Pros: …
- Cons: …
- Rejected: why

## Consequences
Positive and negative outcomes, follow-ups, known gaps, and acceptance criteria.

## Sources
The specs, schema sections, and sprint docs that ground this decision.
```

## Related deliverables

- `requrements/README.md` — the document-set index (deliverable list) · `requrements/qa_test_strategy.md` — how decisions are verified · `research/pacs-ris-multitenancy.md` / `research/pacs-ris-platform-decision-guide.md` — the research basis for ADR-001/002
