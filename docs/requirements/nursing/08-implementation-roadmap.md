# Implementation Roadmap — Radiology Service Nursing Team (R11)

## Artifact Status Overview

| # | Artifact | File | Status | Notes |
|---|----------|------|--------|-------|
| 01 | User Requirements | `01-user-requirements.md` | done | 10 FRs + 6 NFRs |
| 02 | Workflow Maps | `02-workflow-maps.md` | done | W1 safety+contrast, W2 reaction |
| 03 | User Stories | `03-user-stories.md` | done | 7 stories |
| 04 | UI/UX Requirements | `04-ui-ux-requirements.md` | done | 6 screens |
| 05 | Metrics & SLAs | `05-metrics-slas.md` | done | 7 KPIs |
| 06 | Acceptance Criteria | `06-acceptance-criteria.md` | done | 16 ACs |
| 07 | Traceability Matrix | `07-traceability.md` | done | 12 rows + deps |
| 08 | Implementation Roadmap | `08-implementation-roadmap.md` | done | This file |

## FR/NFR Implementation Status

### Implemented (Passing ACs)

| FR/NFR ID | Summary | AC Coverage | Effort |
|-----------|---------|-------------|--------|
| — | **Shared infrastructure only**: patient/medication context via patient page — no nursing-specific FR is fully implemented | (patient context ACs) | S |

### Partially Implemented (GATED / Partial)

| FR/NFR ID | Summary | Blocking Dependency | AC | Effort |
|-----------|---------|---------------------|----|--------|
| FR-R11-01 | Nursing worklist | Requires visit-status events from R08/R06/R07 | AC-R11-01 | M |
| FR-R11-09 | MAR — patient/medication context exists; no nursing-specific MAR workflow | No nursing MAR endpoints | AC-R11-09 | S |
| FR-R11-05 | Safety verification | HL7 allergy flag ingestion not confirmed | AC-R11-05 | M |

### Missing (Not Started)

| FR/NFR ID | Summary | Reason | AC | Effort |
|-----------|---------|--------|----|--------|
| FR-R11-02 | Prep checklist | No nursing endpoints | AC-R11-02 | M |
| FR-R11-03 | Vitals capture | No endpoints + offline queue | AC-R11-03 | M |
| FR-R11-04 | Contrast record | No endpoints | AC-R11-04 | M |
| FR-R11-06 | Adverse reaction escalation | No escalation wiring | AC-R11-06 | L |
| FR-R11-07 | Sedation monitoring | No endpoints | AC-R11-07 | M |
| FR-R11-08 | Recovery & discharge | No endpoints | AC-R11-08 | M |
| FR-R11-10 | Handoff notes | No endpoints | AC-R11-10 | S |

## Effort Estimation Key

| Size | Days | Criteria |
|------|------|----------|
| S (Small) | 1–3 | Single component; no cross-team dependency |
| M (Medium) | 4–10 | Multi-step feature; backend + frontend coordination |
| L (Large) | 11+ | New infrastructure or integration contract |

## Dependency-Ordered Implementation Plan

### Phase 1: Foundation (done)
- Artifacts 01–08 complete; MAR pattern identified as existing.

### Phase 2: Unblock GATED requirements (next priority)
1. **Visit-status events** — required for FR-R11-01 / AC-R11-01
   - Owner: Backend; Blocks: AC-R11-01; Effort: M
2. **HL7 allergy ingestion** — required for FR-R11-05 / AC-R11-05
   - Owner: Integration; Blocks: AC-R11-05; Effort: M

### Phase 3: Core nursing endpoints
3. **Nursing endpoints (prep, vitals, contrast, recovery, MAR)** — FR-R11-02..04, 07, 08, 09; M
4. **Offline sync queue** — FR-R11-03; M
5. **Escalation wiring** — FR-R11-06; L
6. **Handoff notes** — FR-R11-10; S

## Blocking Dependencies

| Blocking Dependency | Blocks | AC | Impact |
|---------------------|--------|----|--------|
| Visit-status events | FR-R11-01 | AC-R11-01 | Nurses unaware of arrivals |
| HL7 allergy ingestion | FR-R11-05 | AC-R11-05 | Contrast safety depends on manual flags |
| Escalation wiring | FR-R11-06 | AC-R11-06 | Reactions not escalated within SLA |
| Offline sync queue | FR-R11-03 | AC-R11-03 | Bedside documentation lost offline |

## Next Steps (highest priority)

1. **Nursing endpoints** — unblocks AC-R11-02..04/07..09; M effort
2. **Visit-status events** — unblocks AC-R11-01; M effort
3. **Escalation wiring** — unblocks AC-R11-06; L effort
4. Update this roadmap each sprint as FR/NFR status changes.
