# User Stories — Radiology Technician (R07)

## US-R07-01: View and Monitor Modality Worklist
**Story**: As a R07 technician, I want to view my assigned worklist with auto-refresh so that I can see new exams as they are assigned without manually refreshing.
**Priority**: Must

### Acceptance Criteria
- **Given** I am logged in as a R07 technician, **when** I navigate to the worklist, **then** I observe a table of assigned exams with columns: Accession, Patient (initials), Modality (DR/CR/Fluoroscopy/Mammography), Protocol, Priority, Status. STAT rows have red left border (4px solid #EF4444), urgent rows have yellow left border (4px solid #F59E0B).
- **Given** the worklist is loaded, **when** 30 seconds pass, **then** I observe the worklist auto-refreshes with new exams (WebSocket push) and the last-updated timestamp updates.
- **Given** a STAT exam is assigned to me, **when** it appears in the worklist, **then** I observe an audio alert (with visual equivalent) and the STAT row has a pulsing red animation.
- **Given** I am using keyboard-only navigation, **when** I Tab through the worklist, **then** I observe all rows are focusable and Enter opens the exam detail.
- **Given** the worklist has 50+ exams, **when** I scroll, **then** I observe virtualization with smooth scrolling at 60fps.

### Dependencies
- FR-R07-01, NFR-R07-01, NFR-R07-06
- API: `GET /api/v2/worklists/technician`

---

## US-R07-02: Verify Patient Identity Before Exam
**Story**: As a R07 technician, I want to verify patient identity before starting an exam so that I prevent misidentification errors.
**Priority**: Must

### Acceptance Criteria
- **Given** I open an exam for preparation, **when** the exam detail panel loads, **then** I observe patient demographics: name initials, MRN last 4 digits, DOB, sex, and a "Confirm Patient" button.
- **Given** I click "Confirm Patient", **when** I confirm the identity, **then** I observe the exam status changes to "in_progress", the acquisition UI opens, and a green toast "Patient confirmed" appears.
- **Given** the patient has a prior study in the system, **when** I view the exam detail, **then** I observe a "Prior Study" indicator with a comparison link to the prior study.
- **Given** I am using keyboard-only navigation, **when** I Tab to "Confirm Patient" and press Enter, **then** I observe the confirmation is processed and the acquisition UI opens.
- **Given** the patient demographics do not match what I expected, **when** I click "Swap Patient", **then** I observe a patient search modal opens for me to re-search.

### Dependencies
- FR-R07-02, NFR-R07-07
- API: `POST /api/v2/exams/{id}/confirm-patient`

---

## US-R07-03: Review and Confirm Protocol Before Acquisition
**Story**: As a R07 technician, I want to review the assigned protocol parameters before starting acquisition so that I can confirm they are correct for the patient.
**Priority**: Must

### Acceptance Criteria
- **Given** I have confirmed the patient, **when** the protocol panel opens, **then** I observe: protocol name, required views (AP/PA/Lateral/Oblique for DR/CR, CC/MLO for Mammography), exposure parameters (kVp, mAs, SID, grid), and a "Start Protocol" button.
- **Given** the protocol parameters conflict with patient safety (e.g., contrast allergy for fluoroscopy), **when** the protocol panel renders, **then** I observe a red warning banner "CONTRAST ALLERGY: {allergy_description}" with the protocol parameters highlighted in yellow.
- **Given** I click "Start Protocol", **when** the protocol starts, **then** I observe the acquisition UI opens with the first view ready, and a green toast "Protocol started" appears.
- **Given** I am using keyboard-only navigation, **when** I Tab to "Start Protocol" and press Enter, **when** the protocol starts.

### Dependencies
- FR-R07-03, NFR-R07-07
- API: `GET /api/v2/exams/{id}/protocol`

---

## US-R07-04: Acquire Images and Perform Real-Time QA
**Story**: As a R07 technician, I want to acquire images with real-time quality assurance so that I can flag poor-quality images for retake before the exam is complete.
**Priority**: Must

### Acceptance Criteria
- **Given** I have started the protocol, **when** images are acquired, **then** I observe real-time image preview with QA overlay showing exposure indicator, positioning indicator, and artifact detection flags.
- **Given** I review an acquired image and it has a quality issue, **when** I click "Reject", **then** I observe a reject reason dropdown (motion, artifact, positioning, exposure, collimation, grid_error, other) and a description textarea, and on submit, a red alert "Image rejected — reason: {reason}" appears with a re-acquire prompt.
- **Given** I accept an image, **when** I click "Accept", **then** I observe the image moves to the accepted section and the next image is ready for review.
- **Given** I have rejected 3 or more images in a single acquisition, **when** the 3rd rejection occurs, **then** I observe a warning "High reject rate — consider repositioning the patient" with a "Reposition" button.
- **Given** I am using keyboard-only navigation, **when** I press 'A' key, **then** I observe the image is accepted; pressing 'R' key opens the reject modal.

### Dependencies
- FR-R07-04, NFR-R07-02, NFR-R07-05, NFR-R07-08
- API: `POST /api/v2/exams/{id}/acquire`, `POST /api/v2/exams/{id}/reject`

---

## US-R07-05: Monitor and Document Dose Parameters
**Story**: As a R07 technician, I want to automatically log dose parameters and monitor cumulative patient dose so that I comply with ALARA principles and regulatory requirements.
**Priority**: Must

### Acceptance Criteria
- **Given** I am acquiring images, **when** each image is acquired, **then** I observe the dose panel updates with DAP, DLP (where applicable), kVp, mAs, SID, and exposure time for that acquisition.
- **Given** I view the dose panel, **when** the panel renders, **then** I observe the cumulative dose for the patient across all studies in the current encounter, displayed prominently.
- **Given** the cumulative dose approaches the protocol ACR benchmark (≥80%), **when** the dose panel updates, **then** I observe a yellow warning banner "Cumulative dose approaching ACR benchmark".
- **Given** the cumulative dose exceeds the protocol ACR benchmark, **when** the dose panel updates, **then** I observe a red alert "Dose limit exceeded — consult R05 QA" and the exam is flagged for QA review.
- **Given** dose data is missing from the DICOM header, **when** the dose panel renders, **then** I observe a "Dose not recorded" warning and allow manual entry.

### Dependencies
- FR-R07-05, NFR-R07-04
- API: `GET /api/v2/exams/{id}/dose-baseline`, `POST /api/v2/exams/{id}/dose-log`

---

## US-R07-06: Perform Patient Safety Checks Before Contrast
**Story**: As a R07 technician, I want to perform patient safety checks before contrast administration (fluoroscopy) so that I prevent adverse reactions.
**Priority**: Must

### Acceptance Criteria
- **Given** I am about to administer contrast (fluoroscopy exam), **when** the safety check panel opens, **then** I observe: patient allergy/contrast reaction history prominently displayed, "No known allergies" confirmation checkbox, and "Proceed with Contrast" primary button.
- **Given** the patient has a known contrast allergy, **when** the safety check panel renders, **then** I observe a red warning banner "CONTRAST ALLERGY: {allergy_description} — Severity: {severity}" with the "Proceed with Contrast" button disabled until I document the allergy and provide a justification.
- **Given** the patient is flagged as pregnant, **when** the safety check panel renders, **then** I observe a radiation warning banner "Pregnancy confirmed — radiation risk applies" with a "Confirm Proceed" checkbox and "I understand the risks" acknowledgment text.
- **Given** I confirm "No known allergies" and proceed, **when** I click "Proceed with Contrast", **then** I observe the contrast administration begins and the safety check is logged in the audit trail.
- **Given** the EMR feed is down and allergy data is unavailable, **when** the safety check panel renders, **then** I observe a "Allergy data unavailable — please verify manually" warning and the manual entry fields are enabled.

### Dependencies
- FR-R07-06, NFR-R07-07
- API: `POST /api/v2/exams/{id}/safety-check`

---

## US-R07-07: Complete Exam and Hand Off to Radiologist
**Story**: As a R07 technician, I want to mark an exam as complete so that the radiologist is notified and images are pushed to PACS.
**Priority**: Must

### Acceptance Criteria
- **Given** I have completed image acquisition, **when** I click "Complete Exam", **then** I observe: (1) a completion summary showing dose data, view compliance, and reject count, (2) "Complete Exam" primary button and "Cancel" secondary button, (3) all required fields must be filled before the button is enabled.
- **Given** I click "Complete Exam", **when** the completion is processed, **then** I observe: (1) exam status changes to "complete" in the worklist, (2) a green toast "Exam complete — radiologist notified" appears, (3) images are pushed to PACS archive (shown as "Archiving..." progress), (4) radiologist worklist is updated within 5s.
- **Given** required fields (dose data, view compliance) are incomplete, **when** I click "Complete Exam", **then** I observe a validation error highlighting the missing fields and the exam is not marked complete.
- **Given** PACS push fails, **when** the retry is triggered, **then** I observe a "Images pending archive" banner with retry status and the exam is still marked complete.

### Dependencies
- FR-R07-07, NFR-R07-03, NFR-R07-05
- API: `POST /api/v2/exams/{id}/complete`

---

## US-R07-08: Log Retakes and Incidents
**Story**: As a R07 technician, I want to log image rejections and incidents so that they are recorded for QA analysis and medico-legal documentation.
**Priority**: Must

### Acceptance Criteria
- **Given** I have rejected an image, **when** I fill in the reject reason and description and submit, **then** I observe: (1) the rejection is recorded with timestamp, (2) the image is marked as rejected in the QA panel, (3) the reject count increments, (4) a confirmation toast "Rejection logged" appears.
- **Given** I need to log an incident (equipment malfunction, contrast reaction), **when** I click "Log Incident", **then** I observe a modal with: incident type dropdown (positioning, artifact, protocol_deviation, patient_motion, equipment_malfunction, contrast_extravasation), description textarea, severity selector (low/medium/high/critical), and "Submit" button.
- **Given** I submit an incident with severity=high or critical, **when** the submission completes, **then** I observe: (1) R05 QA team receives a notification, (2) if severity=critical, R12 radiologist also receives a notification, (3) the incident appears in the audit trail.
- **Given** I am using keyboard-only navigation, **when** I Tab to "Log Incident" and press Enter, **then** I observe the incident modal opens and I can navigate all fields with Tab.

### Dependencies
- FR-R07-08, NFR-R07-07
- API: `POST /api/v2/exams/{id}/reject`, `POST /api/v2/exams/{id}/incident`

---

## US-R07-09: Use Fluoroscopy-Specific Acquisition Workflow
**Story**: As a R07 technician, I want a fluoroscopy-specific acquisition workflow so that I can perform fluoroscopy exams with live imaging, spot capture, and dose tracking.
**Priority**: Should

### Acceptance Criteria
- **Given** I am performing a Fluoroscopy exam, **when** I start the acquisition, **then** I observe the fluoroscopy workflow: live fluoroscopy mode with continuous imaging, spot image capture button, cine recording button, and DAP cumulative dose tracker.
- **Given** I am in live fluoroscopy mode, **when** I capture a spot image, **then** I observe the spot image appears in the preview panel with a "Spot" label and the DAP dose is recorded for that frame.
- **Given** I start a cine recording, **when** I click "Start Cine", **then** I observe the cine recording indicator (red dot) and the frame counter increments in real-time.
- **Given** I stop the cine recording, **when** I click "Stop Cine", **then** I observe the cine clip is saved and the DAP cumulative dose is updated.
- **Given** the cumulative DAP exceeds the protocol ACR benchmark, **when** the dose panel updates, **then** I observe a red alert "Dose limit exceeded — consult R05 QA".

### Dependencies
- FR-R07-09, NFR-R07-05
- API: `POST /api/v2/exams/{id}/fluoroscopy-start`, `POST /api/v2/exams/{id}/spot-capture`, `POST /api/v2/exams/{id}/cine-start`, `POST /api/v2/exams/{id}/cine-stop`

---

## US-R07-10: Use Mammography-Specific Acquisition Workflow
**Story**: As a R07 technician, I want a mammography-specific acquisition workflow so that I can perform CC and MLO views with compression monitoring and ACR-compliant dose tracking.
**Priority**: Should

### Acceptance Criteria
- **Given** I am performing a Mammography exam, **when** I start the acquisition, **then** I observe the mammography workflow: CC view selection, MLO view selection, compression monitoring with real-time pressure display, and exposure parameter auto-calculation based on breast thickness and composition.
- **Given** I select the CC view, **when** I start acquisition, **then** I observe the CC-specific parameters (compression force, breast thickness, ACR view type) displayed on the protocol panel.
- **Given** I select the MLO view, **when** I start acquisition, **then** I observe the MLO-specific parameters (compression force, breast thickness, ACR view type) displayed on the protocol panel.
- **Given** the compression pressure exceeds the safe threshold, **when** the protocol panel updates, **then** I observe a warning "Compression pressure approaching limit — reduce compression" with the current pressure value highlighted in yellow.
- **Given** the exam is complete, **when** I view the dose panel, **then** I observe the average glandular dose (AGD) displayed per ACR standards.

### Dependencies
- FR-R07-10, NFR-R07-05
- API: `GET /api/v2/exams/{id}/protocol` (returns mammography-specific workflow template)