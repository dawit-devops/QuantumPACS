# Backend Requirements: R04 Radiology & Service Coordinator

## Context

The Coordinator is the department scheduler: modality scheduling, exam
assignment to technologists, STAT triage, resource utilization, staffing rosters,
and worklist management. Works from a central desk with a schedule board and
worklist side-by-side. Requires **real-time updates** (WebSocket) when exams are
assigned or completed, because technologists (R06/R07) and the reading queue
depend on the same data. Patient initials only on the schedule board (HIPAA
minimum necessary); full PHI only in the exam detail modal.

**Screens (new)**: Modality Scheduling Board, Exam Assignment, Stat/Priority
Triage, Resource Utilization Dashboard, Staffing Roster, Department Worklist,
Exam Override/Reassign, Schedule Conflict Detection, Shift Handoff Report,
Modality Calendar View.

**Personas**: P2/P4 (scheduling). **Access tier**: department scheduler
(read/write scheduling, no clinical reading).

## Screens/Components

### Modality Scheduling Board

**Purpose**: Visual schedule with drag-and-drop exam blocks.

**Data I need to display**:
- Exam blocks per modality column and 30-minute time slot: patient initials,
  modality icon, priority badge (STAT/urgent/routine), assigned technologist,
  conflict indicator.
- The full schedule for the selected day/range, plus modality + technologist
  capacity.

**Actions**: drag an exam to a new slot, drag to assign/reassign a technologist,
open exam detail modal, bulk reassign with confirmation.

**States to handle**: loading, empty schedule, populated, conflict (red border),
optimistic move with rollback on failure.

**Business rules affecting UI**:
- Priority color-coding is fixed by priority level.
- Moves/assignments must propagate to technologists' worklists in ≤5 s
  (WebSocket).
- Real-time conflict detection when two exams collide for a modality or
  technologist.

### Stat/Priority Triage

**Purpose**: Keep STAT exams visible and promoted.

**Data I need**: sorted worklist by priority, auto-promotion rules state, STAT
badge rendering.

**Actions**: promote/demote, view exam detail, assign.

### Resource Utilization Dashboard

**Purpose**: Capacity bar chart + utilization trend.

**Data I need**: scheduled vs. capacity per modality/technologist over a date
range, utilization percentage trend.

**Actions**: date-range filter.

### Staffing Roster Management

**Purpose**: Manage shift assignments for technologists.

**Data I need**: roster of technologists with their shifts (date, type,
start/end, status), overflow warnings.

**Actions**: assign/swap/cancel shifts, update roster entry.

**States to handle**: loading, empty roster, conflict/overflow warning.

### Department Worklist & Bulk Operations

**Purpose**: Filterable, paginated department-wide worklist.

**Data I need**: all scheduled/performed/cancelled exams for the department with
filters by status, modality, priority, date.

**Actions**: filter, bulk reassign, bulk cancel, export.

### Shift Handoff Report

**Purpose**: Structured handoff at shift change.

**Data I need**: current state of in-flight exams, assignments, and pending
handoffs compiled into a report.

**Actions**: generate PDF, copy to clipboard.

## Uncertainties
- [ ] The schedule board needs exam data in slot granularity — does the backend
  return pre-aggregated blocks, or raw entries the UI lays out?
- [ ] Conflict detection: is it computed server-side (authoritative) or purely
  client-side on the loaded board?
- [ ] Roster source: HR integration is deferred (v3.1) — is the roster managed
  entirely in-system for v3?
- [ ] Bulk reassign atomicity: one request for N exams, or per-exam?
- [ ] WebSocket event types for board updates (exam created/moved/assigned) need
  a contract.
- [ ] Handoff report is currently PDF + clipboard — confirm export format and
  size limits.

## Questions for Backend
- What real-time events should the board subscribe to, and what payload does each
  carry?
- Should schedule-board data be fetched per-day/per-range, and is there a
  server-side capacity aggregate?
- Who can de-assign an exam that a technologist has already started?

## Discussion Log

_(pending backend review)_
