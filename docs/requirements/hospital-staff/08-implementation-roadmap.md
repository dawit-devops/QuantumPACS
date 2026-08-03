# Implementation Roadmap — Other Hospital Staff (R19)

## Artifact Status Overview

| # | Artifact | File | Status | Notes |
|---|----------|------|--------|-------|
| 01 | User Requirements | `01-user-requirements.md` | done | 10 FRs + 6 NFRs |
| 02 | Workflow Maps | `02-workflow-maps.md` | done | W1 results check, W2 notification |
| 03 | User Stories | `03-user-stories.md` | done | 6 stories |
| 04 | UI/UX Requirements | `04-ui-ux-requirements.md` | done | 6 screens, mobile-first |
| 05 | Metrics & SLAs | `05-metrics-slas.md` | done | 6 KPIs |
| 06 | Acceptance Criteria | `06-acceptance-criteria.md` | done | 16 ACs |
| 07 | Traceability Matrix | `07-traceability.md` | done | 12 rows + deps |
| 08 | Implementation Roadmap | `08-implementation-roadmap.md` | done | This file |

## FR/NFR Implementation Status

### Implemented (Passing ACs)

| FR/NFR ID | Summary | AC Coverage | Effort |
|-----------|---------|-------------|--------|
| — | **Shared infrastructure only**: read-only share-link viewer + shared audit infra (`/logs`) — no portal-specific FR is fully implemented | (viewer/audit ACs) | S |

### Partially Implemented (GATED / Partial)

| FR/NFR ID | Summary | Blocking Dependency | AC | Effort |
|-----------|---------|---------------------|----|--------|
| FR-R19-02 | Read-only report view | Blocked on R12 reporting endpoints | AC-R19-02 | L |
| FR-R19-05 | Read-only viewer — share-link viewer exists; portal scope not wired | Role-scoped portal shell | AC-R19-05 | S |
| FR-R19-09 | Access audit — shared `/logs` exists; role-scoped audit view GATED | Role-scoped audit view | AC-R19-09 | S |
| FR-R19-03 | Order awareness | Order status view not built (R15/R04 dependency) | AC-R19-03 | M |
| FR-R19-06 | No write access | Scope enforcement for this role not built | AC-R19-06 | M |

### Missing (Not Started)

| FR/NFR ID | Summary | Reason | AC | Effort |
|-----------|---------|--------|----|--------|
| FR-R19-01 | Scoped patient lookup | Care-team scope model not defined | AC-R19-01 | M |
| FR-R19-04 | Results notifications | Report-finalize event needed (R12) | AC-R19-04 | M |
| FR-R19-07 | Mobile portal | New portal shell | AC-R19-07 | M |
| FR-R19-08 | PHI minimum necessary | Scope model dependency | AC-R19-08 | M |
| FR-R19-10 | Follow-up request | Request primitive not built | AC-R19-10 | S |

## Effort Estimation Key

| Size | Days | Criteria |
|------|------|----------|
| S (Small) | 1–3 | Single component; no cross-team dependency |
| M (Medium) | 4–10 | Multi-step feature; backend + frontend coordination |
| L (Large) | 11+ | New infrastructure or integration contract |

## Dependency-Ordered Implementation Plan

### Phase 1: Foundation (done)
- Read-only viewer mode + audit infrastructure exist.

### Phase 2: Unblock GATED requirements (next priority)
1. **Care-team scope model** — required for FR-R19-01/08 / AC-R19-01/08
   - Owner: Backend; Blocks: AC-R19-01, AC-R19-08; Effort: M
2. **Write-access enforcement** — required for FR-R19-06 / AC-R19-06
   - Owner: Backend; Blocks: AC-R19-06; Effort: M

### Phase 3: Portal and delivery
3. **Mobile portal shell** — FR-R19-07; M
4. **Report view (with R12)** — FR-R19-02; L
5. **Notifications** — FR-R19-04; M
6. **Follow-up request** — FR-R19-10; S

## Blocking Dependencies

| Blocking Dependency | Blocks | AC | Impact |
|---------------------|--------|----|--------|
| Care-team scope model | FR-R19-01, 08 | AC-R19-01, 08 | Unscoped access risk |
| R12 reporting endpoints | FR-R19-02 | AC-R19-02 | No report view |
| Report-finalize event | FR-R19-04 | AC-R19-04 | No notifications |
| Write-enforcement | FR-R19-06 | AC-R19-06 | Role could mutate data |

## Next Steps (highest priority)

1. **Care-team scope model** — unblocks AC-R19-01/08; M effort
2. **Mobile portal shell** — unblocks AC-R19-07; M effort
3. **Coordinate report view with R12** — unblocks AC-R19-02; L effort
4. Update this roadmap each sprint as FR/NFR status changes.
