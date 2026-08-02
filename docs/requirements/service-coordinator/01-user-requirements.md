# User Requirements — Radiology & Service Coordinator (R04)

**Version**: 1.0.0 (v3.0 scope)
**Status**: Draft
**Date**: 2026-08-02

---

## Functional Requirements

| ID | Requirement | Priority | Notes |
|----|-------------|----------|-------|
| FR-R04-01 | **Modality Scheduling Board**: Display a drag-and-drop schedule board showing all modalities (CT, MRI, PET, DX, MG, US, FL) with time slots (30-min intervals, 8:00–18:00). Each slot shows: patient name (initials), modality icon, protocol name, priority badge (STAT/urgent/routine), and assigned technologist. Drag to reschedule; click to open exam detail. | Must | New `ScheduleBoard` component; extends `KanbanBoard` with modality columns |
| FR-R04-02 | **Exam Assignment**: Assign exams from the scheduling board to technologists (R06/R07) via drag-and-drop or dropdown. Assignment triggers `POST /api/v2/schedule/assign` with `{exam_id, technologist_id, priority}`. Assigned technologist receives in-app notification and exam appears in their worklist within ≤5s. | Must | New assignment API; WebSocket push to technologist worklist |
| FR-R04-03 | **Stat/Priority Triage**: Reorder the schedule board by priority (STAT > Urgent > Routine) with visual indicators (STAT rows have red left border 4px solid #EF4444, urgent rows have yellow left border 4px solid #F59E0B, routine rows have default gray left border). Auto-promote routine exams to urgent when STAT backlog exceeds 3 pending exams. | Must | Priority-based sorting algorithm; auto-promotion threshold configurable |
| FR-R04-04 | **Resource Utilization Dashboard**: Display per-modality utilization metrics: scheduled exams vs. capacity (%), average exam duration, idle time %, overtime hours. Filter by date range, modality, and technologist. Visual: bar chart for capacity, line chart for utilization trend. | Must | New `UtilizationDashboard` component; charts use existing design tokens |
| FR-R04-05 | **Staffing Roster Management**: View and manage the technologist roster per shift. Display: name, role (R06/R07), assigned modalities, current status (available/busy/off), scheduled hours vs. actual hours. Allow drag-and-drop shift assignment; color-code by status. | Must | New `StaffingRoster` component; extends `Table` with status badges |
| FR-R04-06 | **Worklist Management**: View and manage the department worklist. Filter by modality, priority, status (scheduled/in-progress/completed/cancelled), technologist, date range. Bulk actions: reassign, cancel, mark complete. Pagination: 25 exams/page with virtualization. | Must | Extends existing worklist with department-wide scope; new bulk action API |
| FR-R04-07 | **Exam Override & Reassignment**: When a technologist calls in sick or a modality goes down, allow the coordinator to reassign all pending exams from that technologist/modality to others in a single operation. Confirmation modal lists affected exams and target technologist before execution. | Must | Bulk reassignment API; audit log entry for each reassignment |
| FR-R04-08 | **Schedule Conflict Detection**: When assigning an exam or dragging to a time slot, detect and warn about conflicts: overlapping exams for the same technologist, same modality double-booked, or exam exceeding modality availability window. Display conflicts as red inline badges with tooltip listing conflicting exams. | Must | Conflict detection algorithm; real-time validation on drag/drop and assignment |
| FR-R04-09 | **Shift Handoff Report**: Generate a shift handoff report at shift end (configurable time, default 15:00 and 23:00). Report includes: pending exams, STAT exams not yet started, exams in progress with estimated completion time, and any conflicts or overrides applied. Export as PDF or copy to clipboard. | Should | PDF generation via backend; clipboard copy via frontend |
| FR-R04-10 | **Modality Calendar View**: Switch between schedule board view and calendar view (day/week/month). Calendar view shows exam blocks color-coded by priority; click to expand exam details. Week view shows all modalities in parallel rows. | Should | New `CalendarView` component; toggle between board and calendar |

## Non-Functional Requirements

| ID | Requirement | Target | Measurement |
|----|-------------|--------|-------------|
| NFR-R04-01 | Schedule board load time (LCP) | ≤ 2.0s | Lighthouse CI, RUM |
| NFR-R04-02 | Exam assignment latency (API) | ≤ 500ms | Backend timing |
| NFR-R04-03 | Worklist refresh staleness (new assignments appear) | ≤ 5s | WebSocket latency + DB trigger |
| NFR-R04-04 | Conflict detection latency (real-time) | ≤ 200ms after drag/drop | Frontend timing |
| NFR-R04-05 | Schedule board virtualization | Smooth scroll at 60fps with 500+ exams | react-window performance |
| NFR-R04-06 | WCAG 2.2 AA compliance | 100% (forms keyboard-intensive) | axe-core CI + manual |
| NFR-R04-07 | Drag-and-drop touch support | Touch drag ≥ 44px threshold; tap to select | Manual + E2E |
| NFR-R04-08 | Token compliance | 100% (no one-off colors) | Stylelint custom rule + manual |
| NFR-R04-09 | Concurrent coordinators | ≥ 5 simultaneous coordinators editing the same schedule | k6 WebSocket scenario |
| NFR-R04-10 | Schedule board responsive | Desktop (≥1024px): full board; Tablet (768–1023px): condensed columns; Mobile (<768px): list view | Manual + E2E |

## Codebase Status (verified 2026-08-03)

**Implemented**: worklist CRUD, calendar view, batch mark-performed/cancel, search,
date-range + station filters (`/worklist*`). **GATED**: FR-R04 schedule board, exam
assignment, stat/priority triage automation, resource utilization, staffing
rosters, shift handoff report — no scheduling-board endpoints or routes exist;
flagged to backend. See artifacts 04/07/08.

## Assumptions & Constraints

| # | Assumption / Constraint | Impact |
|---|-------------------------|--------|
| A1 | PHI: Schedule board shows patient initials only (not full name); full name accessible via exam detail modal per HIPAA minimum necessary | FR-R04-01, FR-R04-06 |
| A2 | 6 new API endpoints required (flagged for `frontend-to-backend-requirements`) | FR-R04-02, FR-R04-07, FR-R04-09 |
| A3 | WebSocket push to technologist worklists requires backend LISTEN/NOTIFY integration (R06/R07 worklist subscription) | FR-R04-02, NFR-R04-03 |
| A4 | Drag-and-drop on schedule board requires `react-dnd` or `@dnd-kit/core`; touch devices use long-press to initiate drag | FR-R04-01, NFR-R04-07 |
| A5 | Calendar view uses `react-big-calendar` or equivalent; day/week/month views share the same underlying data model | FR-R04-10 |
| A6 | Shift handoff PDF generation requires a backend PDF service (e.g., `puppeteer` or `weasyprint`); frontend triggers via `POST /api/v2/schedule/handoff-report` | FR-R04-09 |
| A7 | Utilization dashboard charts use existing `Recharts` dependency (already in frontend); no new chart library needed | FR-R04-04 |
| A8 | Resource utilization data is computed from exam start/end timestamps in the `exam_sessions` table; no separate tracking needed | FR-R04-04 |
| A9 | Staffing roster data comes from the existing `users` table filtered by role (R06/R07) and shift assignment; shift assignments stored in a new `shift_assignments` table | FR-R04-05 |
| A10 | Auto-promotion threshold (STAT backlog > 3) is configurable per tenant via `settings.scheduler.stat_backlog_threshold` | FR-R04-03 |