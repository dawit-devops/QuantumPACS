# User Stories — Radiology Trainee/Resident (R13)

## US-R13-01: View and Monitor Supervised Reading Worklist
**Story**: As a R13 resident, I want to view my supervised reading worklist with attending assignments so that I know which studies to interpret and who my supervising attending is.
**Priority**: Must

### Acceptance Criteria
- **Given** I am logged in as a R13 resident, **when** I navigate to the worklist, **then** I observe a table of assigned studies with columns: Accession, Patient (initials), Modality, Protocol, Priority, Assigned Attending, Status. STAT rows have red left border (4px solid #EF4444).
- **Given** the worklist is loaded, **when** 30 seconds pass, **then** I observe the worklist auto-refreshes with new studies (WebSocket push) and the last-updated timestamp updates.
- **Given** a STAT study is assigned to me, **when** it appears in the worklist, **then** I observe an audio alert (with visual equivalent) and the STAT row has a pulsing red animation.
- **Given** I am using keyboard-only navigation, **when** I Tab through the worklist, **then** I observe all rows are focusable and Enter opens the supervised study view.
- **Given** the worklist has 50+ studies, **when** I scroll, **then** I observe virtualization with smooth scrolling at 60fps.

### Dependencies
- FR-R13-01, NFR-R13-01, NFR-R13-06
- API: `GET /api/v2/worklists/resident`

---

## US-R13-02: Interpret Study with Attending Guidance
**Story**: As a R13 resident, I want to interpret a study with attending guidance visible so that I can learn from the attending's expertise while developing my own interpretive skills.
**Priority**: Must

### Acceptance Criteria
- **Given** I open a study for interpretation, **when** the supervised viewer loads, **then** I observe a split-screen view: DICOM viewer on the left, attending guidance panel on the right with the attending's preliminary notes and suggested areas of focus.
- **Given** the attending adds guidance while I am interpreting, **when** the guidance is updated, **then** I observe the attending guidance panel updates in real-time (WebSocket push) with a subtle "Updated" indicator.
- **Given** I want to focus on my own interpretation, **when** I click "Toggle Guidance", **then** I observe the attending guidance panel collapses/expands and the viewer resizes accordingly.
- **Given** I am using keyboard-only navigation, **when** I press 'G' key, **then** I observe the guidance panel toggles.
- **Given** no attending guidance is available, **when** the viewer loads, **then** I observe a placeholder "Attending guidance not yet available — proceed with independent interpretation" and I can still interpret the study.

### Dependencies
- FR-R13-02, NFR-R13-08
- API: `GET /api/v2/studies/{id}/supervised`, WebSocket for guidance updates

---

## US-R13-03: Create and Submit Draft Report
**Story**: As a R13 resident, I want to create a structured draft report with auto-save so that I can focus on content without worrying about losing work.
**Priority**: Must

### Acceptance Criteria
- **Given** I am in the supervised viewer, **when** I click "Create Draft Report", **then** I observe a structured report editor with sections: Findings, Impression, Recommendations, each with a word count and completeness indicator.
- **Given** I am writing the draft report, **when** I pause typing for 10 seconds, **then** I observe an auto-save indicator "Saving..." → "Saved 2s ago" with green checkmark, and the draft is persisted to the backend.
- **Given** I have completed the draft report, **when** I click "Submit for Attending Review", **then** I observe: (1) the report status changes to "Submitted", (2) a green toast "Draft submitted for attending review" appears, (3) the report is locked from further editing, (4) the attending receives a notification within 5s.
- **Given** the attending returns the draft for revision, **when** I open the report, **then** I observe attending feedback highlighted inline with revision status, and the report is unlocked for editing.
- **Given** I am using keyboard-only navigation, **when** I press Ctrl+S, **then** I observe the draft is manually saved.

### Dependencies
- FR-R13-03, NFR-R13-02, NFR-R13-10
- API: `POST /api/v2/reports/draft`, `PUT /api/v2/reports/draft/{id}`, `POST /api/v2/reports/draft/{id}/submit`

---

## US-R13-04: Attending Review and Co-Sign Workflow
**Story**: As a R12 attending, I want to review resident draft reports side-by-side with the final report so that I can provide targeted feedback and efficiently co-sign.
**Priority**: Must

### Acceptance Criteria
- **Given** I am an attending with resident drafts pending, **when** I open my review queue, **then** I observe a list of submitted drafts with: study accession, resident name, modality, submission time, and "Review" button.
- **Given** I click "Review" on a draft, **when** the review view opens, **then** I observe a side-by-side comparison: resident's draft findings on the left, my final report editor on the right, with inline comment capability on the resident's text.
- **Given** I have reviewed the draft, **when** I click "Approve & Co-sign", **then** I observe: (1) the report status changes to "Final", (2) my digital signature is appended, (3) the draft is removed from my queue, (4) the resident receives "Report approved" notification.
- **Given** I identify issues requiring revision, **when** I click "Return for Revision", **then** I observe a feedback modal where I can select specific sections, add comments, and the resident receives the feedback with the draft unlocked for editing.
- **Given** I am using keyboard-only navigation, **when** I Tab through the review view, **then** I observe all interactive elements are reachable and operable.

### Dependencies
- FR-R13-04, NFR-R13-03
- API: `GET /api/v2/attending/review-queue`, `POST /api/v2/reports/draft/{id}/approve`, `POST /api/v2/reports/draft/{id}/return`

---

## US-R13-05: Capture Teaching Cases
**Story**: As a R13 resident, I want to capture teaching cases from studies I've interpreted so that I can build my educational portfolio and contribute to the departmental teaching library.
**Priority**: Must

### Acceptance Criteria
- **Given** I have completed a study interpretation, **when** I click "Capture Teaching Case", **then** I observe a teaching file editor pre-populated with: key images (from the study), my draft findings, attending's feedback, and a diagnosis field.
- **Given** I select key images for the teaching case, **when** I click images from the thumbnail strip, **then** I observe the selected images are added to the teaching case with a checkmark indicator, and I can reorder them.
- **Given** I add differential diagnosis, key learning points, and tags (anatomy, pathology, modality), **when** I click "Submit for Attending Approval", **then** I observe: (1) the teaching case status is "Pending Approval", (2) the attending receives a notification, (3) I cannot edit the case while pending.
- **Given** the attending approves the teaching case, **when** I view my teaching library, **then** I observe the case is published with a "Published" badge and is de-identified (no PHI in images or metadata).
- **Given** the attending requests changes, **when** I open the case, **then** I observe attending feedback and the case is unlocked for revision.

### Dependencies
- FR-R13-05, NFR-R13-04
- API: `POST /api/v2/teaching-files`, `POST /api/v2/teaching-files/{id}/approve`

---

## US-R13-06: Manage Personal Exam List and Export Portfolio
**Story**: As a R13 resident, I want to view my personal exam log with filtering and export it for my residency program portfolio so that I can track my educational progress.
**Priority**: Must

### Acceptance Criteria
- **Given** I navigate to the Exam List view, **when** the list loads, **then** I observe a filterable, paginated table of all studies I've interpreted with columns: Date, Accession, Modality, Body Part, Diagnosis, Attending, Review Status, Interpretation Time.
- **Given** I apply filters (modality=CT, body_part=chest, date_range=last_month), **when** I click "Apply", **then** I observe the table updates with filtered results and the metrics summary updates (total studies, avg interpretation time, attending agreement rate).
- **Given** I click "Export CSV", **when** the export completes, **then** I observe a CSV download with columns matching residency program requirements: date, accession, modality, body_part, diagnosis, attending, interpretation_time, draft_to_final_turnaround, revision_count.
- **Given** I am using keyboard-only navigation, **when** I Tab through the table, **then** I observe all rows are focusable and filter controls are operable.

### Dependencies
- FR-R13-06, NFR-R13-05
- API: `GET /api/v2/resident/{id}/exam-list`, `POST /api/v2/resident/{id}/exam-list/export`

---

## US-R13-07: View Performance Feedback Dashboard
**Story**: As a R13 resident, I want to see my performance metrics and attending feedback so that I can track my educational progress and identify areas for improvement.
**Priority**: Should

### Acceptance Criteria
- **Given** I open the Feedback Dashboard, **when** it loads, **then** I observe charts: studies interpreted by modality (bar chart), interpretation time trend (line chart), attending agreement rate (gauge), and feedback themes (word cloud or category breakdown).
- **Given** an attending adds private feedback on a study, **when** I open the Feedback Dashboard, **then** I observe the new feedback entry with: study accession, date, attending name, category (interpretation/technique/communication), and feedback text.
- **Given** I am on a tablet (768px viewport), **when** I view the dashboard, **then** I observe charts stack vertically and remain readable with touch-friendly interactions.
- **Given** I am the program director (R03), **when** I view a resident's dashboard, **then** I observe the same metrics plus aggregate cohort comparison (visible only to R03/R12).

### Dependencies
- FR-R13-07, NFR-R13-07
- API: `GET /api/v2/resident/{id}/feedback`

---

## US-R13-08: Request On-Call Attending Consult
**Story**: As a R13 resident on call, I want to request an attending consult for a difficult case so that I can get timely guidance and ensure patient safety.
**Priority**: Should

### Acceptance Criteria
- **Given** I am on call and encounter a difficult study, **when** I click "Request Attending Consult", **then** I observe a modal with: study selector (pre-filled with current study), urgency dropdown (routine/urgent/emergent), and a brief description textarea.
- **Given** I submit the consult request, **when** the request is sent, **then** I observe: (1) the on-call attending (R12 or R18) receives a priority notification, (2) a "Consult requested" banner appears with estimated response time, (3) I cannot submit another request for the same study.
- **Given** the attending accepts the consult, **when** they join, **then** I observe: (1) a screen-sharing session starts OR written guidance appears in the study viewer, (2) the consult status changes to "In Progress", (3) I can communicate with the attending via integrated chat.
- **Given** the attending provides guidance and closes the consult, **when** the consult ends, **then** I observe the guidance is saved to the study record and the consult status changes to "Completed".

### Dependencies
- FR-R13-08, NFR-R13-07
- API: `POST /api/v2/resident/{id}/consult-request`, `POST /api/v2/resident/{id}/consult-response`

---

## US-R13-09: Access Protocol Learning Annotations
**Story**: As a R13 resident, I want to see educational annotations on protocols so that I can understand the clinical reasoning behind each protocol.
**Priority**: Should

### Acceptance Criteria
- **Given** I am selecting a protocol for a study, **when** the protocol panel opens, **then** I observe educational annotations: clinical indication, key sequences and their purpose, common artifacts, normal variants, and red flags.
- **Given** I have reviewed the protocol annotations, **when** I click "Mark as Reviewed", **then** I observe the protocol is added to my "Reviewed Protocols" list with a completion timestamp.
- **Given** I want to track my protocol learning progress, **when** I open the Protocol Learning view, **then** I observe a progress tracker showing total protocols for my rotation, reviewed count, and percentage complete.
- **Given** the attending adds new educational content, **when** I view the protocol, **then** I observe the new content with a "New" badge and the completion percentage updates.

### Dependencies
- FR-R13-09
- API: `GET /api/v2/protocols/{id}/education`, `POST /api/v2/resident/{id}/protocol-reviewed`

---

## US-R13-10: Prepare Cases for Departmental Conference
**Story**: As a R13 resident, I want to tag studies for case conference presentation so that I can efficiently prepare educational materials.
**Priority**: Could

### Acceptance Criteria
- **Given** I have completed a study that would make a good teaching case, **when** I click "Tag for Case Conference", **then** I observe the study is added to my "Case Conference" list with a tag badge.
- **Given** I have tagged multiple studies, **when** I click "Generate Presentation", **then** I observe a presentation-ready export with: de-identified images, my draft findings, attending's final report, diagnosis, and discussion points for each case.
- **Given** the attending reviews my tagged cases, **when** they approve a case for conference, **then** I observe the case status changes to "Approved for Conference" and it is added to the departmental conference schedule.
- **Given** I export the presentation, **when** the export completes, **then** I observe a PDF/PowerPoint download with all tagged cases formatted for presentation.

### Dependencies
- FR-R13-10
- API: `POST /api/v2/resident/{id}/conference-tag`, `POST /api/v2/resident/{id}/conference-export`