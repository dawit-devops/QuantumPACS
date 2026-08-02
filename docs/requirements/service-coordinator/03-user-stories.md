# User Stories — Radiology & Service Coordinator (R04)

## US-R04-01: Schedule Exam on Modality Board
**Story**: As a R04 coordinator, I want to schedule an exam on the modality schedule board so that the exam is assigned a time slot and visible to technologists.
**Priority**: Must

### Acceptance Criteria
- **Given** I am on the schedule board view, **when** I click "Schedule Exam" button, **then** I observe a modal with modality dropdown, date picker, time slot selector, patient search (autocomplete), and protocol selector.
- **Given** I have filled the scheduling form, **when** I click "Schedule", **then** I observe the exam block appears on the board at the selected slot, a green toast "Exam scheduled" appears, and the exam appears in the department worklist within 5s.
- **Given** I select a time slot that conflicts with an existing exam for the same technologist, **when** I click "Schedule", **then** I observe a conflict warning modal listing the conflicting exam with details and "Cancel" / "Override" buttons.
- **Given** I am on a tablet (768px viewport), **when** I tap the schedule board, **then** I observe touch-friendly tap targets (≥44px) and the modal is scrollable.
- **Given** the schedule board has 200+ exams, **when** I scroll, **then** I observe smooth scrolling at 60fps with virtualization (no lag).

### Dependencies
- FR-R04-01, NFR-R04-01, NFR-R04-05, NFR-R04-07
- API: `POST /api/v2/schedule/exam` (new endpoint)

---

## US-R04-02: Assign Exam to Technologist
**Story**: As a R04 coordinator, I want to assign a scheduled exam to a specific technologist so that the technologist receives the exam in their worklist.
**Priority**: Must

### Acceptance Criteria
- **Given** I am on the schedule board, **when** I click an exam block, **then** I observe an "Assign" button in the exam detail panel.
- **Given** I click "Assign", **when** the assign dropdown opens, **then** I observe a list of available technologists (R06/R07, status=available) with their current load indicator and modality specialization tags.
- **Given** I select a technologist and click "Assign", **when** the assignment completes, **then** I observe the exam block changes to show the technologist name, a green checkmark badge, and the exam appears in the technologist's worklist within 5s (WebSocket push).
- **Given** I assign an exam to a technologist who is already busy, **when** the assignment is processed, **then** I observe a warning toast "Technologist has overlapping exam — confirm assignment?" with "Confirm" / "Cancel" buttons.
- **Given** I am using keyboard-only navigation, **when** I Tab to the Assign button and press Enter, **then** I observe the dropdown opens and I can navigate technologist options with Arrow keys and select with Enter.

### Dependencies
- FR-R04-02, NFR-R04-02, NFR-R04-03
- API: `POST /api/v2/schedule/assign` (new endpoint)

---

## US-R04-03: Triage STAT Exams by Priority
**Story**: As a R04 coordinator, I want STAT exams to automatically appear at the top of the schedule board so that they are prioritized over routine exams.
**Priority**: Must

### Acceptance Criteria
- **Given** a STAT exam is scheduled or arrives, **when** the board renders, **then** I observe STAT exams appear at the top of their modality column with a red left border (4px solid #EF4444) and red background fade (rgba(239, 68, 68, 0.1)).
- **Given** the STAT backlog exceeds 3 pending exams, **when** a new routine exam is scheduled, **then** I observe the routine exam is auto-promoted to urgent with a yellow left border (4px solid #F59E0B) and a banner "Auto-promoted to urgent due to STAT backlog".
- **Given** I drag a STAT exam to a different slot, **when** I drop it, **then** I observe the board reorders STAT exams to the top automatically.
- **Given** I click a STAT exam block, **when** the detail panel opens, **then** I observe the priority badge shows "STAT" in red with a pulsing animation.

### Dependencies
- FR-R04-03
- API: None (client-side sorting + server-side priority field)

---

## US-R04-04: View Resource Utilization Dashboard
**Story**: As a R04 coordinator, I want to see a utilization dashboard so that I can identify underutilized or overutilized modalities and adjust scheduling.
**Priority**: Must

### Acceptance Criteria
- **Given** I navigate to the Utilization tab, **when** the dashboard loads, **then** I observe a bar chart showing per-modality capacity (scheduled vs. max) and a line chart showing utilization trend over the selected date range.
- **Given** I filter by a specific modality and date range, **when** I apply the filter, **then** I observe the charts update within ≤300ms with the filtered data.
- **Given** a modality is at ≥90% capacity, **when** the dashboard renders, **then** I observe that modality's bar is colored red (#EF4444); at 70-89% it is yellow (#F59E0B); below 70% it is green (#10B981).
- **Given** I hover over a data point on the utilization line chart, **when** the tooltip appears, **then** I observe the exact utilization percentage and exam count for that time period.
- **Given** I am on a desktop (≥1024px), **when** I view the dashboard, **then** I observe both charts side-by-side; on tablet (768-1023px), they stack vertically.

### Dependencies
- FR-R04-04, NFR-R04-01
- API: `GET /api/v2/schedule/utilization?modality=&date_from=&date_to=`

---

## US-R04-05: Manage Staffing Roster
**Story**: As a R04 coordinator, I want to manage the technologist staffing roster per shift so that I can ensure adequate coverage for all scheduled exams.
**Priority**: Must

### Acceptance Criteria
- **Given** I navigate to the Staffing tab, **when** the roster loads, **then** I observe a table with all R06/R07 technologists, their assigned shift (morning/evening/night), current status (available/busy/off), and scheduled vs. actual hours.
- **Given** I drag a technologist row to a different shift, **when** I drop, **then** I observe the shift assignment updates, the status badge changes, and the roster reorders.
- **Given** a technologist is assigned to a shift that exceeds 8 hours, **when** I drop them, **then** I observe a warning "Shift exceeds 8h limit" inline and the row is highlighted yellow.
- **Given** I click a technologist row, **when** the detail panel opens, **then** I observe their scheduled exams for the week, overtime hours, and availability status.
- **Given** I am on a mobile viewport (<768px), **when** I view the roster, **then** I observe a list view (not table) with each technologist as a card.

### Dependencies
- FR-R04-05
- API: `GET /api/v2/schedule/roster`, `PUT /api/v2/schedule/roster/{user_id}`

---

## US-R04-06: Manage Department Worklist
**Story**: As a R04 coordinator, I want to view and manage the department-wide worklist so that I can track all exams across technologists and modalities.
**Priority**: Must

### Acceptance Criteria
- **Given** I navigate to the Worklist tab, **when** the worklist loads, **then** I observe a filterable, paginated table of all department exams with columns: Accession, Patient (initials), Modality, Protocol, Priority, Technologist, Status, Scheduled Time.
- **Given** I apply filters (modality, priority, status, technologist, date range), **when** I click "Apply", **then** I observe the table updates with filtered results within ≤1s.
- **Given** I select multiple exam rows via checkboxes, **when** I click "Bulk Actions" toolbar, **then** I observe a dropdown with Reassign, Cancel, and Mark Complete options.
- **Given** I select "Reassign" from bulk actions, **when** I choose a target technologist and confirm, **then** I observe all selected exams are reassigned and the table refreshes.
- **Given** the worklist has 100+ exams, **when** I scroll, **then** I observe virtualization with smooth scrolling and a loading indicator at the scroll position.

### Dependencies
- FR-R04-06
- API: `GET /api/v2/schedule/worklist`, `PUT /api/v2/schedule/bulk-reassign`, `PUT /api/v2/schedule/bulk-cancel`

---

## US-R04-07: Reassign Exams During Override
**Story**: As a R04 coordinator, I want to reassign all pending exams from a technologist or modality in a single operation when they call in sick or a modality goes down.
**Priority**: Must

### Acceptance Criteria
- **Given** I click "Override" on the schedule board, **when** the override modal opens, **then** I observe options: "Reassign all from technologist" or "Reassign all from modality", with a search/select for the source and target.
- **Given** I select a source technologist who has 5 pending exams, **when** I choose a target technologist and click "Reassign", **then** I observe a confirmation modal listing all 5 affected exams with their priority and scheduled time, and "Confirm Reassign" / "Cancel" buttons.
- **Given** I confirm the reassignment, **when** the operation completes, **then** I observe all 5 exams are reassigned to the target technologist, the board updates, and each reassignment is logged in the audit trail.
- **Given** the target technologist already has overlapping exams, **when** I confirm, **then** I observe a warning listing the conflicts and asking me to resolve them before confirming.
- **Given** the reassignment is complete, **when** I check the audit log, **then** I observe entries for each reassigned exam with timestamp, source tech, target tech, and coordinator ID.

### Dependencies
- FR-R04-07
- API: `POST /api/v2/schedule/bulk-reassign`

---

## US-R04-08: Detect Schedule Conflicts in Real-Time
**Story**: As a R04 coordinator, I want the system to detect and warn me about scheduling conflicts in real-time so that I don't double-book modalities or technologists.
**Priority**: Must

### Acceptance Criteria
- **Given** I drag an exam to a time slot where the same technologist already has an exam, **when** I drop, **then** I observe a red inline badge on the target slot with tooltip "Conflict: Dr. Smith already scheduled for CT-001 at this time" and the exam snaps back to its original position.
- **Given** I drag an exam to a time slot where the same modality is already booked, **when** I drop, **then** I observe a red inline badge on the target slot with tooltip "Conflict: CT-1 already booked at this time" and the exam snaps back.
- **Given** I assign an exam to a technologist who is already assigned to an overlapping exam, **when** I confirm the assignment, **then** I observe a conflict warning modal with the conflicting exam details and "Cancel" / "Override Anyway" buttons.
- **Given** I hover over a conflict badge, **when** the tooltip appears, **then** I observe the conflicting exam details (patient initials, modality, time).
- **Given** there are no conflicts, **when** I schedule/assign an exam, **then** I observe no conflict warnings and the operation completes smoothly.

### Dependencies
- FR-R04-08, NFR-R04-04
- API: Conflict check is client-side with server-side validation on save

---

## US-R04-09: Generate Shift Handoff Report
**Story**: As a R04 coordinator, I want to generate a shift handoff report at shift end so that the incoming coordinator has visibility into pending exams and issues.
**Priority**: Should

### Acceptance Criteria
- **Given** I click "Generate Handoff Report", **when** the report is generated, **then** I observe a preview with: pending exams count, STAT exams not yet started, exams in progress with estimated completion time, and any conflicts/overrides applied.
- **Given** I click "Export as PDF", **when** the PDF generates, **then** I observe a PDF download with the same content formatted for printing (header with shift dates, footer with page numbers).
- **Given** I click "Copy to Clipboard", **when** the copy completes, **then** I observe a green toast "Report copied to clipboard" and the report text is available for pasting.
- **Given** there are no pending exams for the shift, **when** I generate the report, **then** I observe an empty state "No pending exams for this shift" with a "Copy empty report" option.

### Dependencies
- FR-R04-09
- API: `POST /api/v2/schedule/handoff-report`

---

## US-R04-10: Switch Between Board and Calendar View
**Story**: As a R04 coordinator, I want to switch between schedule board view and calendar view so that I can see the schedule at different levels of detail.
**Priority**: Should

### Acceptance Criteria
- **Given** I am on the schedule board view, **when** I click the "Calendar" toggle, **then** I observe the view switches to a calendar with exam blocks color-coded by priority (STAT=red, urgent=yellow, routine=gray).
- **Given** I am in calendar view, **when** I click the "Board" toggle, **then** I observe the view switches back to the schedule board with the same data.
- **Given** I am in calendar week view, **when** I click a day, **then** I observe a drill-down showing all exams for that day in a side panel.
- **Given** I am in calendar month view, **when** I hover over an exam block, **then** I observe a tooltip with patient initials, modality, and protocol name.
- **Given** I switch between board and calendar views, **when** the view changes, **then** I observe the transition is smooth (no full page reload) and the current date filter is preserved.

### Dependencies
- FR-R04-10
- API: Same endpoints as board view; calendar uses `GET /api/v2/schedule/board` with `view=calendar` parameter