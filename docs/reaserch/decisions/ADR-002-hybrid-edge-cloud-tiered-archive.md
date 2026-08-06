# ADR-002: Hybrid Edge + Cloud Tiered Archive for Pixel Storage

## Status
Accepted

## Date
2026-08-04

## Context
PACS must store petabytes of DICOM pixel data with clinically safe retrieval latency and economically sustainable cost. Research (`pacs-ris-platform-decision-guide.md`) compared on-prem PACS, VNA+cloud hybrid, and full cloud-native. The platform is multi-site and multi-tenant (IDNs, teleradiology), so:

- Active-study retrieval must be LAN-speed (`< 2–3 s`, PAC-SL-10/11) even over constrained WAN links.
- Deep archive must be cheap (Glacier-class) for 5–30+ year retention.
- Ransomware resilience requires immutable (WORM) storage.
- DR must meet RTO ≤ 4 h / RPO ≤ 60 min (PAC-SL-03/04) with active reads continuing during a region outage.

## Decision
Adopt a **hybrid architecture: local edge cache + cloud object storage with lifecycle tiering**, one shared bucket with tenant-prefixed, UID-derived immutable keys:

- **Edge cache (hot):** recent/active studies staged at the reading site (TIER1_HOT, 0–30 d, < 2 s retrieval). During a cloud-region outage, active reads continue from edge; ingestion buffers.
- **Warm tier (TIER2_WARM):** cloud standard storage, 1–12 months, < 10 s retrieval.
- **Deep archive (TIER3_ARCHIVE):** cold/Glacier-class, 5–30+ yr, < 60 s retrieval, WORM/object-lock enabled for ransomware resilience.
- **ILM:** lifecycle policies auto-migrate between tiers (recent 0–2 yr high-performance; older 2–7+ yr auto-transition); prefetch policies stage priors to the edge before read time (≥ 95% availability, PAC-SL-24).
- **Storage Commitment:** a study is only "safe to purge" on the modality when the archive confirms custody — 100% verifiable, 0 silent purges (PAC-SL-21).
- Key layout `s3://vna/{tenant_code}/{facility_id}/{study}/{series}/{sop}.dcm` with IAM prefix policies; immutable UID-derived keys mean one tenant can never overwrite another's object. *(Source `pacs-ris-multitenancy.md` §4 specifies the `{tenant_code}/{facility_id}/…` prefix; the `{study}/{series}` sub-path depth is our implementation refinement, chosen to keep lifecycle-policy filters on study boundaries.)*

## Alternatives Considered

### On-prem PACS (proprietary archive)
- Pros: full control; no egress fees
- Cons: high CapEx + refresh cycles every 5–7 yr; highest staffing burden; ransomware-vulnerable (backups on same LAN); no elastic scale
- Rejected: wrong fit for a multi-tenant SaaS platform

### Full cloud-native (no edge)
- Pros: zero CapEx, elastic, best for teleradiology/greenfield
- Cons: depends on robust WAN; large modalities (tomosynthesis, CINE, PET-CT > 500 MB) over weak links hurt
- Rejected as primary: the platform must serve high-acuity trauma centers and bandwidth-sensitive sites — edge caching is required; cloud-native is the model for well-connected/greenfield tenants

### Bucket-per-tenant
- Pros: extreme isolation
- Cons: tiering-policy duplication per bucket; bucket-limit exhaustion at scale
- Rejected: kept as documented escape hatch only (per `pacs-ris-multitenancy.md` §4)

## Consequences
- LAN-speed reads for active studies, cheap deep archive, WORM resilience, and geo-redundant DR all hold simultaneously.
- Egress is the dominant imaging cost — metered (`WADO_BYTES`) and rate-limited per plan (see ADR-006).
- Edge cache introduces data-sync and eviction complexity; prefetch policy must be tuned per site (staged hybrid tiering).
- Migration of legacy archives uses the same tiered model (hot for recent, cold for old) with count reconciliation (PAC-AC-P04-09).
- Retrieval latency SLAs (PAC-SL-40/41/42) are the acceptance criteria for the storage layer.

## Sources
`research/pacs-ris-platform-decision-guide.md` §1–§6 · `research/pacs-ris-architecture-deep-dive.md` §1.5–§1.6 · `research/pacs-ris-multitenancy.md` §4 · `research/pacs-ris-schema.sql` (`storage_tiers`, `storage_objects`, `retention_policies`) · `requrements/PACS/05_metrics_and_slas.md` PAC-SL-40…45 · sprint3 (E-PAC-04) · sprint6 (E-PAC-10 DR)
