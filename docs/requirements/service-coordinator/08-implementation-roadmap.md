# Implementation Roadmap — Radiology & Service Coordinator (R04)

**Role ID**: R04
**Generated**: 2026-08-02 (rev. 2026-08-03)
**Version**: 1.2.0

---

## Dependency Graph

```
FR-R04-01 (Schedule Board) — IMPLEMENTED (frontend over worklist API)
├── FR-R04-03 (Priority Triage) — depends on board rendering
├── FR-R04-06 (Worklist) — IMPLEMENTED (shares board data model)
├── FR-R04-08 (Conflict Detection) — depends on board drag/drop
└── FR-R04-10 (Calendar View) — PARTIAL (worklist calendar toggle)

FR-R04-02 (Exam Assignment)
├── FR-R04-07 (Bulk Reassign) — extends single assignment
├── FR-R04-08 (Conflict Detection) — validates assignments
└── FR-R04-03 (Priority Triage) — assignment respects priority

FR-R04-04 (Utilization Dashboard)
└── FR-R04-05 (Staffing Roster) — shares utilization data

FR-R04-09 (Handoff Report) — depends on all data models
```

---

## Implemented (Passing ACs)

| FR/NFR ID | Summary | AC Coverage | Effort |
|-----------|---------|-------------|--------|
| FR-R04-01 | **Schedule board** — `ScheduleBoard.tsx` at `/schedule-board` renders modality × 30-min slots (08:00–18:00, CT/MRI/PET/DX/MG/US/FL), statuses scheduled/performed/cancelled, entry drawer, prev/next day nav; reads `GET /worklist?date_from&date_to` (per_page 500); gated by `WORKLIST_READ`. Drag-and-drop rescheduling NOT implemented (no backend). | AC-R04-01-01..05 | M |
| FR-R04-06 | **Worklist management** — `/worklist` CRUD, search, date-range + station filters, batch mark-performed/cancel, pagination (`Worklist.tsx`, `CreateEntry.tsx`) | AC-R04-06-01..05 | S |
| FR-R04-10 | **Calendar view (partial)** — table/calendar toggle in `Worklist.tsx` with `CalendarView.tsx` (day grouping, status color-coding); week/month toggle + day drill-down GATED | AC-R04-10-01..04 | S |

## Missing (Not Started — GATED)

| FR/NFR ID | Summary | Blocking Dependency | AC | Effort |
|-----------|---------|---------------------|----|--------|
| FR-R04-02 | **Exam Assignment** (assign to technologist, WebSocket push ≤5s) | No `/schedule/assign` endpoint; no LISTEN/NOTIFY push to R06/R07 worklists | AC-R04-02-01..04 | M |
| FR-R04-03 | **Stat/Priority Triage** (auto-sort, auto-promotion at threshold) | No priority sort/auto-promotion on board | AC-R04-03-01..03 | M |
| FR-R04-04 | **Resource Utilization Dashboard** (capacity bar/line charts) | No utilization endpoints | AC-R04-04-01..05 | L |
| FR-R04-05 | **Staffing Roster Management** (shift assignment) | No roster endpoints; no `shift_assignments` table | AC-R04-05-01..04 | M |
| FR-R04-07 | **Exam Override & Reassignment** (bulk) | No bulk-reassign endpoint | AC-R04-07-01..04 | M |
| FR-R04-08 | **Schedule Conflict Detection** (real-time) | No conflict detection algorithm/endpoint | AC-R04-08-01..04 | L |
| FR-R04-09 | **Shift Handoff Report** (PDF/clipboard) | No report generation endpoint | AC-R04-09-01..04 | M |
| NFR-R04-02, 03, 04, 09 | Assignment latency / worklist staleness / conflict latency / concurrency | Blocked on FR-R04-02..08 above | — | L |

---

## Implementation Phases

### Phase 1: Core Board & Scheduling (MVP)
**Status**: Partial — board (FR-R04-01), worklist (FR-R04-06) and calendar toggle
(FR-R04-10 partial) are done. FR-R04-03 (priority triage) remains GATED.
**Dependencies**: None

| Artifact | What's Lacking | What's Done |
|----------|---------------|-------------|
| 01 User Requirements | FR-R04-03 | FR-R04-01, FR-R04-06, FR-R04-10 (partial) |
| 02 Workflow Maps | W1, W3, W5 | — |
| 03 User Stories | US-R04-03 | US-R04-01, US-R04-06, US-R04-10 |
| 04 UI/UX | S-R04-04 (priority triage) | S-R04-01 (ScheduleBoard), S-R04-03, S-R04-08 |
| 05 Metrics | M-R04-03 | M-R04-01, M-R04-06 |
| 06 ACs | AC-R04-03 | AC-R04-01, AC-R04-06, AC-R04-10 |
| 07 Traceability | FR-R04-03 mapping | FR-R04-01/06/10 mappings |
| 08 Roadmap | This document | ✅ |

**Key APIs still needed**:
1. `GET /api/v2/schedule/board` — fetch schedule board data (optional; board currently reads worklist API)
2. `POST /api/v2/schedule/exam` — schedule new exam
3. `POST /api/v2/schedule/move` — move exam to different slot (drag-and-drop persistence)
4. `PUT /api/v2/schedule/reorder` — reorder by priority (triage)

**Frontend components still needed**:
1. `ExamBlock` drag-and-drop (`@dnd-kit/core` or `react-dnd`)
2. `ConflictBadge` — inline conflict indicator
3. Priority auto-promotion logic (FR-R04-03)

**Estimated effort**: Medium (2 sprints — remainder of Phase 1)

---

### Phase 2: Assignment & Conflict Detection
**Status**: Missing — depends on Phase 1 remainder
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
| 06 ACs | AC-R04-04, AC-R04-09, AC-R04-10 (week/month) | — |
| 07 Traceability | FR-R04-04, FR-R04-09 mappings | — |

**Key APIs needed**:
1. `GET /api/v2/schedule/utilization` — utilization data
2. `POST /api/v2/schedule/handoff-report` — generate handoff report

**Frontend components needed**:
1. `UtilizationDashboard` — new dashboard with charts
2. `HandoffReportModal` — new report generation modal
3. Calendar week/month views + drill-down (extend existing `CalendarView`)
4. `Chart` components using existing Recharts dependency

**Estimated effort**: Medium (2 sprints)

---

## Status Summary

| Artifact | Status | Phase |
|----------|--------|-------|
| 01 User Requirements | ✅ Complete | — |
| 02 Workflow Maps | ✅ Complete | — |
| 03 User Stories | ✅ Complete | — |
| 04 UI/UX Requirements | ✅ Complete (routes updated 2026-08-03) | — |
| 05 Metrics & SLAs | ✅ Complete | — |
| 06 Acceptance Criteria | ✅ Complete | — |
| 07 Traceability Matrix | ✅ Complete (statuses updated 2026-08-03) | — |
| 08 Implementation Roadmap | ✅ Complete (rev. 2026-08-03) | — |

## Blocking Dependencies

| Blocking Dependency | Blocks | AC | Impact |
|---------------------|--------|----|--------|
| No `/schedule/*` backend endpoints (assignment/move/bulk-reassign/roster/utilization/handoff) | FR-R04-02..05, FR-R04-07..09 | AC-R04-02..05, 07..09 | Assignment/staffing/utilization features cannot ship without a scheduling backend; board (FR-R04-01) is frontend-over-worklist and ships today |

## Next Steps

1. Raise scheduling backend with backend team — assign/move/bulk-reassign/roster/utilization/handoff endpoints; unblocks FR-R04-02..05, 07..09
2. Delegate API contract design to `frontend-to-backend-requirements` skill
3. Add drag-and-drop rescheduling (FR-R04-01 gap) once `POST /schedule/move` exists
4. Prioritize FR-R04-03 (priority triage) as the next frontend-only slice
5. Schedule stakeholder review with R04 service coordinator