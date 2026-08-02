# Implementation Roadmap — External PACS (R17)

## Artifact Status Overview

| # | Artifact | File | Status | Notes |
|---|----------|------|--------|-------|
| 01 | User Requirements | `01-user-requirements.md` | done | 10 FRs + 7 NFRs |
| 02 | Workflow Maps | `02-workflow-maps.md` | done | W1 store, W2 retrieve |
| 03 | User Stories | `03-user-stories.md` | done | 7 stories |
| 04 | UI/UX Requirements | `04-ui-ux-requirements.md` | done | DICOMweb/replica admin |
| 05 | Metrics & SLAs | `05-metrics-slas.md` | done | 7 KPIs |
| 06 | Acceptance Criteria | `06-acceptance-criteria.md` | done | 17 ACs |
| 07 | Traceability Matrix | `07-traceability.md` | done | 12 rows + contracts |
| 08 | Implementation Roadmap | `08-implementation-roadmap.md` | done | This file |

## FR/NFR Implementation Status

### Implemented (Passing ACs)

| FR/NFR ID | Summary | AC Coverage | Effort |
|-----------|---------|-------------|--------|
| FR-R17-01 | C-STORE receive — dcm server exists | AC-R17-01 | S |
| FR-R17-04 | QIDO-RS — dicomweb exists | AC-R17-04 | S |
| FR-R17-05 | WADO-RS — viewer consumes it | AC-R17-05 | S |
| FR-R17-09 | AE node management — DICOMweb admin exists | AC-R17-09 | S |
| FR-R17-10 | Metrics — DICOM admin metrics exist | AC-R17-10 | S |

### Partially Implemented (GATED / Partial)

| FR/NFR ID | Summary | Blocking Dependency | AC | Effort |
|-----------|---------|---------------------|----|--------|
| FR-R17-02 | C-FIND | 30s timeout semantics to verify | AC-R17-02 | S |
| FR-R17-03 | C-MOVE | Retry 2x semantics to verify | AC-R17-03 | S |
| FR-R17-06 | STOW-RS | Exists; concurrency/large-instance testing needed | AC-R17-06 | M |

### Missing (Not Started)

| FR/NFR ID | Summary | Reason | AC | Effort |
|-----------|---------|--------|----|--------|
| FR-R17-07 | Instance routing delivery log | Delivery success tracking not built | AC-R17-07 | M |
| FR-R17-08 | Archive synchronization | Replica backfill/retrieve-on-demand not confirmed | AC-R17-08 | L |

## Effort Estimation Key

| Size | Days | Criteria |
|------|------|----------|
| S (Small) | 1–3 | Single component; no cross-team dependency |
| M (Medium) | 4–10 | Multi-step feature; backend + frontend coordination |
| L (Large) | 11+ | New infrastructure or integration contract |

## Dependency-Ordered Implementation Plan

### Phase 1: Foundation (done)
- C-STORE SCP, DICOMweb QIDO/WADO, AE admin, metrics exist.

### Phase 2: Unblock GATED requirements (next priority)
1. **C-MOVE/C-FIND semantics verification** — required for FR-R17-02/03
   - Owner: Backend; Blocks: AC-R17-02, AC-R17-03; Effort: S
2. **STOW-RS hardening** — required for FR-R17-06 / AC-R17-06
   - Owner: Backend; Blocks: AC-R17-06; Effort: M

### Phase 3: Delivery and archive
3. **Routing delivery log** — FR-R17-07; M
4. **Archive synchronization** — FR-R17-08; L

## Blocking Dependencies

| Blocking Dependency | Blocks | AC | Impact |
|---------------------|--------|----|--------|
| C-MOVE retry semantics | FR-R17-03 | AC-R17-03 | Retrieves unreliable |
| Routing delivery log | FR-R17-07 | AC-R17-07 | Routing unverified |
| Archive sync contract | FR-R17-08 | AC-R17-08 | Backfill unavailable |
| STOW-RS hardening | FR-R17-06 | AC-R17-06 | Large stores fail |

## Next Steps (highest priority)

1. **Verify C-MOVE/C-FIND semantics** — unblocks AC-R17-02/03; S effort
2. **Routing delivery log** — unblocks AC-R17-07; M effort
3. **Archive synchronization contract** — unblocks AC-R17-08; L effort
4. Update this roadmap each sprint as FR/NFR status changes.
