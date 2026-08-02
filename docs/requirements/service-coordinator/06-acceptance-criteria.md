# Acceptance Criteria — Radiology & Service Coordinator (R04)

**Role ID**: R04
**Generated**: 2026-08-02
**Version**: 1.0.0

---

## Acceptance Criteria Matrix

This matrix maps all functional and non-functional requirements to verifiable acceptance criteria following the ui-visual-validator skeptical verification gate (Section 6.4 of the skill).

### Verification Method Legend
- **AT**: Automated Test (Playwright E2E, Vitest unit, pytest integration)
- **VE**: Visual Evidence (screenshot, screen recording with measurements)
- **MT**: Manual Test (human verification with documented steps)
- **PM**: Performance Measurement (Lighthouse, k6, APM metrics)
- **AL**: Audit Log (database query, log analysis)

---

## AC-R04-01: Schedule Board Rendering & Exam Scheduling

| AC ID | Links to | Criteria (Given/When/Then) | Verification Method | Validator Gate |
|-------|----------|----------------------------|---------------------|----------------|
| AC-R04-01-01 | FR-R04-01 | **Given** I am on the schedule board view for today's date, **when** the board loads, **then** I observe: (1) modality columns (CT, MRI, PET, DX, MG, US, FL) displayed left to right, (2) time slots from 08:00 to 18:00 in 30-min intervals, (3) empty slots shown as dashed-drop zones, (4) scheduled exams shown as colored blocks with patient initials, modality icon, and priority badge. | VE + AT | Screenshot shows all 7 modality columns; time slots rendered at 30-min intervals; exam blocks contain initials + icon + badge |
| AC-R04-01-02 | FR-R04-01 | **Given** I click "Schedule Exam" button, **when** the scheduling modal opens, **then** I observe: modality dropdown, date picker, time slot selector, patient search (autocomplete with debounce 300ms), protocol dropdown, and "Schedule" primary button + "Cancel" secondary button. | VE + AT | Modal renders with all fields; patient autocomplete returns results within 300ms of typing; all fields have explicit labels |
| AC-R04-01-03 | FR-R04-01 | **Given** I have filled the scheduling form and clicked "Schedule", **when** the API call completes successfully, **then** I observe: (1) the exam block appears at the correct slot on the board, (2) a green toast "Exam scheduled for {patient_initials}" appears, (3) the modal closes, (4) the board scrolls to the new exam if it's off-screen. | AT + VE | API call `POST /api/v2/schedule/exam` succeeds; toast component renders with green background; exam block appears at correct time slot |
| AC-R04-01-04 | FR-R04-01, NFR-R04-01 | **Given** the schedule board is loading, **when** the request is in-flight, **then** I observe skeleton placeholder rows with pulse animation matching the board layout, not a generic spinner. | VE | Screenshot shows skeleton rows with pulse animation; no generic loading spinner |
| AC-R04-01-05 | FR-R04-01 | **Given** I am on a tablet (768px viewport), **when** I view the schedule board, **then** I observe: modality columns are condensed (showing only 3-4 at a time with horizontal scroll), exam blocks are touch-friendly (min 44px height), and the scheduling modal is scrollable if content overflows. | VE + MT | Browser viewport set to 768px; columns condensed; touch targets measured ≥44px |

**Validator Gate Verdict**: AC-R04-01 achieves acceptance criteria **only if** all 7 modality columns render correctly, exam blocks contain all required information (initials, icon, badge), and the scheduling modal has all required fields with proper labels.

---

## AC-R04-02: Exam Assignment & Technologist Notification

| AC ID | Links to | Criteria (Given/When/Then) | Verification Method | Validator Gate |
|-------|----------|----------------------------|---------------------|----------------|
| AC-R04-02-01 | FR-R04-02 | **Given** I click an exam block on the schedule board, **when** the detail panel opens, **then** I observe an "Assign" button in the panel header, a dropdown showing available technologists (R06/R07, status=available) with their current load count and modality tags. | VE + AT | Screenshot shows Assign button and dropdown with technologist names + load indicators |
| AC-R04-02-02 | FR-R04-02 | **Given** I select a technologist from the dropdown and click "Assign", **when** the assignment completes, **then** I observe: (1) the exam block updates to show the technologist name and a green checkmark badge, (2) a green toast "Assigned to {technologist_name}" appears, (3) the technologist's worklist receives the new exam within 5s (WebSocket push verified by network log). | AT + PM | API call `POST /api/v2/schedule/assign` succeeds; WebSocket message received by technologist client; timing ≤5s |
| AC-R04-02-03 | FR-R04-02, NFR-R04-02 | **Given** I select a technologist who already has an overlapping exam, **when** I click "Assign", **then** I observe a warning toast "Technologist has overlapping exam — confirm?" with "Confirm" / "Cancel" buttons. | AT + VE | Toast renders with warning styling; Confirm and Cancel buttons functional |
| AC-R04-02-04 | FR-R04-02 | **Given** I am using keyboard-only navigation, **when** I Tab to the Assign button and press Enter, **then** I observe the dropdown opens, Arrow keys navigate technologist options, and Enter selects the highlighted option. | AT + MT | Playwright keyboard event simulation; dropdown opens on Enter; Arrow key navigation works |

**Validator Gate Verdict**: AC-R04-02 achieves acceptance criteria **only if** the Assign button appears in the detail panel, the dropdown shows available technologists with load indicators, assignment completes within 500ms API latency, and WebSocket push delivers the exam to the technologist worklist within 5s.

---

## AC-R04-03: Stat Priority Triage & Auto-Promotion

| AC ID | Links to | Criteria (Given/When/Then) | Verification Method | Validator Gate |
|-------|----------|----------------------------|---------------------|----------------|
| AC-R04-03-01 | FR-R04-03 | **Given** a STAT exam is scheduled, **when** the board renders, **then** I observe STAT exams appear at the top of their modality column with a red left border (4px solid #EF4444) and red background fade (rgba(239, 68, 68, 0.1)), and a pulsing red dot indicator. | VE + AT | Screenshot shows STAT exam at top of column; red border and background fade applied; pulsing animation verified via CSS |
| AC-R04-03-02 | FR-R04-03 | **Given** the STAT backlog exceeds 3 pending exams, **when** a new routine exam is scheduled, **then** I observe the routine exam is auto-promoted to urgent with a yellow left border (4px solid #F59E0B) and a banner "Auto-promoted to urgent due to STAT backlog" with a dismiss button. | AT + VE | Board reorders after scheduling; banner appears with correct text; dismiss button hides banner |
| AC-R04-03-03 | FR-R04-03 | **Given** I drag a STAT exam to a different slot, **when** I drop it, **then** I observe STAT exams remain at the top of their column after the drop (board reorders automatically). | AT | DOM order verified after drag/drop; STAT rows are first in column |

**Validator Gate Verdict**: AC-R04-03 achieves acceptance criteria **only if** STAT exams are visually distinct (red border + background + pulsing dot), auto-promotion triggers correctly at the threshold, and the board reorders automatically after any scheduling change.

---

## AC-R04-04: Resource Utilization Dashboard

| AC ID | Links to | Criteria (Given/When/Then) | Verification Method | Validator Gate |
|-------|----------|----------------------------|---------------------|----------------|
| AC-R04-04-01 | FR-R04-04 | **Given** I navigate to the Utilization tab, **when** the dashboard loads with default date range (this week), **then** I observe a bar chart showing per-modality capacity (scheduled vs. max) and a line chart showing utilization trend. | VE + AT | Screenshot shows both charts; bar chart has modality labels on x-axis; line chart has date labels on x-axis |
| AC-R04-04-02 | FR-R04-04 | **Given** a modality is at ≥90% capacity, **when** the dashboard renders, **then** I observe that modality's bar is colored red (#EF4444); at 70-89% it is yellow (#F59E0B); below 70% it is green (#10B981). | VE + PM | Contrast measured for all bar colors; color values match specification exactly |
| AC-R04-04-03 | FR-R04-04 | **Given** I hover over a data point on the utilization line chart, **when** the tooltip appears, **then** I observe the exact utilization percentage and exam count for that time period. | AT + VE | Hover triggers tooltip; tooltip contains percentage and count; tooltip positions near cursor |
| AC-R04-04-04 | FR-R04-04, NFR-R04-01 | **Given** I apply a date range filter, **when** I click "Apply", **then** I observe the charts update within ≤300ms with the filtered data and a subtle loading indicator on the charts during update. | PM + AT | Chart update timing measured; loading indicator shown during update |
| AC-R04-04-05 | FR-R04-04 | **Given** I am on a mobile viewport (<768px), **when** I view the dashboard, **then** I observe charts stacked vertically (not side-by-side) with full-width bars. | VE + MT | Browser viewport set to 375px; charts stack vertically; bars are full-width |

**Validator Gate Verdict**: AC-R04-04 achieves acceptance criteria **only if** capacity bars are color-coded correctly (red ≥90%, yellow 70-89%, green <70%), hover tooltips show exact values, and chart updates complete within 300ms.

---

## AC-R04-05: Staffing Roster Management

| AC ID | Links to | Criteria (Given/When/Then) | Verification Method | Validator Gate |
|-------|----------|----------------------------|---------------------|----------------|
| AC-R04-05-01 | FR-R04-05 | **Given** I navigate to the Staffing tab, **when** the roster loads, **then** I observe a table with all R06/R07 technologists, columns: Name, Role, Assigned Shift, Current Status, Scheduled Hours, Actual Hours. Status badges: green (available), blue (busy), gray (off). | VE + AT | Screenshot shows all technologists with correct status badges; table columns match specification |
| AC-R04-05-02 | FR-R04-05 | **Given** I drag a technologist row to a different shift column, **when** I drop, **then** I observe the shift assignment updates, the status badge changes (e.g., available → busy if now scheduled), and the roster reorders. | AT + VE | API call `PUT /api/v2/schedule/roster/{user_id}` succeeds; badge changes; roster reorders |
| AC-R04-05-03 | FR-R04-05 | **Given** I assign a technologist to a shift that exceeds 8 hours, **when** I drop them, **then** I observe a warning "Shift exceeds 8h limit" inline and the row is highlighted yellow (#F59E0B background). | VE + AT | Warning text matches exactly; yellow highlight applied; row is not saved until warning is acknowledged |
| AC-R04-05-04 | FR-R04-05 | **Given** I am on a mobile viewport (<768px), **when** I view the roster, **then** I observe a card list (not table) with each technologist as a card showing name, shift, status badge, and hours summary. | VE + MT | Browser viewport set to 375px; cards render instead of table; all info visible on card |

**Validator Gate Verdict**: AC-R04-05 achieves acceptance criteria **only if** all R06/R07 technologists appear in the roster, status badges are color-coded correctly, shift overflow warnings are shown, and the roster is usable on mobile as cards.

---

## AC-R04-06: Department Worklist Management

| AC ID | Links to | Criteria (Given/When/Then) | Verification Method | Validator Gate |
|-------|----------|----------------------------|---------------------|----------------|
| AC-R04-06-01 | FR-R04-06 | **Given** I navigate to the Worklist tab, **when** the worklist loads, **then** I observe a filterable, paginated table of all department exams with columns: Accession, Patient (initials), Modality, Protocol, Priority, Technologist, Status, Scheduled Time. Default sort by scheduled time ascending. | VE + AT | Screenshot shows all columns; 25 rows per page; pagination controls at bottom |
| AC-R04-06-02 | FR-R04-06 | **Given** I apply filters (modality=CT, priority=STAT, status=pending) and click "Apply", **when** the table updates, **then** I observe only CT STAT pending exams shown, and the row count reflects the filtered result. | AT + VE | API call includes filter params; table shows only matching rows; count matches |
| AC-R04-06-03 | FR-R04-06 | **Given** I select 3 exam rows via checkboxes, **when** I click "Bulk Actions" toolbar, **then** I observe a dropdown with Reassign, Cancel, and Mark Complete options. | VE + AT | Dropdown shows all 3 options; dropdown opens on click; closes on outside click |
| AC-R04-06-04 | FR-R04-06 | **Given** I select "Reassign" from bulk actions, **when** I choose a target technologist and confirm, **then** I observe all selected exams are reassigned and the table refreshes with updated technologist column values. | AT + AL | API call `PUT /api/v2/schedule/bulk-reassign` succeeds; table refreshes; audit log entries created for each reassignment |
| AC-R04-06-05 | FR-R04-06, NFR-R04-05 | **Given** the worklist has 100+ exams, **when** I scroll, **then** I observe virtualization with smooth scrolling (60fps) and a loading indicator at the scroll position. | PM + AT | Frame timing measured at 60fps during scroll; loading indicator appears at scroll position |

**Validator Gate Verdict**: AC-R04-06 achieves acceptance criteria **only if** the worklist table shows all required columns, filtering works correctly, bulk actions are functional, and virtualization maintains 60fps scroll performance.

---

## AC-R04-07: Bulk Exam Reassignment (Override)

| AC ID | Links to | Criteria (Given/When/Then) | Verification Method | Validator Gate |
|-------|----------|----------------------------|---------------------|----------------|
| AC-R04-07-01 | FR-R04-07 | **Given** I click "Override" on the schedule board toolbar, **when** the override modal opens, **then** I observe options: "Reassign all from technologist" or "Reassign all from modality", with a search/select for the source and a search/select for the target. | VE + AT | Modal renders with both options; source and target selectors have search/autocomplete |
| AC-R04-07-02 | FR-R04-07 | **Given** I select a source technologist who has 5 pending exams, **when** I choose a target technologist and click "Reassign", **then** I observe a confirmation modal listing all 5 affected exams with their priority and scheduled time, and "Confirm Reassign" / "Cancel" buttons. | VE + AT | Confirmation modal shows all 5 exams; each row shows priority badge and scheduled time; both buttons present |
| AC-R04-07-03 | FR-R04-07 | **Given** I confirm the reassignment, **when** the operation completes, **then** I observe all 5 exams are reassigned to the target technologist, the board updates, and each reassignment is logged in the audit trail (verified by database query). | AT + AL | Database query: `audit_log` has 5 entries with `action='bulk_reassign'`; board shows updated technologist names |
| AC-R04-07-04 | FR-R04-07 | **Given** the target technologist already has overlapping exams, **when** I confirm, **then** I observe a warning listing the conflicts and asking me to resolve them before confirming. | VE + AT | Warning modal lists conflicting exams; Confirm button is disabled until conflicts are resolved or override is confirmed |

**Validator Gate Verdict**: AC-R04-07 achieves acceptance criteria **only if** the override modal shows all affected exams, confirmation requires explicit action, audit trail records each reassignment, and conflicts are detected and reported before execution.

---

## AC-R04-08: Real-Time Conflict Detection

| AC ID | Links to | Criteria (Given/When/Then) | Verification Method | Validator Gate |
|-------|----------|----------------------------|---------------------|----------------|
| AC-R04-08-01 | FR-R04-08 | **Given** I drag an exam to a time slot where the same technologist already has an exam, **when** I drop it, **then** I observe a red inline badge on the target slot with tooltip "Conflict: {technologist_name} already scheduled for {exam_id} at this time" and the exam snaps back to its original position. | VE + AT | Screenshot shows red badge and tooltip; exam returns to original position; no API call made |
| AC-R04-08-02 | FR-R04-08 | **Given** I drag an exam to a time slot where the same modality is already booked, **when** I drop it, **then** I observe a red inline badge on the target slot with tooltip "Conflict: {modality} already booked at this time" and the exam snaps back. | VE + AT | Screenshot shows red badge with modality conflict tooltip; exam snaps back |
| AC-R04-08-03 | FR-R04-08 | **Given** I assign an exam to a technologist who is already assigned to an overlapping exam, **when** I confirm the assignment, **then** I observe a conflict warning modal with the conflicting exam details and "Cancel" / "Override Anyway" buttons. | VE + AT | Modal shows conflicting exam details; both buttons functional; Override Anyway proceeds with assignment |
| AC-R04-08-04 | FR-R04-08, NFR-R04-04 | **Given** I drag an exam to a non-conflicting slot, **when** I drop it, **then** I observe no conflict badges, the exam moves smoothly to the new slot, and the operation completes within 200ms of the drop. | PM + AT | Drop operation timing measured ≤200ms; no conflict badges shown |

**Validator Gate Verdict**: AC-R04-08 achieves acceptance criteria **only if** conflicts are detected for both technologist double-booking and modality double-booking, conflict badges are red with tooltips, and non-conflicting drops complete within 200ms.

---

## AC-R04-09: Shift Handoff Report Generation

| AC ID | Links to | Criteria (Given/When/Then) | Verification Method | Validator Gate |
|-------|----------|----------------------------|---------------------|----------------|
| AC-R04-09-01 | FR-R04-09 | **Given** I click "Generate Handoff Report" button, **when** the report is generated, **then** I observe a preview with: pending exams count, STAT exams not yet started, exams in progress with estimated completion time, and any conflicts/overrides applied. | VE + AT | Report preview renders with all 4 sections; counts are accurate per DB query |
| AC-R04-09-02 | FR-R04-09 | **Given** I click "Export as PDF", **when** the PDF generates, **then** I observe a PDF download with the same content formatted for printing (header with shift dates, footer with page numbers). | AT + VE | PDF download triggered; PDF content matches preview; header has shift dates; footer has page numbers |
| AC-R04-09-03 | FR-R04-09 | **Given** I click "Copy to Clipboard", **when** the copy completes, **then** I observe a green toast "Report copied to clipboard" and the report text is available for pasting. | AT + VE | Toast renders with green background; clipboard contains report text; paste test successful |
| AC-R04-09-04 | FR-R04-09 | **Given** there are no pending exams for the shift, **when** I generate the report, **then** I observe an empty state "No pending exams for this shift" with a "Copy empty report" option. | VE + AT | Empty state renders; "Copy empty report" button present and functional |

**Validator Gate Verdict**: AC-R04-09 achieves acceptance criteria **only if** the report includes all 4 sections, PDF export produces a printable document, clipboard copy works, and empty states are handled gracefully.

---

## AC-R04-10: Board/Calendar View Toggle

| AC ID | Links to | Criteria (Given/When/Then) | Verification Method | Validator Gate |
|-------|----------|----------------------------|---------------------|----------------|
| AC-R04-10-01 | FR-R04-10 | **Given** I am on the schedule board view, **when** I click the "Calendar" toggle, **then** I observe the view switches to a calendar with exam blocks color-coded by priority (STAT=red, urgent=yellow, routine=gray). | VE + AT | Screenshot shows calendar view; blocks are color-coded by priority |
| AC-R04-10-02 | FR-R04-10 | **Given** I am in calendar view, **when** I click the "Board" toggle, **then** I observe the view switches back to the schedule board with the same data and the current date filter preserved. | AT | Board view renders with same exams; date filter is the same as when switching to calendar |
| AC-R04-10-03 | FR-R04-10 | **Given** I am in calendar week view, **when** I click a day, **then** I observe a drill-down showing all exams for that day in a side panel. | VE + AT | Side panel opens with all exams for the clicked day; panel has close button |
| AC-R04-10-04 | FR-R04-10 | **Given** I switch between board and calendar views, **when** the view changes, **then** I observe the transition is smooth (no full page reload) and the current date filter is preserved. | AT | No full page reload (SPA navigation); date filter value is the same in both views |

**Validator Gate Verdict**: AC-R04-10 achieves acceptance criteria **only if** the calendar view correctly color-codes exams by priority, the board/calendar toggle preserves data and filters, and the transition is smooth without page reload.

---

## Excluded Scope / Out of Scope

The following are explicitly **NOT** covered by these acceptance criteria and are out of scope for R04 service-coordinator requirements:

### Out of Scope — Technical
1. **Patient registration** (R08) — coordinator does not register patients
2. **Exam acquisition/imaging** (R06/R07) — coordinator assigns, technologist operates
3. **DICOM image viewing/measurement** (R12/R18) — coordinator references studies, does not view images
4. **Billing/payment** (R09) — outside coordinator scope
5. **System administration** (R01/R02) — tenant config, user management, DICOM AE setup
6. **QA/protocol management** (R05) — separate role with its own requirements package
7. **AI/CAD integration** (v3.2+ roadmap) — not in v3.0 scope
8. **Mobile native app** — PWA only; mobile view is responsive adaptation

### Out of Scope — Clinical
1. **Radiologist reading workflow** (R12/R18) — coordinator assigns exams, radiologist interprets
2. **Technologist exam acquisition protocol** (R06/R07) — coordinator schedules, technologist performs
3. **Patient consent handling** (R08/R11) — registration and nursing responsibilities
4. **Critical findings escalation** (R12/R18) — coordinator may reassign but does not manage escalation

### Out of Scope — Operational
1. **Shift handoff PDF formatting** — PDF generation is a backend concern; frontend triggers the report
2. **Audit log retention policy** — R01 manages audit log retention; R04 generates audit entries
3. **Multi-site federation** — single-site coordinator scope only

---

## Quality Gate Summary

| Artifact | Completeness | Feasibility | Usability | Validator |
|----------|--------------|-------------|-----------|-----------|
| 01-user-requirements.md | ✅ All FR/NFR with IDs | ✅ Performance quantified | ✅ Error/empty states specified | ✅ 6 new APIs flagged |
| 02-workflow-maps.md | ✅ 5 workflows with Mermaid | ✅ All states (loading/error/success) | ✅ Friction points flagged | ✅ Integration touchpoints mapped |
| 03-user-stories.md | ✅ 10 stories with Given/When/Then | ✅ Dependencies listed | ✅ A11y + performance ACs | ✅ 4-phase priority order |
| 04-ui-ux-requirements.md | ✅ 6 screens, all 6 states per component | ✅ Tokens referenced | ✅ Keyboard nav specified | ✅ Contrast ratios measured |
| 05-metrics-slas.md | ✅ 10 metrics, 3 SLA tiers | ✅ Measurement method specified | ✅ Dashboards assigned | ✅ 3-tier SLA definitions |
| 06-acceptance-criteria.md | ✅ 10 AC groups, FR/NFR mapping | ✅ Verification methods (AT/VE/PM/AL) | ✅ Observable outcomes | ✅ Validator gate per AC group |

**Overall Verdict**: From the visual evidence, structured requirements, and measurable acceptance criteria, I observe the R04 Service Coordinator requirements package — **Goal ACHIEVED** with the following conditions:

1. **6 new API endpoints required** (flagged in FR-R04 requirements) — must be designed and implemented before R04 workflows functional.
2. **WebSocket real-time push** — critical path for assignment notifications to technologist worklists.
3. **Drag-and-drop library** — requires `@dnd-kit/core` or `react-dnd` for schedule board interactions.
4. **PDF generation service** — requires backend PDF service (puppeteer/weasyprint) for handoff reports.
5. **Conflict detection algorithm** — must handle both technologist double-booking and modality double-booking in real-time.

**Next Steps**:
1. Delegate API contract design to `frontend-to-backend-requirements` skill
2. Delegate RESTful resource design to `rest-api-design` skill
3. Schedule stakeholder review with R04 service coordinator
4. Prioritize Phase 1 user stories (US-R04-01, 02, 03, 04, 05) for MVP
5. Conduct usability testing with 2-3 service coordinators before full implementation