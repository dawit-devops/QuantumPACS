# Implementation Roadmap — Radiology & Service Coordinator (R04)

**Role ID**: R04
**Generated**: 2026-08-02
**Version**: 1.0.0

---

## Dependency Graph

```
FR-R04-01 (Schedule Board)
├── FR-R04-03 (Priority Triage) — depends on board rendering
├── FR-R04-06 (Worklist) — shares board data model
├── FR-R04-08 (Conflict Detection) — depends on board drag/drop
└── FR-R04-10 (Calendar View) — alternative view of same data

FR-R04-02 (Exam Assignment)
├── FR-R04-07 (Bulk Reassign) — extends single assignment
├── FR-R04-08 (Conflict Detection) — validates assignments
└── FR-R04-03 (Priority Triage) — assignment respects priority

FR-R04-04 (Utilization Dashboard)
└── FR-R04-05 (Staffing Roster) — shares utilization data

FR-R04-09 (Handoff Report) — depends on all data models
```

---

## Implementation Phases

### Phase 1: Core Board & Scheduling (MVP)
**Status**: Missing — no implementation started
**Dependencies**: None

| Artifact | What's Lacking | What's Done |
|----------|---------------|-------------|
| 01 User Requirements | FR-R04-01, FR-R04-03, FR-R04-06, FR-R04-08, FR-R04-10 | — |
| 02 Workflow Maps | W1, W3, W5 | — |
| 03 User Stories | US-R04-01, US-R04-03, US-R04-06 | — |
| 04 UI/UX | S-R04-01, S-R04-04 | — |
| 05 Metrics | M-R04-01, M-R04-03, M-R04-04, M-R04-06 | — |
| 06 ACs | AC-R04-01, AC-R04-03, AC-R04-06, AC-R04-08, AC-R04-10 | — |
| 07 Traceability | All FR→AC mappings | — |
| 08 Roadmap | This document | ✅ |

**Key APIs needed**:
1. `GET /api/v2/schedule/board` — fetch schedule board data
2. `POST /api/v2/schedule/exam` — schedule new exam
3. `POST /api/v2/schedule/move` — move exam to different slot
4. `GET /api/v2/schedule/worklist` — department worklist
5. `PUT /api/v2/schedule/reorder` — reorder by priority

**Frontend components needed**:
1. `ScheduleBoard` — new KanbanBoard variant with modality columns
2. `ExamBlock` — new draggable block component
3. `ConflictBadge` — new inline conflict indicator
4. `ScheduleBoard` extends existing `KanbanBoard`

**Estimated effort**: Large (3-4 sprints)

---

### Phase 2: Assignment & Conflict Detection
**Status**: Missing — depends on Phase 1
**Dependencies**: Phase 1 complete

| Artifact | What's Lacking | What's Done |
|----------|---------------|-------------|
| 01 User Requirements | FR-R04-02, FR-R04-07 | — |
| 02 Workflow Maps | W2, W4 | — |
| 03 User Stories | US-R04-02, US-R04-05, US-R04-07 | — |
| 04 UI/UX | S-R04-04 (ExamDetailPanel), S-R04-05, S-R04-06 | — |
| 05 Metrics | M-R04-02, M-R04-07, M-R04-08, M-R04-10 | — |
| 06 ACs | AC-R04-02, AC-R04-05, AC-R04-07, AC-R04-08 | — |
| 07 Traceability | FR-R04-02, FR-R04-07 mappings | — |

**Key APIs needed**:
1. `POST /api/v2/schedule/assign` — assign exam to technologist
2. `POST /api/v2/schedule/bulk-reassign` — bulk reassignment
3. `GET /api/v2/schedule/assign-options` — available technologists
4. `PUT /api/v2/schedule/roster/{user_id}` — shift assignment
5. `GET /api/v2/schedule/roster` — staffing roster data

**Frontend components needed**:
1. `AssignDropdown` — new technologist selector with load indicator
2. `OverrideModal` — new bulk reassignment confirmation
3. `StaffingRoster` — new roster table component
4. `ConflictWarning` — new conflict modal

**Estimated effort**: Medium (2 sprints)

---

### Phase 3: Dashboard, Reports & Calendar
**Status**: Missing — depends on Phase 2
**Dependencies**: Phase 2 complete

| Artifact | What's Lacking | What's Done |
|----------|---------------|-------------|
| 01 User Requirements | FR-R04-04, FR-R04-09 | — |
| 02 Workflow Maps | W5 | — |
| 03 User Stories | US-R04-04, US-R04-09, US-R04-10 | — |
| 04 UI/UX | S-R04-02, S-R04-03, S-R04-05 | — |
| 05 Metrics | M-R04-05, M-R04-09 | — |
| 06 ACs | AC-R04-04, AC-R04-09, AC-R04-10 | — |
| 07 Traceability | FR-R04-04, FR-R04-09, FR-R04-10 mappings | — |

**Key APIs needed**:
1. `GET /api/v2/schedule/utilization` — utilization data
2. `POST /api/v2/schedule/handoff-report` — generate handoff report
3. `GET /api/v2/schedule/board?view=calendar` — calendar view data

**Frontend components needed**:
1. `UtilizationDashboard` — new dashboard with charts
2. `HandoffReportModal` — new report generation modal
3. `CalendarView` — new calendar component (toggle from board)
4. `Chart` components using existing Recharts dependency

**Estimated effort**: Medium (2 sprints)

---

## Status Summary

| Artifact | Status | Phase |
|----------|--------|-------|
| 01 User Requirements | ✅ Complete | — |
| 02 Workflow Maps | ✅ Complete | — |
| 03 User Stories | ✅ Complete | — |
| 04 UI/UX Requirements | ✅ Complete | — |
| 05 Metrics & SLAs | ✅ Complete | — |
| 06 Acceptance Criteria | ✅ Complete | — |
| 07 Traceability Matrix | ✅ Complete | — |
| 08 Implementation Roadmap | ✅ Complete | — |

## Blocking Dependencies

| Blocking Dependency | Blocks | AC | Impact |
|---------------------|--------|----|--------|
| Backend scheduling-board endpoints (no `/schedule*` routes exist) | FR-R04-01..05, FR-R04-07..10 | AC-R04 scheduling ACs | Scheduling/staffing features cannot ship without a scheduling backend |
| Worklist API (already implemented) | FR-R04-06 | AC-R04 worklist ACs | None — worklist slice is shippable today |

## Next Steps

1. Delegate API contract design to `frontend-to-backend-requirements` skill
2. Delegate RESTful resource design to `rest-api-design` skill
3. Prioritize Phase 1 user stories (US-R04-01, 02, 03, 06, 08) for MVP
4. Schedule stakeholder review with R04 service coordinator
5. Conduct usability testing with 2-3 service coordinators before full implementation