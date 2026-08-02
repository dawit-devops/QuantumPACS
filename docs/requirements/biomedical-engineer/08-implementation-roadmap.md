# Implementation Roadmap — Biomedical Engineer (R10)

## Artifact Status Overview

| # | Artifact | File | Status | Notes |
|---|----------|------|--------|-------|
| 01 | User Requirements | `01-user-requirements.md` | done | 10 FRs + 6 NFRs |
| 02 | Workflow Maps | `02-workflow-maps.md` | done | W1 downtime, W2 PM/QC |
| 03 | User Stories | `03-user-stories.md` | done | 6 stories |
| 04 | UI/UX Requirements | `04-ui-ux-requirements.md` | done | 7 screens |
| 05 | Metrics & SLAs | `05-metrics-slas.md` | done | 7 KPIs |
| 06 | Acceptance Criteria | `06-acceptance-criteria.md` | done | 16 ACs |
| 07 | Traceability Matrix | `07-traceability.md` | done | 12 rows + deps |
| 08 | Implementation Roadmap | `08-implementation-roadmap.md` | done | This file |

## FR/NFR Implementation Status

### Implemented (Passing ACs)

| FR/NFR ID | Summary | AC Coverage | Effort |
|-----------|---------|-------------|--------|
| — | **Shared infrastructure only**: audit-log infra (`/logs`) — no equipment-specific FR is fully implemented | (audit ACs) | S |

### Partially Implemented (GATED / Partial)

| FR/NFR ID | Summary | Blocking Dependency | AC | Effort |
|-----------|---------|---------------------|----|--------|
| FR-R10-07 | Fault alerting | Requires notification event wiring (R01 gap shared) | AC-R10-07 | M |
| FR-R10-10 | Audit of changes — shared `/logs` exists; no equipment-specific audit view | No equipment audit view | AC-R10-10 | S |

### Missing (Not Started)

| FR/NFR ID | Summary | Reason | AC | Effort |
|-----------|---------|--------|----|--------|
| FR-R10-01 | Equipment registry | No endpoints | AC-R10-01 | M |
| FR-R10-02 | PM schedule | Depends on registry | AC-R10-02 | M |
| FR-R10-03 | QC records | Depends on registry | AC-R10-03 | M |
| FR-R10-04 | Downtime tracking | Needs exam-scheduling integration | AC-R10-04 | M |
| FR-R10-05 | Work orders | No endpoints | AC-R10-05 | M |
| FR-R10-06 | Vendor contracts | No endpoints | AC-R10-06 | S |
| FR-R10-08 | Uptime/compliance reporting | Needs aggregates shared with R03 | AC-R10-08 | M |
| FR-R10-09 | Parts inventory | Not scoped | AC-R10-09 | L |

## Effort Estimation Key

| Size | Days | Criteria |
|------|------|----------|
| S (Small) | 1–3 | Single component; no cross-team dependency |
| M (Medium) | 4–10 | Multi-step feature; backend + frontend coordination |
| L (Large) | 11+ | New infrastructure or integration contract |

## Dependency-Ordered Implementation Plan

### Phase 1: Foundation (done)
- Artifacts 01–08 complete; audit infrastructure identified as existing.

### Phase 2: Unblock GATED requirements (next priority)
1. **Notification event wiring** — required for FR-R10-07 / AC-R10-07
   - Owner: Backend; Blocks: AC-R10-07; Effort: M
   - Once done, re-run validator gate on AC-R10-07.

### Phase 3: Core registry and workflows
2. **Equipment registry endpoints** — FR-R10-01; M
3. **PM/QC endpoints** — FR-R10-02/03; M
4. **Downtime + scheduling integration** — FR-R10-04; M
5. **Work orders** — FR-R10-05; M
6. **Reports aggregates (with R03)** — FR-R10-08; M
7. **Contracts** — FR-R10-06; S
8. **Parts inventory** — FR-R10-09; L

## Blocking Dependencies

| Blocking Dependency | Blocks | AC | Impact |
|---------------------|--------|----|--------|
| Equipment registry endpoints | FR-R10-02..05 | AC-R10-02..05 | No equipment tracking |
| Downtime ↔ scheduling integration | FR-R10-04 | AC-R10-04 | Exams scheduled on down modalities |
| Notification wiring | FR-R10-07 | AC-R10-07 | Faults not escalated |
| R03 metrics aggregates | FR-R10-08 | AC-R10-08 | Director lacks uptime view |

## Next Steps (highest priority)

1. **Equipment registry endpoints** — unblocks AC-R10-01..05; M effort
2. **Notification event wiring** — unblocks AC-R10-07; M effort
3. **Downtime ↔ scheduling integration** — unblocks AC-R10-04; M effort
4. Update this roadmap each sprint as FR/NFR status changes.
