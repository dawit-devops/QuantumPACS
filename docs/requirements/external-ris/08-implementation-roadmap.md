# Implementation Roadmap — External RIS (R15)

## Artifact Status Overview

| # | Artifact | File | Status | Notes |
|---|----------|------|--------|-------|
| 01 | User Requirements | `01-user-requirements.md` | done | 10 FRs + 7 NFRs |
| 02 | Workflow Maps | `02-workflow-maps.md` | done | W1 inbound, W2 outbound |
| 03 | User Stories | `03-user-stories.md` | done | 6 stories |
| 04 | UI/UX Requirements | `04-ui-ux-requirements.md` | done | HL7 admin surface |
| 05 | Metrics & SLAs | `05-metrics-slas.md` | done | 7 KPIs |
| 06 | Acceptance Criteria | `06-acceptance-criteria.md` | done | 17 ACs |
| 07 | Traceability Matrix | `07-traceability.md` | done | 12 rows + contracts |
| 08 | Implementation Roadmap | `08-implementation-roadmap.md` | done | This file |

## FR/NFR Implementation Status

### Implemented (Passing ACs)

| FR/NFR ID | Summary | AC Coverage | Effort |
|-----------|---------|-------------|--------|
| FR-R15-06 | HL7 ACK/NAK — listener + ACK handling exists | AC-R15-06 | S |
| FR-R15-08 | Message logging — HL7 dashboard exists | AC-R15-08 | S |
| FR-R15-09 | Config management — HL7 config screen exists | AC-R15-09 | S |

### Partially Implemented (GATED / Partial)

| FR/NFR ID | Summary | Blocking Dependency | AC | Effort |
|-----------|---------|---------------------|----|--------|
| FR-R15-01 | ORM order ingestion | Mapping of accession/procedure → worklist needs verification | AC-R15-01 | M |
| FR-R15-07 | Dead-letter + reconciliation | Retry/dead-letter semantics not confirmed | AC-R15-07 | M |
| FR-R15-10 | Metrics | HL7 admin metrics exist; reconcile with R03/R05 | AC-R15-10 | S |

### Missing (Not Started)

| FR/NFR ID | Summary | Reason | AC | Effort |
|-----------|---------|--------|----|--------|
| FR-R15-02 | Scheduling sync | Depends on R04 schedule board | AC-R15-02 | M |
| FR-R15-03 | Outbound status updates | Not wired to exam status events | AC-R15-03 | M |
| FR-R15-04 | Report delivery (ORU) | Blocked on R12 reporting endpoints | AC-R15-04 | L |
| FR-R15-05 | MWL C-FIND | SCP exists (dicom-mwl-scp); result cap to verify | AC-R15-05 | S |

## Effort Estimation Key

| Size | Days | Criteria |
|------|------|----------|
| S (Small) | 1–3 | Single component; no cross-team dependency |
| M (Medium) | 4–10 | Multi-step feature; backend + frontend coordination |
| L (Large) | 11+ | New infrastructure or integration contract |

## Dependency-Ordered Implementation Plan

### Phase 1: Foundation (done)
- HL7 listener, ACK handling, message dashboard, config exist.

### Phase 2: Unblock GATED requirements (next priority)
1. **Outbound status event wiring** — required for FR-R15-03 / AC-R15-03
   - Owner: Backend; Blocks: AC-R15-03; Effort: M
2. **Dead-letter + reconciliation** — required for FR-R15-07 / AC-R15-07
   - Owner: Backend; Blocks: AC-R15-07; Effort: M

### Phase 3: Delivery channels
3. **Report delivery (ORU)** — FR-R15-04; blocked on R12 reporting; L
4. **Scheduling sync (R04)** — FR-R15-02; M
5. **MWL C-FIND verification** — FR-R15-05; S

## Blocking Dependencies

| Blocking Dependency | Blocks | AC | Impact |
|---------------------|--------|----|--------|
| Exam status events → outbound | FR-R15-03 | AC-R15-03 | RIS unaware of completion |
| R12 reporting endpoints | FR-R15-04 | AC-R15-04 | No report delivery |
| R04 schedule board | FR-R15-02 | AC-R15-02 | Scheduling not synced |
| Retry/dead-letter semantics | FR-R15-07 | AC-R15-07 | Failed messages unreconciled |

## Next Steps (highest priority)

1. **Outbound status event wiring** — unblocks AC-R15-03; M effort
2. **Dead-letter + reconciliation** — unblocks AC-R15-07; M effort
3. **Coordinate report delivery with R12** — unblocks AC-R15-04; L effort
4. Update this roadmap each sprint as FR/NFR status changes.
