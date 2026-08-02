# Implementation Roadmap — Radiology Trainee/Resident (R13)

## Artifact Status Overview

| # | Artifact | File | Status | Notes |
|---|----------|------|--------|-------|
| 01 | User Requirements | `01-user-requirements.md` | done | 10 FRs + 10 NFRs |
| 02 | Workflow Maps | `02-workflow-maps.md` | done | 5 workflows |
| 03 | User Stories | `03-user-stories.md` | done | 10 stories |
| 04 | UI/UX Requirements | `04-ui-ux-requirements.md` | done | Supervised viewer, editor, dashboards |
| 05 | Metrics & SLAs | `05-metrics-slas.md` | done | 10 KPIs |
| 06 | Acceptance Criteria | `06-acceptance-criteria.md` | done | 20 ACs |
| 07 | Traceability Matrix | `07-traceability.md` | done | 20 rows + deps |
| 08 | Implementation Roadmap | `08-implementation-roadmap.md` | done | This file |

## FR/NFR Implementation Status

### Implemented (Passing ACs)

| FR/NFR ID | Summary | AC Coverage | Effort |
|-----------|---------|-------------|--------|
| — | **Shared infrastructure only**: study/patient list + Files browser + viewer (`/`, `/files/:id`) — no resident-specific FR is fully implemented | (viewer ACs) | S |

### Partially Implemented (GATED / Partial)

| FR/NFR ID | Summary | Blocking Dependency | AC | Effort |
|-----------|---------|---------------------|----|--------|
| FR-R13-01 | Supervised worklist | Requires attending-assignment data + WebSocket push | AC-R13-01 | M |
| FR-R13-02 | Supervised viewer | Viewer exists; attending-guidance panel + guidance channel do not | AC-R13-02 | M |
| FR-R13-06 | Exam list — study/patient list infra exists (Files browser); exam-log filters, CSV export, metrics do not | No resident exam-log view/endpoints | AC-R13-06 | S |

### Missing (Not Started)

| FR/NFR ID | Summary | Reason | AC | Effort |
|-----------|---------|--------|----|--------|
| FR-R13-03 | Draft report editor | No reporting endpoints (shared R12 gap) | AC-R13-03 | L |
| FR-R13-04 | Attending review/sign-off | Depends on draft reports | AC-R13-04 | L |
| FR-R13-05 | Teaching file capture | No de-identification service | AC-R13-05 | L |
| FR-R13-07 | Feedback dashboard | No resident metrics aggregates | AC-R13-07 | M |
| FR-R13-08 | On-call consult | No consult/notification routing | AC-R13-08 | M |
| FR-R13-09 | Protocol learning | No education-annotation store | AC-R13-09 | M |
| FR-R13-10 | Case conference export | Depends on teaching files + presentation export | AC-R13-10 | M |

## Effort Estimation Key

| Size | Days | Criteria |
|------|------|----------|
| S (Small) | 1–3 | Single endpoint or UI component; no cross-team dependency |
| M (Medium) | 4–10 | Multi-step feature; requires backend + frontend coordination |
| L (Large) | 11+ | Cross-cutting feature; requires integration contract or new infrastructure |

## Dependency-Ordered Implementation Plan

### Phase 1: Foundation (done)
- Artifacts 01–08 complete; exam-list infrastructure identified as existing.

### Phase 2: Unblock GATED requirements (next priority)
1. **Attending-assignment data + worklist push** — required for FR-R13-01 / AC-R13-01
   - Owner: Backend; Blocks: AC-R13-01; Effort: M
   - Once done, re-run validator gate on AC-R13-01.
2. **Attending-guidance channel** — required for FR-R13-02 / AC-R13-02
   - Owner: Backend; Blocks: AC-R13-02; Effort: M

### Phase 3: Reporting foundation (with R12)
3. **Draft report endpoints** — FR-R13-03; shared with R12 reporting (L)
4. **Attending review/sign-off workflow** — FR-R13-04; L
5. **Teaching file capture + de-identification** — FR-R13-05; L
6. **Feedback dashboard aggregates** — FR-R13-07; M
7. **On-call consult routing** — FR-R13-08; M
8. **Protocol learning store** — FR-R13-09; M
9. **Case conference export** — FR-R13-10; M

## Blocking Dependencies

| Blocking Dependency | Blocks | AC | Impact |
|---------------------|--------|----|--------|
| Reporting endpoints (R12) | FR-R13-03, 04 | AC-R13-03, 04 | No draft/sign-off workflow |
| Resident exam-log view/endpoints | FR-R13-06 | AC-R13-06 | Exam list has no resident-specific filters/export/metrics |
| Attending-assignment data | FR-R13-01 | AC-R13-01 | No supervised worklist |
| De-identification service | FR-R13-05, 10 | AC-R13-05, 10 | Teaching files can't publish |
| Consult routing | FR-R13-08 | AC-R13-08 | On-call guidance unavailable |
| Guidance channel | FR-R13-02 | AC-R13-02 | No attending guidance in viewer |

## Next Steps (highest priority)

1. **Draft report endpoints (with R12)** — unblocks AC-R13-03/04; L effort
2. **Attending-assignment data + worklist push** — unblocks AC-R13-01; M effort
3. **Attending-guidance channel** — unblocks AC-R13-02; M effort
4. Update this roadmap each sprint as FR/NFR status changes.
