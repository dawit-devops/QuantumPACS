# Implementation Roadmap — External EMR (R16)

## Artifact Status Overview

| # | Artifact | File | Status | Notes |
|---|----------|------|--------|-------|
| 01 | User Requirements | `01-user-requirements.md` | done | 10 FRs + 7 NFRs |
| 02 | Workflow Maps | `02-workflow-maps.md` | done | W1 ADT, W2 report |
| 03 | User Stories | `03-user-stories.md` | done | 6 stories |
| 04 | UI/UX Requirements | `04-ui-ux-requirements.md` | done | FHIR/HL7 admin surface |
| 05 | Metrics & SLAs | `05-metrics-slas.md` | done | 7 KPIs |
| 06 | Acceptance Criteria | `06-acceptance-criteria.md` | done | 17 ACs |
| 07 | Traceability Matrix | `07-traceability.md` | done | 12 rows + contracts |
| 08 | Implementation Roadmap | `08-implementation-roadmap.md` | done | This file |

## FR/NFR Implementation Status

### Implemented (Passing ACs)

| FR/NFR ID | Summary | AC Coverage | Effort |
|-----------|---------|-------------|--------|
| FR-R16-01 | ADT demographics upsert — HL7 listener exists | AC-R16-01 | M |
| FR-R16-06 | FHIR R4 read endpoints — fhir-r4-api exists | AC-R16-06 | M |
| FR-R16-08 | Request logging — FHIR monitoring exists | AC-R16-08 | S |
| FR-R16-09 | Client management — FHIR admin config exists | AC-R16-09 | S |
| FR-R16-10 | Metrics — FHIR admin metrics exist | AC-R16-10 | S |

### Partially Implemented (GATED / Partial)

| FR/NFR ID | Summary | Blocking Dependency | AC | Effort |
|-----------|---------|---------------------|----|--------|
| FR-R16-03 | Order context linking | ServiceRequest mapping not confirmed | AC-R16-03 | M |
| FR-R16-07 | Dead-letter + reconciliation | Retry semantics shared with R15 not confirmed | AC-R16-07 | M |

### Missing (Not Started)

| FR/NFR ID | Summary | Reason | AC | Effort |
|-----------|---------|--------|----|--------|
| FR-R16-02 | Demographics outbound | Not wired | AC-R16-02 | M |
| FR-R16-04 | Report → DiagnosticReport | Blocked on R12 reporting endpoints | AC-R16-04 | L |
| FR-R16-05 | Results status | Depends on report delivery | AC-R16-05 | M |

## Effort Estimation Key

| Size | Days | Criteria |
|------|------|----------|
| S (Small) | 1–3 | Single component; no cross-team dependency |
| M (Medium) | 4–10 | Multi-step feature; backend + frontend coordination |
| L (Large) | 11+ | New infrastructure or integration contract |

## Dependency-Ordered Implementation Plan

### Phase 1: Foundation (done)
- ADT listener, FHIR R4 reads, FHIR admin/monitoring exist.

### Phase 2: Unblock GATED requirements (next priority)
1. **Order context mapping** — required for FR-R16-03 / AC-R16-03
   - Owner: Integration; Blocks: AC-R16-03; Effort: M
2. **Dead-letter + reconciliation (shared)** — required for FR-R16-07 / AC-R16-07
   - Owner: Backend; Blocks: AC-R16-07; Effort: M

### Phase 3: Delivery channels
3. **Report → DiagnosticReport** — FR-R16-04; blocked on R12 reporting; L
4. **Demographics outbound** — FR-R16-02; M
5. **Results status sync** — FR-R16-05; M

## Blocking Dependencies

| Blocking Dependency | Blocks | AC | Impact |
|---------------------|--------|----|--------|
| R12 reporting endpoints | FR-R16-04 | AC-R16-04 | No report delivery to EMR |
| ServiceRequest mapping | FR-R16-03 | AC-R16-03 | Imaging not linked to orders |
| Shared dead-letter semantics | FR-R16-07 | AC-R16-07 | Failures unreconciled |
| Demographics outbound wiring | FR-R16-02 | AC-R16-02 | Systems diverge on corrections |

## Next Steps (highest priority)

1. **Coordinate report delivery with R12** — unblocks AC-R16-04; L effort
2. **Order context mapping** — unblocks AC-R16-03; M effort
3. **Demographics outbound** — unblocks AC-R16-02; M effort
4. Update this roadmap each sprint as FR/NFR status changes.
