# ADR-007: Storage Commitment, Retention/Legal-Hold & WORM

## Status
Accepted

## Date
2026-08-04

## Context
A PACS makes a custody promise to modalities: "your images are safely stored, you may purge your local cache." That promise must be verifiable (Storage Commitment), and data governance must honor legal retention clocks (5–30+ yr, pediatric) with legal-hold overrides — with **zero accidental purges** (PAC-SL-43) and **0 silent purges** (PAC-SL-21). Ransomware resilience adds immutable storage.

## Decision
Implement a **Storage-Commitment engine + retention/legal-hold policy enforcement + WORM object storage**:

- **Storage Commitment:** after C-STORE/STOW-RS completes validation and archive placement, the platform returns an SC success N-EVENT (or failure) to the modality; the scanner is only prompted to purge after success is shown (PAC-AC-P02-02). Failure → no purge signal, retry offered. SC acknowledgment < 60 s for a complete series set (PAC-SL-15).
- **Retention clocks:** `retention_policies` per facility, keyed by modality_code (NULL = default), `retention_years` 1–100, legal-hold flag; ILM runs only compliant purges.
- **Legal hold:** overrides block purges and are audit-logged; dry-run purge reports are available to admins before any batch action (sprint5 admin console).
- **WORM:** deep archive tier has object-lock/immutability enabled (PAC-SL-44, 11-nines durability) — ransomware-resilient and tamper-evident.
- **Observability:** `studies.status='QUARANTINED'` for exception paths; quota alerts at 75%/90% (PAC-AC-P04-04); 0 accidental purge accounting verified by `T-SL-43` in the QA strategy.

## Alternatives Considered

### Treat C-STORE success as sufficient (no explicit SC)
- Pros: fewer moving parts
- Cons: modality purges before durability is confirmed → silent data loss; violates the custody promise
- Rejected: SC is a hard gate G1 criterion (100% verifiable, 0 silent purges)

### Client-side retention only (delete after N years in app code)
- Pros: simple
- Cons: no legal-hold override path; no dry-run; accidental purge risk; not auditable
- Rejected: legal-hold and audit are compliance requirements (HIPAA)

### Local-only backup (no WORM)
- Pros: cheap
- Cons: ransomware-vulnerable — backups on the same LAN are deleted with production
- Rejected: WORM/immutable object-lock in cloud/hybrid is a platform decision-filter (decision guide §4.1)

## Consequences
- Modalities can safely purge local cache — the SC loop closes, protecting both scanner storage and patient data.
- Retention/legal-hold enforcement is a gate G4 criterion: 0 accidental purges, quota alerts 75/90%.
- WORM + tenant-prefixed keys (ADR-002) give a defensible ransomware posture.
- Freezegun-based tests advance retention clocks deterministically (QA strategy `fx_retention`/`fx_legal_hold`).
- Purge runs are admin-initiated with dry-run + audit, never automatic silent deletes.

## Sources
`research/pacs-ris-schema.sql` (`retention_policies`, `storage_tiers`, `storage_objects`) · `research/pacs-ris-architecture-deep-dive.md` §1.5 (ILM) · `requrements/PACS/06_acceptance_criteria.md` PAC-AC-P02-02, P04-03/04 · `requrements/PACS/05_metrics_and_slas.md` PAC-SL-15/21/43/44/45 · sprint3 (E-PAC-04 SC) · sprint5 (retention editor UI) · `requrements/PACS/go-live-checklist.md` G1/G4
