# User Stories — Radiology Technologist (R06)

## US-R06-01: View and Monitor Modality Worklist
**Story**: As a R06 technologist, I want to view my assigned worklist with auto-refresh so that I can see new exams as they are assigned without manually refreshing.
**Priority**: Must

### Acceptance Criteria
- **Given** I am logged in as a R06 technologist, **when** I navigate to the worklist, **then** I observe a table of assigned exams with columns: Accession, Patient (initials), Modality, Protocol, Priority, Status. STAT rows have red left border (4px solid #EF4444), urgent rows have yellow left border (4px solid #F59E0B).
- **Given** the worklist is loaded, **when** 30 seconds pass, **then** I observe the worklist auto-refreshes with new exams (WebSocket push) and the last-updated timestamp updates.
- **Given** a STAT exam is assigned to me, **when** it appears in the worklist, **then** I observe an audio alert (with visual equivalent) and the STAT row has a pulsing red animation.
- **Given** I am using keyboard-only navigation, **when** I Tab through the worklist, **then** I observe all rows are focusable and Enter opens the exam detail.
- **Given** the worklist has 50+ exams, **when** I scroll, **then** I observe virtualization with smooth scrolling at 60fps.

### Dependencies
- FR-R06-01, NFR-R06-01, NFR-R06-06
- API: `GET /api/v2/worklists/technologist`

---

## US-R06-02: Verify Patient Identity Before Exam
**Story**: As a R06 technologist, I want to verify patient identity before starting an exam so that I prevent misidentification errors.
**Priority**: Must

### Acceptance Criteria
- **Given** I open an exam for preparation, **when** the exam detail panel loads, **then** I observe patient demographics: name initials, MRN last 4 digits, DOB, sex, and a "Confirm Patient" button.
- **Given** I click "Confirm Patient", **when** I confirm the identity, **then** I observe the exam status changes to "in_progress", the acquisition UI opens, and a green toast "Patient confirmed" appears.
- **Given** the patient has a prior study in the system, **when** I view the exam detail, **then** I observe a "Prior Study" indicator with a comparison link to the prior study.
- **Given** I am using keyboard-only navigation, **when** I Tab to "Confirm Patient" and press Enter, **then** I observe the confirmation is processed and the acquisition UI opens.
- **Given** the patient demographics do not match what I expected, **when** I click "Swap Patient", **then** I observe a patient search modal opens for me to re-search.

### Dependencies
- FR-R06-02, NFR-R06-07
- API: `POST /api/v2/exams/{id}/confirm-patient`

---

## US-R06-03: Review and Confirm Protocol Before Acquisition
**Story**: As a R06 technologist, I want to review the assigned protocol parameters before starting acquisition so that I can confirm they are correct for the patient.
**Priority**: Must

### Acceptance Criteria
- **Given** I have confirmed the patient, **when** the protocol panel opens, **then** I observe: protocol name, required sequences list with parameters (kVp, mAs, slice thickness, contrast), body position instructions, and a "Start Protocol" button.
- **Given** the protocol parameters conflict with patient safety (e.g., contrast allergy), **when** the protocol panel renders, **then** I observe a red warning banner "CONTRAST ALLERGY: {allergy_description}" with the protocol parameters highlighted in yellow.
- **Given** I click "Start Protocol", **when** the protocol starts, **then** I observe the acquisition UI opens with the first sequence ready, and a green toast "Protocol started" appears.
- **Given** I am using keyboard-only navigation, **when** I Tab to "Start Protocol" and press Enter, **when** the protocol starts.

### Dependencies
- FR-R06-03, NFR-R06-07
- API: `GET /api/v2/exams/{id}/protocol`

---

## US-R06-04: Acquire Images and Perform Real-Time QA
**Story**: As a R06 technologist, I want to acquire images with real-time quality assurance so that I can flag poor-quality images for retake before the exam is complete.
**Priority**: Must

### Acceptance Criteria
- **Given** I have started the protocol, **when** images are acquired, **then** I observe real-time image preview with QA overlay showing signal-to-noise indicator, contrast indicator, and artifact detection flags.
- **Given** I review an acquired image and it has a quality issue, **when** I click "Reject", **then** I observe a reject reason dropdown (motion, artifact, positioning, exposure, patient_movement, equipment_malfunction, other) and a description textarea, and on submit, a red alert "Image rejected — reason: {reason}" appears with a re-acquire prompt.
- **Given** I accept an image, **when** I click "Accept", **then** I observe the image moves to the accepted section and the next image is ready for review.
- **Given** I have rejected 3 or more images in a single acquisition, **when** the 3rd rejection occurs, **then** I observe a warning "High reject rate — consider repositioning the patient" with a "Reposition" button.
- **Given** I am using keyboard-only navigation, **when** I press 'A' key, **then** I observe the image is accepted; pressing 'R' key opens the reject modal.

### Dependencies
- FR-R06-04, NFR-R06-02, NFR-R06-05, NFR-R06-08
- API: `POST /api/v2/exams/{id}/acquire`, `POST /api/v2/exams/{id}/reject`

---

## US-R06-05: Monitor and Document Dose Parameters
**Story**: As a R06 technologist, I want to automatically log dose parameters and monitor cumulative patient dose so that I comply with ALARA principles and regulatory requirements.
**Priority**: Must

### Acceptance Criteria
- **Given** I am acquiring images, **when** each image is acquired, **then** I observe the dose panel updates with DLP, CTDIvol, kVp, mAs, and exposure time for that acquisition.
- **Given** I view the dose panel, **when** the panel renders, **then** I observe the cumulative dose for the patient across all studies in the current encounter, displayed prominently.
- **Given** the cumulative dose approaches the protocol ACR benchmark (≥80%), **when** the dose panel updates, **then** I observe a yellow warning banner "Cumulative dose approaching ACR benchmark".
- **Given** the cumulative dose exceeds the protocol ACR benchmark, **when** the dose panel updates, **then** I observe a red alert "Dose limit exceeded — consult R05 QA" and the exam is flagged for QA review.
- **Given** dose data is missing from the DICOM header, **when** the dose panel renders, **then** I observe a "Dose not recorded" warning and allow manual entry.

### Dependencies
- FR-R06-05, NFR-R06-04
- API: `GET /api/v2/exams/{id}/dose-baseline`, `POST /api/v2/exams/{id}/dose-log`

---

## US-R06-06: Perform Patient Safety Checks Before Contrast
**Story**: As a R06 technologist, I want to perform patient safety checks before contrast administration so that I prevent adverse reactions.
**Priority**: Must

### Acceptance Criteria
- **Given** I am about to administer contrast, **when** the safety check panel opens, **then** I observe: patient allergy/contrast reaction history prominently displayed, "No known allergies" confirmation checkbox, and "Proceed with Contrast" primary button.
- **Given** the patient has a known contrast allergy, **when** the safety check panel renders, **then** I observe a red warning banner "Allergy: {allergy_description} — Severity: {severity}" with the "Proceed with Contrast" button disabled until I document the allergy and provide a justification.
- **Given** the patient is flagged as pregnant, **when** the safety check panel renders, **then** I observe a radiation warning banner "Pregnancy confirmed — radiation risk applies" with a "Confirm Proceed" checkbox and "I understand the risks" acknowledgment text.
- **Given** I confirm "No known allergies" and proceed, **when** I click "Proceed with Contrast", **then** I observe the contrast administration begins and the safety check is logged in the audit trail.
- **Given** the EMR feed is down and allergy data is unavailable, **when** the safety check panel renders, **then** I observe a "Allergy data unavailable — please verify manually" warning and the manual entry fields are enabled.

### Dependencies
- FR-R06-06, NFR-R06-07
- API: `POST /api/v2/exams/{id}/safety-check`

---

## US-R06-07: Complete Exam and Hand Off to Radiologist
**Story**: As a R06 technologist, I want to mark an exam as complete so that the radiologist is notified and images are pushed to PACS.
**Priority**: Must

### Acceptance Criteria
- **Given** I have completed image acquisition, **when** I click "Complete Exam", **then** I observe: (1) a completion summary showing dose data, sequence compliance, and reject count, (2) "Complete Exam" primary button and "Cancel" secondary button, (3) all required fields must be filled before the button is enabled.
- **Given** I click "Complete Exam", **when** the completion is processed, **then** I observe: (1) exam status changes to "complete" in the worklist, (2) a green toast "Exam complete — radiologist notified" appears, (3) images are pushed to PACS archive (shown as "Archiving..." progress), (4) radiologist worklist is updated within 5s.
- **Given** required fields (dose data, sequence compliance) are incomplete, **when** I click "Complete Exam", **then** I observe a validation error highlighting the missing fields and the exam is not marked complete.
- **Given** PACS push fails, **when** the retry is triggered, **then** I observe a "Images pending archive" banner with retry status and the exam is still marked complete.

### Dependencies
- FR-R06-07, NFR-R06-03, NFR-R06-05
- API: `POST /api/v2/exams/{id}/complete`

---

## US-R06-08: Log Retakes and Incidents
**Story**: As a R06 technologist, I want to log image rejections and incidents so that they are recorded for QA analysis and medico-legal documentation.
**Priority**: Must

### Acceptance Criteria
- **Given** I have rejected an image, **when** I fill in the reject reason and description and submit, **then** I observe: (1) the rejection is recorded with timestamp, (2) the image is marked as rejected in the QA panel, (3) the reject count increments, (4) a confirmation toast "Rejection logged" appears.
- **Given** I need to log an incident (equipment malfunction, contrast reaction), **when** I click "Log Incident", **then** I observe a modal with: incident type dropdown (positioning, artifact, protocol_deviation, patient_motion, equipment_malfunction, contrast_extravasation), description textarea, severity selector (low/medium/high/critical), and "Submit" button.
- **Given** I submit an incident with severity=high or critical, **when** the submission completes, **then** I observe: (1) R05 QA team receives a notification, (2) if severity=critical, R12 radiologist also receives a notification, (3) the incident appears in the audit trail.
- **Given** I am using keyboard-only navigation, **when** I Tab to "Log Incident" and press Enter, **then** I observe the incident modal opens and I can navigate all fields with Tab.

### Dependencies
- FR-R06-08, NFR-R06-07
- API: `POST /api/v2/exams/{id}/reject`, `POST /api/v2/exams/{id}/incident`

---

## US-R06-09: Override Protocol in Emergency
**Story**: As a R06 technologist, I want to override standard protocol parameters in emergency situations so that I can prioritize speed over completeness when clinically necessary.
**Priority**: Should

### Acceptance Criteria
- **Given** I am in an emergency situation (STAT exam, trauma), **when** I click "Emergency Override" in the protocol panel, **then** I observe a justification textarea (required, max 500 chars) and a "Confirm Override" button.
- **Given** I have entered a justification and confirmed the override, **when** the override is processed, **then** I observe: (1) protocol parameters are updated to the overridden values, (2) a yellow banner "Protocol overridden — justification logged" appears, (3) the override is recorded in the audit trail with timestamp, justification, and technologist ID.
- **Given** I have not entered a justification, **when** I try to confirm the override, **then** I observe a validation error "Justification is required for protocol override" and the override is not applied.
- **Given** the override is logged, **when** I view the audit trail, **then** I observe the override entry with all details (original params, overridden params, justification, timestamp).

### Dependencies
- FR-R06-09
- API: `POST /api/v2/exams/{id}/override-protocol`

---

## US-R06-10: Use Modality-Specific Acquisition Workflows
**Story**: As a R06 technologist, I want modality-specific acquisition workflows so that I can follow the correct protocol for each imaging modality.
**Priority**: Must

### Acceptance Criteria
- **Given** I am performing a CT exam, **when** I start the acquisition, **then** I observe the CT workflow: localizer → contrast (if ordered) → diagnostic series, with modality-specific parameters (kVp, mAs, slice thickness, pitch).
- **Given** I am performing an MRI exam, **when** I start the acquisition, **then** I observe the MRI workflow: localizer → sequence list with parameters (TR, TE, flip angle, slice thickness), with each sequence as a collapsible section.
- **Given** I am performing a PET exam, **when** I start the acquisition, **then** I observe the PET workflow: dose calibration → uptake period timer → acquisition, with uptake time tracking.
- **Given** I am performing an Ultrasound exam, **when** I start the acquisition, **then** I observe real-time capture with annotation capability and freeze/measure tools.
- **Given** I am performing a Mammography exam, **when** I start the acquisition, **then** I observe CC and MLO view workflows with compression monitoring and dose tracking per view.
- **Given** I switch between modalities, **when** I start a new exam, **then** I observe the correct workflow template loads based on the modality.

### Dependencies
- FR-R06-10
- API: `GET /api/v2/exams/{id}/protocol` (returns modality-specific workflow template)