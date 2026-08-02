# User Stories — Radiology & Imaging Service QI/QA Team (R05)

**Version**: 1.0.0 (v3.0 scope)
**Status**: Final
**Date**: 2026-08-02

---

## Story Index (v3.0 Must Priority)

| Story ID | Title | Priority | FR Links |
|----------|-------|----------|----------|
| US-R05-01 | QA Review Queue | Must | FR-R05-01, NFR-R05-01, NFR-R05-03, NFR-R05-09 |
| US-R05-02 | QA Review Workflow (Pass/Fail + Dose) | Must | FR-R05-02, NFR-R05-02, NFR-R05-07 |
| US-R05-03 | Protocol Registry CRUD | Must | FR-R05-03, NFR-R05-04 |
| US-R05-04 | QA Score Persistence (feeds R03) | Must | FR-R05-04 |
| US-R05-05 | Corrective Action Inbox | Must | FR-R05-05, NFR-R05-05 |
| US-R05-06 | Incident/Retake Logging | Must | FR-R05-06, NFR-R05-05 |
| US-R05-07 | Personal Compliance Dashboard | Must | NFR-R05-01, NFR-R05-09 |
| US-R05-08 | RBAC QA Role | Must | FR-R05-07 |
| US-R05-09 | Peer Review Assignment (R05→R12) | Must | FR-R05-10 |
| US-R05-10 | Peer Review Comparison & Discrepancy | Must | FR-R05-10 |
| US-R05-11 | QA Queue Auto-Population (R06 trigger) | Must | FR-R05-01, FR-R05-04 |
| US-R05-12 | Incident Notification to R06 | Must | FR-R05-06 |
| US-R05-13 | Corrective Action Escalation to R03 | Must | FR-R05-05, FR-R05-10 |

---

## US-R05-01: QA Review Queue

**Story**: As a QA reviewer, I want a filterable, paginated queue of exams awaiting QA review so that I can efficiently prioritize and process my daily review workload.

**Priority**: Must

### Acceptance Criteria

**AC-R05-01-01** (Functional): **Given** I open the QA Queue page (`/qa/queue`), **when** the queue loads, **then** a table renders with columns: Accession, Patient (initials only), Modality, Protocol, Scheduled Date, Priority badge, Status badge, and "Review" action button per row.

**AC-R05-01-02** (Filtering): **Given** the queue table is visible, **when** I apply filters (modality dropdown, status dropdown, date range picker, priority radio), **then** the table refreshes to show only matching exams.

**AC-R05-01-03** (Pagination): **Given** there are >50 pending exams, **when** the queue renders, **then** pagination controls appear at the bottom (20/50/100 per page selector), and the table shows 50 exams per page with virtualized rows.

**AC-R05-01-04** (Auto-refresh): **Given** the queue is displayed, **when** 1 minute elapses, **then** the queue auto-refreshes (new exams appear, completed exams are removed), with a subtle "Updated 1m ago" timestamp.

**AC-R05-01-05** (Loading State): **Given** I navigate to `/qa/queue`, **when** data is fetching, **then** the table shows skeleton rows (5 rows) with a loading spinner.

**AC-R05-01-06** (Empty State): **Given** there are no pending exams, **when** the queue loads, **then** the table body shows "No exams pending QA review" with a "Check completed exams" link to the completed tab.

**AC-R05-01-07** (Error State): **Given** the API call fails, **when** the error occurs, **then** a toast appears ("Failed to load QA queue") and a "Retry" button is shown; the table shows its last cached data if available.

**AC-R05-01-08** (Accessibility - Keyboard): **Given** I navigate the queue table with keyboard, **when** I tab into the table, **then** arrow keys navigate rows, Enter opens the review form, Escape returns focus to the table.

**AC-R05-01-09** (Accessibility - Contrast): **Given** Priority badges (routine=gray, stat=red, escalated=amber), **when** viewed in grayscale, **then** each badge includes text label ("Routine"/"STAT"/"Escalated") in addition to color.

---

## US-R05-02: QA Review Workflow (Pass/Fail + Dose)

**Story**: As a QA reviewer, I want a structured QA review form for each exam so that I can consistently record pass/fail, dose metrics, and sequence compliance.

**Priority**: Must

### Acceptance Criteria

**AC-R05-02-01** (Functional): **Given** I click "Review" on a queue row, **when** the review page loads, **then** the page shows: "Open in Viewer" button (left side, links to `/files/{study_uid}` in new tab) + QA form (right side) with Pass/Fail radio group, Dose fields (DLP, CTDIvol, kVp, mAs), Sequence checklist (dynamic based on protocol.required_sequences), Comments textarea (max 500 chars), Submit/Cancel buttons.

**AC-R05-02-02** (Pass/Fail): **Given** the QA form is open, **when** I select Pass or Fail, **then** the selected radio button is highlighted with `--color-success` (Pass) or `--color-error` (Fail), and the form enables dose fields and sequence checklist.

**AC-R05-02-03** (Dose Validation): **Given** I enter a dose value, **when** I tab out of the field, **then** inline validation runs within 200ms: DLP must be 0-10000 mGy·cm, CTDIvol must be 0-100 mGy, kVp must be 60-150, mAs must be 1-1000. Invalid values show red border + error message below the field.

**AC-R05-02-04** (Sequence Checklist): **Given** the protocol has required sequences, **when** the form loads, **then** a checklist renders with each sequence as a row (name, phase, contrast boolean). Each row has a checkbox (checked=present, unchecked=missing). The checklist auto-populates from `protocol.required_sequences` JSONB.

**AC-R05-02-05** (Comments): **Given** I enter text in the Comments textarea, **when** I type, **then** a character counter shows "N/500" and the textarea prevents input beyond 500 characters.

**AC-R05-02-06** (Submit): **Given** all required fields are filled (Pass/Fail selected, dose values entered or cleared), **when** I click "Submit", **then** a loading spinner appears on the button, the API call is made, and on success a toast appears "QA score submitted" and the queue refreshes (exam removed from pending).

**AC-R05-02-07** (Cancel): **Given** I have made changes to the form, **when** I click "Cancel", **then** a confirmation dialog appears ("Discard changes?"), and if confirmed, the form resets and returns to the queue.

**AC-R05-02-08** (Accessibility - Form): **Given** I use keyboard navigation on the QA form, **when** I tab through fields, **then** focus order is logical (Pass/Fail → Dose fields → Sequence checkboxes → Comments → Submit), all fields have associated `<label>` elements, and error messages are announced by screen readers (`aria-live="assertive"`).

**AC-R05-02-09** (Accessibility - Contrast): **Given** Pass/Fail radio buttons, **when** viewed in color-blind simulator, **then** Pass has a checkmark icon (✓) + green text "Pass", Fail has an X icon (✗) + red text "Fail", distinguishable without color alone.

---

## US-R05-03: Protocol Registry CRUD

**Story**: As a QA lead, I want to create, edit, and delete protocols with required sequences and ACR benchmarks so that the QA team has a structured reference for exam quality standards.

**Priority**: Must

### Acceptance Criteria

**AC-R05-03-01** (List): **Given** I open the Protocol Registry (`/qa/protocols`), **when** the page loads, **then** a table renders with columns: Code, Name, Modality, Body Part, # Sequences, # Benchmarks, Actions (Edit/Delete). Built-in roles cannot be deleted.

**AC-R05-03-02** (Create): **Given** I click "Add Protocol", **when** the modal opens, **then** I can fill: Code (required, unique, alphanumeric), Name (required), Modality (dropdown: CT/MR/US/DX/MG/FL/PET), Body Part (text), Required Sequences (dynamic list: add/remove rows with sequence name, phase, contrast boolean), ACR Benchmarks (key-value editor: add/remove key-value pairs). Validation: code uniqueness check (async, shows error if duplicate), ≥1 sequence required.

**AC-R05-03-03** (Edit): **Given** I click "Edit" on an existing protocol, **when** the modal opens, **then** all fields are pre-populated with existing values and the form behaves identically to Create.

**AC-R05-03-04** (Delete): **Given** I click "Delete" on a protocol, **when** the confirmation dialog appears, **then** it shows "Delete protocol '{name}'? This action cannot be undone." and requires explicit confirmation. Built-in protocols are protected (delete button hidden or disabled).

**AC-R05-03-05** (Save): **Given** I fill all required fields and click "Save", **when** the form submits, **then** a loading spinner appears, the API call is made, and on success the modal closes and the table refreshes with the new/updated protocol.

**AC-R05-03-06** (Error Handling): **Given** the API returns an error (e.g., duplicate code), **when** the error occurs, **then** an inline error message appears below the Code field ("Protocol code already exists") and the form remains open with entered data preserved.

**AC-R05-03-07** (Accessibility): **Given** I navigate the protocol form with keyboard, **when** I tab through fields, **then** focus order is logical, all inputs have labels, and the dynamic sequence list supports keyboard add/remove (Tab to add button, Enter to confirm).

**AC-R05-03-08** (Responsive): **Given** I view the protocol registry on a tablet (768px), **when** the viewport narrows, **then** the table becomes horizontally scrollable and the modal form stacks vertically.

---

## US-R05-04: QA Score Persistence (Feeds R03)

**Story**: As a QA reviewer, I want my QA scores to be persisted to the database so that they feed the R03 Service Director's protocol compliance dashboard.

**Priority**: Must

### Acceptance Criteria

**AC-R05-04-01** (Database Write): **Given** I submit a QA score (Pass/Fail + dose + sequence compliance + comments), **when** the API processes the request, **then** a row is inserted into `qa_scores` with all fields: `protocol_id`, `study_uid`, `sequence_compliance` (JSONB), `dose_dlp`, `dose_ctdivol`, `dose_kvp`, `dose_mas`, `pass_fail`, `comments`, `reviewed_by` (user ID), `reviewed_at` (timestamp).

**AC-R05-04-02** (Queue Update): **Given** the QA score is persisted, **when** the transaction commits, **then** the corresponding `qa_queue` entry status is updated to 'completed' and `updated_at` is set.

**AC-R05-04-03** (R03 Dashboard Refresh): **Given** R03 Service Director has the protocol compliance dashboard open, **when** a new QA score is submitted, **then** the R03 dashboard refreshes (auto-refresh at 5min interval) and the protocol's compliance % updates to reflect the new score.

**AC-R05-04-04** (Duplicate Prevention): **Given** a QA score already exists for a study_uid + protocol_id combination, **when** a second submission is attempted, **then** the API returns 409 Conflict with message "QA score already exists for this study and protocol" and the form shows the existing score for reference.

**AC-R05-04-05** (Audit Log): **Given** a QA score is submitted, **when** the transaction commits, **then** an audit log entry is created: `{user_id, action: 'qa_score_submitted', study_uid, protocol_id, pass_fail, timestamp}`.

---

## US-R05-05: Corrective Action Inbox

**Story**: As a QA reviewer, I want to receive and respond to corrective actions assigned by the Service Director so that I can investigate protocol gaps and document resolution.

**Priority**: Must

### Acceptance Criteria

**AC-R05-05-01** (Inbox): **Given** I open the Corrective Actions page (`/qa/actions`), **when** the page loads, **then** a card list renders showing: Source badge (R03/R05_self/R06), Issue Description, Study UIDs (expandable to show full list), Assigned Date, Status badge (Open/In Progress/Resolved), and action buttons (Review/Close).

**AC-R05-05-02** (Expand): **Given** I click "Review" on an open corrective action card, **when** the card expands, **then** it reveals: Study UID list with clickable links (opens `/files/{study_uid}` in new tab), Findings textarea (for documenting root cause), Actions Taken textarea (for documenting resolution), and "Resolve" button.

**AC-R05-05-03** (Resolve): **Given** I have entered findings and actions taken, **when** I click "Resolve", **then** a confirmation dialog appears ("Mark this corrective action as resolved?"), and on confirmation the card status changes to "Resolved" with `resolved_at` timestamp, and a success toast appears.

**AC-R05-05-04** (Notification): **Given** a new corrective action is assigned to me, **when** it is created, **then** an in-app notification badge appears on the sidebar with the count of unread actions.

**AC-R05-05-05** (Filtering): **Given** the corrective actions list, **when** I apply status filter (Open/In Progress/Resolved), **then** the list refreshes to show only matching actions.

**AC-R05-05-06** (Empty State): **Given** there are no corrective actions assigned to me, **when** the page loads, **then** the list shows "No corrective actions assigned" with a checkmark illustration.

**AC-R05-05-07** (Accessibility): **Given** I navigate the corrective action cards with keyboard, **when** I tab through, **then** focus order is logical (card → Review button → Resolve button), and all interactive elements have visible focus rings.

---

## US-R05-06: Incident/Retake Logging

**Story**: As a QA reviewer, I want to log incidents and retakes with structured incident types and linked studies so that we can track quality trends and trigger retraining when needed.

**Priority**: Must

### Acceptance Criteria

**AC-R05-06-01** (Incident Form): **Given** I click "Log Incident" on the Incidents page (`/qa/incidents`), **when** the form opens, **then** I can fill: Study UID (search/autocomplete by accession, patient name last 4, date), Repeat Study UID (optional, same autocomplete), Incident Type (dropdown: positioning, artifact, protocol_deviation, patient_motion, equipment_malfunction, contrast_extravasation), Description (textarea, max 500 chars, with character counter).

**AC-R05-06-02** (Study Linking): **Given** I enter a Study UID, **when** the form loads, **then** the study's metadata (patient initials, modality, date) is displayed below the field for verification.

**AC-R05-06-03** (Submit): **Given** I fill the incident form and click "Submit", **when** the API processes the request, **then** a new row is inserted into `incidents` table with `resolved=false`, a success toast appears, and the incident appears in the incidents table.

**AC-R05-06-04** (R06 Notification): **Given** an incident is logged that requires retraining (incident_type in [positioning, artifact, protocol_deviation, patient_motion]), **when** the incident is created, **then** the R06 technologist who performed the study receives an in-app notification: "Incident logged for your exam: [incident_type]. Please review technique."

**AC-R05-06-05** (Incident List): **Given** the Incidents page is open, **when** the table renders, **then** it shows: Study UID, Repeat Study UID (or "—"), Incident Type badge, Description (truncated), Reported By, Date, Resolved badge (Yes/No), and "Resolve" button for unresolved incidents.

**AC-R05-06-06** (Resolve Incident): **Given** I click "Resolve" on an unresolved incident, **when** I confirm, **then** the incident status changes to resolved with `resolved_at` timestamp and the table refreshes.

**AC-R05-06-07** (Accessibility): **Given** I navigate the incident form with keyboard, **when** I tab through fields, **then** focus order is logical and all inputs have associated labels.

---

## US-R05-07: Personal Compliance Dashboard

**Story**: As a QA reviewer, I want a personal compliance dashboard showing my review activity and protocol compliance trends so that I can track my QA workload and performance.

**Priority**: Must

### Acceptance Criteria

**AC-R05-07-01** (KPI Cards): **Given** I open the QA Dashboard (`/qa/dashboard`), **when** the page loads, **then** I see KPI cards: Exams Reviewed This Week (number), My Compliance % (percentage with trend sparkline), Incidents Logged (number), Open Corrective Actions (number).

**AC-R05-07-02** (Trend): **Given** a KPI card shows a trend, **when** I hover the card, **then** a tooltip shows the 7-day breakdown (e.g., "Mon: 5, Tue: 3, Wed: 7, ...").

**AC-R05-07-03** (Date Range): **Given** the dashboard is displayed, **when** I change the date range selector (This Week / Last Week / This Month / Custom), **then** all KPI cards and trend data refresh to match the selected range.

**AC-R05-07-04** (Loading State): **Given** I navigate to the dashboard, **when** data is fetching, **then** KPI cards show skeleton loaders.

**AC-R05-07-05** (Empty State): **Given** no QA reviews have been completed this week, **when** the dashboard loads, **then** the "Exams Reviewed" card shows "0" with "No reviews this week" message and a "Start Reviewing" CTA link to the QA Queue.

**AC-R05-07-06** (Accessibility): **Given** I navigate the dashboard with keyboard, **when** I tab through KPI cards, **then** focus order is logical and all values are announced by screen readers with full context (e.g., "Exams Reviewed This Week: 12, up from 8 last week").

---

## US-R05-08: RBAC QA Role

**Story**: As a PACS Administrator, I want a built-in `qa_team` role with QA permissions so that I can assign QA team members without custom role configuration.

**Priority**: Must

### Acceptance Criteria

**AC-R05-08-01** (Role Exists): **Given** I navigate to `/roles` as admin, **when** the roles table loads, **then** `qa_team` appears in the built-in roles list (non-deletable), with permissions: `FILE_READ`, `STUDY_READ`, `QA_READ`, `QA_WRITE`, `PROTOCOL_MANAGE`.

**AC-R05-08-02** (Permission Enforcement): **Given** a user has `qa_team` role, **when** they access `/qa/queue`, **then** access is granted (200); **when** they access `/users` or `/tenants`, **then** access is denied (403).

**AC-R05-08-03** (Token Includes Permissions): **Given** a `qa_team` user logs in, **when** the JWT is issued, **then** the token's `permissions` claim includes the 5 QA permissions, and `role` claim is `qa_team`.

**AC-R05-08-04** (UI Visibility): **Given** a `qa_team` user logs in, **when** the sidebar renders, **then** the following items are visible: Study List, QA Queue, Protocols, Incidents, Corrective Actions, Peer Review, QA Dashboard, Account. Admin submenu is hidden.

**AC-R05-08-05** (Tenant Scoping): **Given** a `qa_team` user in Tenant A accesses QA features, **when** the API executes, **then** all queries are scoped to Tenant A's database (no cross-tenant data leakage).

---

## US-R05-09: Peer Review Assignment (R05→R12)

**Story**: As a QA lead, I want to assign peer reviews to radiologists so that I can systematically review critical findings, trainee reads, and conduct random audits.

**Priority**: Must

### Acceptance Criteria

**AC-R05-09-01** (Assignment Form): **Given** I open the Peer Review page (`/qa/peer-review`), **when** the assignment form is visible, **then** I can: Search study by accession/patient name (autocomplete), select radiologist from dropdown (filtered by role=radiologist), select reason (critical_finding/trainee_read/random_audit/complaint), and click "Assign".

**AC-R05-09-02** (Assignment Creation): **Given** I fill the assignment form and click "Assign", **when** the API processes the request, **then** a `peer_reviews` row is created with `status='assigned'`, the assigned radiologist receives an in-app notification, and the peer review list table refreshes with the new entry.

**AC-R05-09-03** (Peer Review List): **Given** I view the peer review list, **when** it renders, **then** it shows: Study UID, Original Reader, Peer Reviewer, Status (assigned/in_progress/completed), Discrepancy Badge (none/minor/major/critical), and Actions (View Comparison / Escalate if major/critical).

**AC-R05-09-04** (Filtering): **Given** the peer review list, **when** I apply filters (status, discrepancy level, date range, reason), **then** the list refreshes to show matching entries.

**AC-R05-09-05** (Accessibility): **Given** I navigate the assignment form with keyboard, **when** I tab through fields, **then** focus order is logical and all inputs have associated labels.

---

## US-R05-10: Peer Review Comparison & Discrepancy Flagging

**Story**: As a QA lead, I want to compare original reports with peer review findings and flag discrepancies so that I can escalate major/critical discrepancies to the Service Director.

**Priority**: Must

### Acceptance Criteria

**AC-R05-10-01** (Comparison Modal): **Given** I click "View Comparison" on a completed peer review, **when** the modal opens, **then** it shows a side-by-side view: Original Report (left, from `original_report_id`) and Peer Review Findings (right), with the discrepancy level badge prominently displayed.

**AC-R05-10-02** (Discrepancy Level): **Given** the comparison modal is open, **when** I review the findings, **then** the discrepancy level is shown with color and icon: none (green ✓), minor (amber ⚠), major (red ✗), critical (dark red 🔴).

**AC-R05-10-03** (Escalate): **Given** the discrepancy level is major or critical, **when** I click "Escalate", **then** a confirmation dialog appears ("Escalate this discrepancy to Service Director?"), and on confirmation the peer review is marked `escalated=true`, the Service Director receives an in-app notification, and a corrective action is auto-created in R05's corrective action inbox.

**AC-R05-10-04** (Close): **Given** the discrepancy level is none or minor, **when** I click "Close", **then** the modal closes and the peer review status remains 'completed' without escalation.

**AC-R05-10-05** (Accessibility): **Given** I navigate the comparison modal with keyboard, **when** I tab through, **then** focus is trapped within the modal, Escape closes it and returns focus to the peer review list row, and all content is readable by screen readers.

---

## US-R05-11: QA Queue Auto-Population (R06 Trigger)

**Story**: As a QA reviewer, I want the QA queue to auto-populate when a technologist marks an exam complete, so that I don't need to manually add exams to review.

**Priority**: Must

### Acceptance Criteria

**AC-R05-11-01** (API Contract): **Given** R06 Technologist marks an exam complete, **when** the exam completion event fires, **then** a `POST /api/v2/qa/queue` call is made with `{study_uid, protocol_id, priority}`. The API creates a `qa_queue` entry with `status='pending'` and returns `201`.

**AC-R05-11-02** (Duplicate Prevention): **Given** a queue entry already exists for a study_uid, **when** the R06 completion event fires again, **then** the API returns `409 Conflict` with message "QA queue entry already exists for this study" and does not create a duplicate.

**AC-R05-11-03** (Queue Appearance): **Given** a new queue entry is created, **when** the QA reviewer refreshes the queue (or auto-refresh triggers), **then** the new exam appears at the top of the pending queue with priority badge (stat=red, routine=gray).

**AC-R05-11-04** (Error Handling): **Given** the R06 completion API call fails (e.g., protocol_id not found), **when** the error occurs, **then** the R06 UI shows an error toast and the exam remains in the worklist (not lost).

**AC-R05-11-05** (Audit): **Given** a queue entry is created, **when** the entry is created, **then** an audit log entry records: `{user_id: tech_id, action: 'qa_queue_entry_created', study_uid, protocol_id, timestamp}`.

---

## US-R05-12: Incident Notification to R06

**Story**: As a QA reviewer, I want the technologist who performed a flagged exam to be notified when an incident is logged, so that they can review and improve their technique.

**Priority**: Must

### Acceptance Criteria

**AC-R05-12-01** (Notification): **Given** an incident is logged with `incident_type` in [positioning, artifact, protocol_deviation, patient_motion], **when** the incident is created, **then** the R06 technologist who performed the study receives an in-app notification: "Incident logged for your exam [accession]: [incident_type]. Please review technique."

**AC-R05-12-02** (Notification Display): **Given** the notification is created, **when** the R06 user views their sidebar, **then** a notification badge appears with the count of unread incident notifications.

**AC-R05-12-03** (Notification Content): **Given** the R06 user clicks the notification, **when** they navigate, **then** they are taken to the incident details page (`/qa/incidents`) with the specific incident highlighted.

**AC-R05-12-04** (No Notification for Equipment): **Given** an incident is logged with `incident_type=equipment_malfunction`, **when** the incident is created, **then** the R06 technologist is NOT notified (equipment issues are handled by R10 Biomedical Engineer, not the technologist).

**AC-R05-12-05** (Accessibility): **Given** notifications are delivered, **when** they appear, **then** an ARIA live region (assertive) announces the notification content without stealing focus.

---

## US-R05-13: Corrective Action Escalation to R03

**Story**: As a QA reviewer, I want to escalate major/critical peer review discrepancies to the Service Director so that they can take leadership action on systemic quality issues.

**Priority**: Must

### Acceptance Criteria

**AC-R05-13-01** (Escalate Button): **Given** a peer review has discrepancy_level of major or critical, **when** the QA lead views the comparison modal, **then** an "Escalate to Service Director" button is visible (not visible for none/minor discrepancies).

**AC-R05-13-02** (Escalation Confirmation): **Given** I click "Escalate", **when** the confirmation dialog appears, **then** it shows "Escalate this [major/critical] discrepancy to the Service Director? This will create a corrective action and notify the original radiologist." with Escalate and Cancel buttons.

**AC-R05-13-03** (Escalation Action): **Given** I confirm the escalation, **when** the API processes the request, **then**: (1) `peer_reviews.escalated` is set to `true`, (2) a corrective action is auto-created in R05's corrective action inbox with `source='R05_peer_review'` and `status='open'`, (3) the Service Director (R03) receives an in-app notification with the study UID and discrepancy summary, (4) the original radiologist (R12) receives an in-app notification that their case was flagged.

**AC-R05-13-04** (Audit): **Given** a peer review is escalated, **when** the escalation occurs, **then** an audit log entry records: `{user_id: qa_lead_id, action: 'peer_review_escalated', study_uid, discrepancy_level, timestamp}`.

**AC-R05-13-05** (Accessibility): **Given** the escalation dialog opens, **when** keyboard focus is managed, **then** focus is trapped within the dialog, Escape closes without escalating, and Enter confirms the escalation.

---

## Cross-Reference Matrix

| AC ID | FR/NFR Link | Verification Method | Validator Gate |
|-------|-------------|---------------------|----------------|
| AC-R05-01-01 | FR-R05-01 | Playwright: assert table columns | ✓ Observable: columns present; ✓ Token: status badges; Search for: missing column, wrong badge |
| AC-R05-01-02 | FR-R05-01 | Playwright: apply filters, assert table refresh | ✓ Observable: filtered rows; Search for: filter not working |
| AC-R05-01-03 | NFR-R05-09 | Playwright: assert pagination controls + virtualization | ✓ Observable: pagination + smooth scroll; Search for: non-virtualized rendering |
| AC-R05-01-04 | NFR-R05-03 | Synthetic probe: wait 60s, assert new exam appears | ✓ Observable: new row appears; Search for: stale data |
| AC-R05-01-05 | FR-R05-01 | Visual test: skeleton rows visible during load | ✓ Observable: skeleton visible; ✓ States: loading; Search for: blank table during load |
| AC-R05-01-06 | FR-R05-01 | Visual test: seed empty tenant, assert empty state | ✓ Observable: empty state + CTA; ✓ States: empty; Search for: error state shown instead |
| AC-R05-01-07 | FR-R05-01 | Error injection: mock API 500, assert retry | ✓ Observable: toast + retry; ✓ States: error; Search for: no retry, crash |
| AC-R05-01-08 | NFR-R05-06/10 | Keyboard test: tab, arrow, Enter, Escape | ✓ Observable: focus path; ✓ A11y: keyboard; Search for: focus lost, wrong order |
| AC-R05-01-09 | NFR-R05-10 | Grayscale test: assert text labels on badges | ✓ Observable: text + icon in grayscale; Search for: color-only badges |
| AC-R05-02-01 | FR-R05-02 | Playwright: assert review page layout (viewer link + form) | ✓ Observable: layout correct; Search for: missing form fields |
| AC-R05-02-02 | FR-R05-02 | Playwright: select Pass, assert green highlight + enable dose fields | ✓ Observable: highlight + enabled fields; Search for: dose fields disabled on Pass |
| AC-R05-02-03 | NFR-R05-07 | Playwright: enter invalid dose, assert inline error within 200ms | ✓ Observable: error within 200ms; Search for: no validation, delayed error |
| AC-R05-02-04 | FR-R05-02 | Playwright: assert checklist auto-populated from protocol | ✓ Observable: checklist items match protocol JSONB; Search for: empty checklist |
| AC-R05-02-05 | FR-R05-02 | Playwright: type 501 chars, assert truncated at 500 | ✓ Observable: counter stops at 500; Search for: unlimited input |
| AC-R05-02-06 | FR-R05-02 | Playwright: click Submit, assert spinner → toast → queue refresh | ✓ Observable: spinner + toast; ✓ States: loading + success; Search for: no spinner, no toast |
| AC-R05-02-07 | FR-R05-02 | Playwright: click Cancel, assert confirmation dialog | ✓ Observable: dialog + cancel/confirm; Search for: no confirmation, data lost |
| AC-R05-02-08 | NFR-R05-06/10 | Keyboard test + axe-core: labels, aria-live | ✓ Observable: logical focus; ✓ A11y: labels + live; Search for: missing labels, no error announcement |
| AC-R05-02-09 | NFR-R05-10 | Coblis simulator: assert Pass/Fail distinguishable | ✓ Observable: icon + text in simulator; Search for: color-only distinction |
| AC-R05-03-01 | FR-R05-03 | Playwright: assert table columns + CRUD buttons | ✓ Observable: columns + buttons; Search for: missing column, no Add button |
| AC-R05-03-02 | FR-R05-03 | Playwright: fill form, assert validation (duplicate code, missing sequences) | ✓ Observable: inline errors; Search for: no validation, duplicate accepted |
| AC-R05-03-03 | FR-R05-03 | Playwright: click Edit, assert pre-populated form | ✓ Observable: fields pre-filled; Search for: empty form on edit |
| AC-R05-03-04 | FR-R05-03 | Playwright: click Delete, assert confirmation dialog | ✓ Observable: dialog + confirmation; Search for: no confirmation, immediate delete |
| AC-R05-03-05 | FR-R05-03 | Playwright: fill form, click Save, assert toast + table refresh | ✓ Observable: toast + refresh; ✓ States: loading + success; Search for: no toast, stale table |
| AC-R05-03-06 | FR-R05-03 | Error injection: mock duplicate code, assert inline error | ✓ Observable: inline error; ✓ States: error; Search for: no error, duplicate created |
| AC-R05-03-07 | NFR-R05-06/10 | Keyboard test + axe-core on protocol form | ✓ Observable: logical focus; ✓ A11y; Search for: missing labels, trapped focus |
| AC-R05-03-08 | NFR-R05-10 | Responsive test: assert table scrolls + modal stacks at 768px | ✓ Observable: responsive behavior; Search for: broken layout at tablet |
| AC-R05-04-01 | FR-R05-04 | DB query: assert qa_scores row exists after submit | ✓ Observable: DB row present; Search for: missing row, wrong fields |
| AC-R05-04-02 | FR-R05-04 | DB query: assert qa_queue status='completed' after submit | ✓ Observable: queue updated; Search for: queue still pending |
| AC-R05-04-03 | FR-R05-04 | Integration test: submit QA score, assert R03 dashboard compliance % updates | ✓ Observable: R03 dashboard updates; Search for: stale data on R03 dashboard |
| AC-R05-04-04 | FR-R05-04 | Playwright: submit duplicate, assert 409 + existing score shown | ✓ Observable: 409 + existing score; Search for: duplicate created, no error |
| AC-R05-04-05 | FR-R05-04 | DB query: assert audit log entry after QA score submit | ✓ Observable: audit entry present; Search for: missing audit entry |
| AC-R05-05-01 | FR-R05-05 | Playwright: assert corrective action cards render | ✓ Observable: cards with source badge + issue; Search for: missing cards, wrong badge |
| AC-R05-05-02 | FR-R05-05 | Playwright: click Review, assert card expands with findings textarea | ✓ Observable: card expands; ✓ States: expanded; Search for: card doesn't expand, no textarea |
| AC-R05-05-03 | FR-R05-05 | Playwright: click Resolve, assert confirmation dialog → status changes | ✓ Observable: dialog + status change; ✓ States: success; Search for: no confirmation, status unchanged |
| AC-R05-05-04 | FR-R05-05 | Integration test: create corrective action, assert notification badge | ✓ Observable: badge appears; Search for: no notification, badge missing |
| AC-R05-05-05 | FR-R05-05 | Playwright: apply status filter, assert list refreshes | ✓ Observable: filtered list; Search for: filter not working |
| AC-R05-05-06 | FR-R05-05 | Visual test: seed no actions, assert empty state | ✓ Observable: empty state + illustration; ✓ States: empty; Search for: error shown instead |
| AC-R05-05-07 | NFR-R05-06/10 | Keyboard test on corrective action cards | ✓ Observable: logical focus; ✓ A11y; Search for: trapped focus, missing focus ring |
| AC-R05-06-01 | FR-R05-06 | Playwright: assert incident form fields + autocomplete | ✓ Observable: form fields + autocomplete; Search for: missing field, no autocomplete |
| AC-R05-06-02 | FR-R05-06 | Playwright: enter study UID, assert metadata displayed | ✓ Observable: metadata below field; Search for: no metadata, blank field |
| AC-R05-06-03 | FR-R05-06 | Playwright: submit incident, assert toast + table row | ✓ Observable: toast + row; ✓ States: loading + success; Search for: no toast, no row |
| AC-R05-06-04 | FR-R05-06 | Integration test: log incident, assert R06 notification | ✓ Observable: R06 notification; Search for: no notification |
| AC-R05-06-05 | FR-R05-06 | Playwright: assert incidents table columns + badges | ✓ Observable: columns + badges; Search for: missing column, wrong badge |
| AC-R05-06-06 | FR-R05-06 | Playwright: click Resolve, assert status changes | ✓ Observable: status change; ✓ States: success; Search for: no status change |
| AC-R05-06-07 | NFR-R05-06/10 | Keyboard test on incident form | ✓ Observable: logical focus; ✓ A11y; Search for: missing labels |
| AC-R05-07-01 | NFR-R05-01 | Playwright: assert 4 KPI cards on dashboard | ✓ Observable: 4 cards; Search for: missing card, wrong values |
| AC-R05-07-02 | NFR-R05-01 | Playwright: hover KPI card, assert tooltip with 7-day breakdown | ✓ Observable: tooltip with breakdown; Search for: no tooltip, wrong data |
| AC-R05-07-03 | NFR-R05-01 | Playwright: change date range, assert all cards refresh | ✓ Observable: cards update; Search for: stale data after range change |
| AC-R05-07-04 | FR-R05-07 | Visual test: skeleton loaders visible during dashboard load | ✓ Observable: skeleton visible; ✓ States: loading; Search for: blank dashboard |
| AC-R05-07-05 | FR-R05-07 | Visual test: seed no reviews, assert empty state + CTA | ✓ Observable: empty state + CTA; ✓ States: empty; Search for: error state shown |
| AC-R05-07-06 | NFR-R05-06/10 | Keyboard test + screen reader on dashboard | ✓ Observable: logical focus; ✓ A11y: aria-label; Search for: missing aria-label, wrong focus |
| AC-R05-08-01 | FR-R05-07 | Playwright: assert qa_team role in built-in roles | ✓ Observable: role present + non-deletable; Search for: missing role, deletable built-in |
| AC-R05-08-02 | FR-R05-07 | API test: qa_team JWT, GET /qa/queue (200), GET /users (403) | ✓ Observable: 200 + 403; Search for: access to /users, missing 403 |
| AC-R05-08-03 | FR-R05-07 | JWT decode test: assert permissions in token | ✓ Observable: claims present; Search for: missing permissions, wrong role |
| AC-R05-08-04 | FR-R05-07 | Playwright: assert sidebar items for qa_team | ✓ Observable: correct sidebar items; Search for: admin submenu visible, extra items |
| AC-R05-08-05 | FR-R05-07 | Cross-tenant test: seed both tenants, query as Tenant A | ✓ Observable: no cross-tenant data; ✓ HIPAA: isolation; Search for: tenant leak |
| AC-R05-09-01 | FR-R05-10 | Playwright: assert assignment form fields + radiologist dropdown | ✓ Observable: form fields + dropdown; Search for: missing field, unfiltered dropdown |
| AC-R05-09-02 | FR-R05-10 | Playwright: click Assign, assert toast + table refresh + R12 notification | ✓ Observable: toast + refresh + notification; ✓ States: loading + success; Search for: no toast, no notification |
| AC-R05-09-03 | FR-R05-10 | Playwright: assert peer review list columns + discrepancy badge | ✓ Observable: columns + badge; Search for: missing column, wrong badge |
| AC-R05-09-04 | FR-R05-10 | Playwright: apply filters, assert list refreshes | ✓ Observable: filtered list; Search for: filter not working |
| AC-R05-09-05 | NFR-R05-06/10 | Keyboard test on assignment form | ✓ Observable: logical focus; ✓ A11y; Search for: missing labels |
| AC-R05-10-01 | FR-R05-10 | Playwright: click View Comparison, assert side-by-side modal | ✓ Observable: modal + side-by-side; Search for: modal missing, wrong layout |
| AC-R05-10-02 | FR-R05-10 | Playwright: assert discrepancy badge color + icon per level | ✓ Observable: color + icon per level; Search for: color-only, missing icon |
| AC-R05-10-03 | FR-R05-10 | Playwright: click Escalate (major), assert confirmation → escalation | ✓ Observable: dialog + escalation; ✓ States: success; Search for: no dialog, no escalation |
| AC-R05-10-04 | FR-R05-10 | Playwright: click Close (minor), assert modal closes without escalation | ✓ Observable: modal closes + no escalation; Search for: escalation triggered for minor |
| AC-R05-10-05 | NFR-R05-06/10 | Keyboard test: focus trap + Escape on comparison modal | ✓ Observable: focus trap + Escape; ✓ A11y; Search for: focus escape, no Escape close |
| AC-R05-11-01 | FR-R05-11 | Integration test: mock R06 POST, assert qa_queue entry created | ✓ Observable: DB row present; Search for: missing row, wrong status |
| AC-R05-11-02 | FR-R05-11 | Integration test: duplicate POST, assert 409 + no duplicate | ✓ Observable: 409 + no duplicate; Search for: duplicate created, 200 returned |
| AC-R05-11-03 | FR-R05-11 | Integration test: new queue entry, assert appears in QA reviewer queue | ✓ Observable: new row in queue; Search for: entry not visible |
| AC-R05-11-04 | FR-R05-11 | Error injection: mock invalid protocol_id, assert R06 error toast | ✓ Observable: error toast; ✓ States: error; Search for: silent failure, lost exam |
| AC-R05-11-05 | FR-R05-11 | DB query: assert audit log entry after queue creation | ✓ Observable: audit entry present; Search for: missing audit entry |
| AC-R05-12-01 | FR-R05-12 | Integration test: log incident (positioning), assert R06 notification | ✓ Observable: R06 notification; Search for: no notification for positioning incident |
| AC-R05-12-02 | FR-R05-12 | Playwright: assert notification badge on R06 sidebar | ✓ Observable: badge count; Search for: missing badge |
| AC-R05-12-03 | FR-R05-12 | Playwright: click notification, assert navigation to incident page | ✓ Observable: navigation + highlight; Search for: wrong page, no highlight |
| AC-R05-12-04 | FR-R05-12 | Integration test: log equipment_malfunction incident, assert NO R06 notification | ✓ Observable: no notification; Search for: notification sent for equipment incident |
| AC-R05-12-05 | NFR-R05-06 | ARIA test: assert live region announces notification | ✓ Observable: announcement; ✓ A11y: assertive live region; Search for: no live region |
| AC-R05-13-01 | FR-R05-13 | Playwright: assert Escalate button visible only for major/critical | ✓ Observable: button visible for major/critical, hidden for none/minor; Search for: button visible for minor |
| AC-R05-13-02 | FR-R05-13 | Playwright: click Escalate, assert confirmation dialog | ✓ Observable: dialog with text + Escalate/Cancel; Search for: no dialog, immediate escalation |
| AC-R05-13-03 | FR-R05-13 | Integration test: confirm escalation, assert corrective action created + R03 notified + R12 notified | ✓ Observable: corrective action + 2 notifications; Search for: missing notification, no corrective action |
| AC-R05-13-04 | FR-R05-13 | DB query: assert audit log entry after escalation | ✓ Observable: audit entry present; Search for: missing audit entry |
| AC-R05-13-05 | NFR-R05-06/10 | Keyboard test: focus trap + Escape + Enter on escalation dialog | ✓ Observable: focus trap + Escape cancels + Enter confirms; ✓ A11y; Search for: focus escape, wrong key behavior |