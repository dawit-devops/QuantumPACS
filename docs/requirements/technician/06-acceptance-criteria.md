# Acceptance Criteria — Radiology Technician (R07)

**Role ID**: R07
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

## AC-R07-01: Worklist Display and Auto-Refresh

| AC ID | Links to | Criteria (Given/When/Then) | Verification Method | Validator Gate |
|-------|----------|----------------------------|---------------------|----------------|
| AC-R07-01-01 | FR-R07-01 | **Given** I am logged in as a R07 technician, **when** the worklist loads, **then** I observe a table of assigned exams with columns: Accession, Patient (initials), Modality (DR/CR/Fluoroscopy/Mammography), Protocol, Priority, Status. STAT rows have red left border (4px solid #EF4444), urgent rows have yellow left border (4px solid #F59E0B). | VE + AT | Screenshot shows all columns; priority badges and left borders applied correctly |
| AC-R07-01-02 | FR-R07-01 | **Given** the worklist is loaded, **when** 30 seconds pass, **then** I observe the worklist auto-refreshes with new exams (WebSocket push) and the last-updated timestamp updates. | AT + PM | Network log shows WebSocket message or polling request; timestamp updates within 30s |
| AC-R07-01-03 | FR-R07-01 | **Given** a STAT exam is assigned to me, **when** it appears in the worklist, **then** I observe an audio alert (with visual equivalent) and the STAT row has a pulsing red animation. | AT + VE | Audio element `play()` called; ARIA live region updated; pulsing animation verified via CSS |
| AC-R07-01-04 | FR-R07-01 | **Given** I am using keyboard-only navigation, **when** I Tab through the worklist, **then** I observe all rows are focusable and Enter opens the exam detail. | AT + MT | Playwright keyboard event simulation; Tab navigation works; Enter opens detail panel |
| AC-R07-01-05 | FR-R07-01, NFR-R07-01 | **Given** the worklist has 50+ exams, **when** I scroll, **then** I observe virtualization with smooth scrolling at 60fps and a loading indicator at the scroll position. | PM + AT | Frame timing measured at 60fps during scroll; loading indicator appears at scroll position |

**Validator Gate Verdict**: AC-R07-01 achieves acceptance criteria **only if** all columns render correctly, STAT rows are visually distinct, auto-refresh works within 30s, and virtualization maintains 60fps scroll performance.

---

## AC-R07-02: Patient Identity Verification

| AC ID | Links to | Criteria (Given/When/Then) | Verification Method | Validator Gate |
|-------|----------|----------------------------|---------------------|----------------|
| AC-R07-02-01 | FR-R07-02 | **Given** I open an exam for preparation, **when** the exam detail panel loads, **then** I observe patient demographics: name initials, MRN last 4 digits, DOB, sex, and a "Confirm Patient" button. | VE + AT | Screenshot shows all demographics; Confirm Patient button is present and labeled |
| AC-R07-02-02 | FR-R07-02 | **Given** I click "Confirm Patient", **when** the confirmation is processed, **then** I observe: exam status changes to "in_progress", the acquisition UI opens, and a green toast "Patient confirmed" appears. | AT + VE | API call `POST /api/v2/exams/{id}/confirm-patient` succeeds; toast renders with green background |
| AC-R07-02-03 | FR-R07-02 | **Given** the patient has a prior study in the system, **when** I view the exam detail, **then** I observe a "Prior Study" indicator with a comparison link to the prior study. | VE + AT | Prior study indicator rendered; comparison link navigates to prior study |
| AC-R07-02-04 | FR-R07-02 | **Given** I am using keyboard-only navigation, **when** I Tab to "Confirm Patient" and press Enter, **then** I observe the confirmation is processed and the acquisition UI opens. | AT + MT | Playwright keyboard event simulation; Enter key triggers confirmation |
| AC-R07-02-05 | FR-R07-02 | **Given** the patient demographics do not match what I expected, **when** I click "Swap Patient", **then** I observe a patient search modal opens for me to re-search. | VE + AT | Modal opens with patient search; search returns results; selection updates patient info |

**Validator Gate Verdict**: AC-R07-02 achieves acceptance criteria **only if** all demographics are displayed correctly, confirmation triggers the acquisition UI, prior study indicator is shown when applicable, and patient swap works via modal.

---

## AC-R07-03: Protocol Review Before Acquisition

| AC ID | Links to | Criteria (Given/When/Then) | Verification Method | Validator Gate |
|-------|----------|----------------------------|---------------------|----------------|
| AC-R07-03-01 | FR-R07-03 | **Given** I have confirmed the patient, **when** the protocol panel opens, **then** I observe: protocol name, required views (AP/PA/Lateral/Oblique for DR/CR, CC/MLO for Mammography), exposure parameters (kVp, mAs, SID, grid), and a "Start Protocol" button. | VE + AT | Screenshot shows protocol panel with all parameters; Start Protocol button present |
| AC-R07-03-02 | FR-R07-03 | **Given** the protocol parameters conflict with patient safety (e.g., contrast allergy for fluoroscopy), **when** the protocol panel renders, **then** I observe a red warning banner "CONTRAST ALLERGY: {allergy_description}" with the protocol parameters highlighted in yellow. | VE + AT | Red banner rendered with correct text; yellow highlight on conflicting parameters; contrast ≥4.5:1 |
| AC-R07-03-03 | FR-R07-03 | **Given** I click "Start Protocol", **when** the protocol starts, **then** I observe the acquisition UI opens with the first view ready and a green toast "Protocol started" appears. | AT + VE | API call succeeds; acquisition UI opens; toast renders with green background |
| AC-R07-03-04 | FR-R07-03 | **Given** I am using keyboard-only navigation, **when** I Tab to "Start Protocol" and press Enter, **when** the protocol starts. | AT + MT | Playwright keyboard event simulation; Enter key triggers protocol start |

**Validator Gate Verdict**: AC-R07-03 achieves acceptance criteria **only if** protocol parameters are displayed correctly, safety conflicts are flagged with red banners, and protocol start triggers the acquisition UI.

---

## AC-R07-04: Image Acquisition and Real-Time QA

| AC ID | Links to | Criteria (Given/When/Then) | Verification Method | Validator Gate |
|-------|----------|----------------------------|---------------------|----------------|
| AC-R07-04-01 | FR-R07-04 | **Given** I have started the protocol, **when** images are acquired, **then** I observe real-time image preview with QA overlay showing exposure indicator, positioning indicator, and artifact detection flags. | VE + AT | Screenshot shows image preview with QA overlay indicators |
| AC-R07-04-02 | FR-R07-04 | **Given** I review an acquired image and it has a quality issue, **when** I click "Reject", **then** I observe a reject reason dropdown (motion, artifact, positioning, exposure, collimation, grid_error, other) and a description textarea, and on submit, a red alert "Image rejected — reason: {reason}" appears with a re-acquire prompt. | VE + AT | Dropdown shows all reason codes; red alert renders with correct text; re-acquire prompt shown |
| AC-R07-04-03 | FR-R07-04 | **Given** I accept an image, **when** I click "Accept", **then** I observe the image moves to the accepted section and the next image is ready for review. | AT | Image moves to accepted section; next image loads in preview |
| AC-R07-04-04 | FR-R07-04, NFR-R07-08 | **Given** I have rejected 3 or more images in a single acquisition, **when** the 3rd rejection occurs, **then** I observe a warning "High reject rate — consider repositioning the patient" with a "Reposition" button. | AT + VE | Warning banner appears after 3rd rejection; Reposition button is functional |
| AC-R07-04-05 | FR-R07-04 | **Given** I am using keyboard-only navigation, **when** I press 'A' key, **then** I observe the image is accepted; pressing 'R' key opens the reject modal. | AT + MT | Playwright keyboard event simulation; 'A' accepts image; 'R' opens reject modal |

**Validator Gate Verdict**: AC-R07-04 achieves acceptance criteria **only if** QA overlay indicators are visible, reject workflow is functional with all reason codes, accept moves images correctly, high reject rate warning triggers at 3, and keyboard shortcuts work.

---

## AC-R07-05: Dose Documentation and Monitoring

| AC ID | Links to | Criteria (Given/When/Then) | Verification Method | Validator Gate |
|-------|----------|----------------------------|---------------------|----------------|
| AC-R07-05-01 | FR-R07-05 | **Given** I am acquiring images, **when** each image is acquired, **then** I observe the dose panel updates with DAP, DLP (where applicable), kVp, mAs, SID, and exposure time for that acquisition. | VE + AT | Dose panel values update per acquisition; all 6 parameters displayed |
| AC-R07-05-02 | FR-R07-05 | **Given** I view the dose panel, **when** the panel renders, **then** I observe the cumulative dose for the patient across all studies in the current encounter, displayed prominently. | VE + AT | Cumulative dose value displayed; matches DB query |
| AC-R07-05-03 | FR-R07-05 | **Given** the cumulative dose approaches the protocol ACR benchmark (≥80%), **when** the dose panel updates, **then** I observe a yellow warning banner "Cumulative dose approaching ACR benchmark". | VE + AT | Yellow banner rendered with correct text; contrast ≥4.5:1 |
| AC-R07-05-04 | FR-R07-05 | **Given** the cumulative dose exceeds the protocol ACR benchmark, **when** the dose panel updates, **then** I observe a red alert "Dose limit exceeded — consult R05 QA" and the exam is flagged for QA review. | VE + AL | Red alert rendered; exam flagged in database with `qa_flagged=true` |
| AC-R07-05-05 | FR-R07-05 | **Given** dose data is missing from the DICOM header, **when** the dose panel renders, **then** I observe a "Dose not recorded" warning and allow manual entry. | VE + AT | Warning banner rendered; manual entry fields enabled |

**Validator Gate Verdict**: AC-R07-05 achieves acceptance criteria **only if** dose parameters update per acquisition, cumulative dose is displayed, warnings trigger at correct thresholds, and missing dose data is handled gracefully.

---

## AC-R07-06: Patient Safety Checks Before Contrast

| AC ID | Links to | Criteria (Given/When/Then) | Verification Method | Validator Gate |
|-------|----------|----------------------------|---------------------|----------------|
| AC-R07-06-01 | FR-R07-06 | **Given** I am about to administer contrast (fluoroscopy exam), **when** the safety check panel opens, **then** I observe: patient allergy/contrast reaction history prominently displayed, "No known allergies" confirmation checkbox, and "Proceed with Contrast" primary button. | VE + AT | Screenshot shows safety check panel with all elements |
| AC-R07-06-02 | FR-R07-06 | **Given** the patient has a known contrast allergy, **when** the safety check panel renders, **then** I observe a red warning banner "CONTRAST ALLERGY: {allergy_description} — Severity: {severity}" with the "Proceed with Contrast" button disabled until I document the allergy and provide a justification. | VE + AT | Red banner rendered with correct text; Proceed button disabled; justification textarea enabled |
| AC-R07-06-03 | FR-R07-06 | **Given** the patient is flagged as pregnant, **when** the safety check panel renders, **then** I observe a radiation warning banner "Pregnancy confirmed — radiation risk applies" with a "Confirm Proceed" checkbox and "I understand the risks" acknowledgment text. | VE + AT | Radiation warning banner rendered; checkbox and acknowledgment text present |
| AC-R07-06-04 | FR-R07-06 | **Given** I confirm "No known allergies" and proceed, **when** I click "Proceed with Contrast", **then** I observe the contrast administration begins and the safety check is logged in the audit trail. | AT + AL | API call succeeds; audit log entry created with `action='safety_check_confirmed'` |
| AC-R07-06-05 | FR-R07-06 | **Given** the EMR feed is down and allergy data is unavailable, **when** the safety check panel renders, **then** I observe a "Allergy data unavailable — please verify manually" warning and the manual entry fields are enabled. | VE + AT | Warning banner rendered; manual entry fields enabled |

**Validator Gate Verdict**: AC-R07-06 achieves acceptance criteria **only if** safety checks are mandatory gates before contrast, allergy and pregnancy warnings are prominently displayed, and manual entry works when EMR data is unavailable.

---

## AC-R07-07: Exam Completion and Radiologist Handoff

| AC ID | Links to | Criteria (Given/When/Then) | Verification Method | Validator Gate |
|-------|----------|----------------------------|---------------------|----------------|
| AC-R07-07-01 | FR-R07-07 | **Given** I have completed image acquisition, **when** I click "Complete Exam", **then** I observe a completion summary showing dose data, view compliance, and reject count, with "Complete Exam" primary button and "Cancel" secondary button. | VE + AT | Completion summary panel renders with all 3 sections; both buttons present |
| AC-R07-07-02 | FR-R07-07 | **Given** I click "Complete Exam", **when** the completion is processed, **then** I observe: (1) exam status changes to "complete" in the worklist, (2) a green toast "Exam complete — radiologist notified" appears, (3) images are pushed to PACS archive (shown as "Archiving..." progress), (4) radiologist worklist is updated within 5s. | AT + PM + VE | API call succeeds; toast renders; PACS push progress shown; radiologist worklist updated within 5s |
| AC-R07-07-03 | FR-R07-07 | **Given** required fields (dose data, view compliance) are incomplete, **when** I click "Complete Exam", **then** I observe a validation error highlighting the missing fields and the exam is not marked complete. | VE + AT | Validation errors shown; exam status remains 'in_progress' |
| AC-R07-07-04 | FR-R07-07 | **Given** PACS push fails, **when** the retry is triggered, **then** I observe a "Images pending archive" banner with retry status and the exam is still marked complete. | VE + AT | Banner rendered; retry status shown; exam status is 'complete' despite PACS failure |

**Validator Gate Verdict**: AC-R07-07 achieves acceptance criteria **only if** completion summary is accurate, handoff notification reaches radiologist within 5s, validation prevents incomplete completion, and PACS push failures are handled gracefully.

---

## AC-R07-08: Retake and Incident Logging

| AC ID | Links to | Criteria (Given/When/Then) | Verification Method | Validator Gate |
|-------|----------|----------------------------|---------------------|----------------|
| AC-R07-08-01 | FR-R07-08 | **Given** I have rejected an image, **when** I fill in the reject reason and description and submit, **then** I observe: (1) the rejection is recorded with timestamp, (2) the image is marked as rejected in the QA panel, (3) the reject count increments, (4) a confirmation toast "Rejection logged" appears. | AT + VE | API call succeeds; QA panel shows rejected image; count increments; toast renders |
| AC-R07-08-02 | FR-R07-08 | **Given** I need to log an incident (equipment malfunction, contrast reaction), **when** I click "Log Incident", **then** I observe a modal with: incident type dropdown (positioning, artifact, protocol_deviation, patient_motion, equipment_malfunction, contrast_extravasation), description textarea, severity selector (low/medium/high/critical), and "Submit" button. | VE + AT | Modal opens with all fields; dropdown has all incident types; severity selector has all levels |
| AC-R07-08-03 | FR-R07-08 | **Given** I submit an incident with severity=high or critical, **when** the submission completes, **then** I observe: (1) R05 QA team receives a notification, (2) if severity=critical, R12 radiologist also receives a notification, (3) the incident appears in the audit trail. | AT + AL | API call succeeds; R05 notification sent; R12 notification sent if critical; audit log entry created |
| AC-R07-08-04 | FR-R07-08 | **Given** I am using keyboard-only navigation, **when** I Tab to "Log Incident" and press Enter, **then** I observe the incident modal opens and I can navigate all fields with Tab. | AT + MT | Playwright keyboard event simulation; modal opens; Tab navigation works |

**Validator Gate Verdict**: AC-R07-08 achieves acceptance criteria **only if** rejections are recorded with all required data, incident logging is functional with all incident types and severity levels, notifications are sent for high/critical incidents, and keyboard navigation works.

---

## AC-R07-09: Fluoroscopy-Specific Workflow

| AC ID | Links to | Criteria (Given/When/Then) | Verification Method | Validator Gate |
|-------|----------|----------------------------|---------------------|----------------|
| AC-R07-09-01 | FR-R07-09 | **Given** I am performing a Fluoroscopy exam, **when** I start the acquisition, **then** I observe the fluoroscopy workflow: live fluoroscopy mode with continuous imaging, spot image capture button, cine recording button, and DAP cumulative dose tracker. | VE + AT | Fluoroscopy workflow loads; live feed visible; spot/cine buttons present; DAP tracker visible |
| AC-R07-09-02 | FR-R07-09 | **Given** I am in live fluoroscopy mode, **when** I capture a spot image, **then** I observe the spot image appears in the preview panel with a "Spot" label and the DAP dose is recorded for that frame. | AT + VE | Spot image appears with "Spot" label; DAP dose recorded in dose panel |
| AC-R07-09-03 | FR-R07-09 | **Given** I start a cine recording, **when** I click "Start Cine", **then** I observe the cine recording indicator (red dot) and the frame counter increments in real-time. | AT + VE | Red dot indicator appears; frame counter increments; cine recording is functional |
| AC-R07-09-04 | FR-R07-09 | **Given** I stop the cine recording, **when** I click "Stop Cine", **then** I observe the cine clip is saved and the DAP cumulative dose is updated. | AT | Cine clip saved; DAP cumulative dose updated in dose panel |
| AC-R07-09-05 | FR-R07-09, NFR-R07-05 | **Given** the cumulative DAP exceeds the protocol ACR benchmark, **when** the dose panel updates, **then** I observe a red alert "Dose limit exceeded — consult R05 QA". | VE + AT | Red alert rendered; exam flagged for QA review |

**Validator Gate Verdict**: AC-R07-09 achieves acceptance criteria **only if** fluoroscopy workflow provides live imaging, spot capture, cine recording, and DAP tracking with correct dose limit alerts.

---

## AC-R07-10: Mammography-Specific Workflow

| AC ID | Links to | Criteria (Given/When/Then) | Verification Method | Validator Gate |
|-------|----------|----------------------------|---------------------|----------------|
| AC-R07-10-01 | FR-R07-10 | **Given** I am performing a Mammography exam, **when** I start the acquisition, **then** I observe the mammography workflow: CC and MLO view selection, compression monitoring with real-time pressure display, and exposure parameter auto-calculation based on breast thickness and composition. | VE + AT | Mammography workflow loads; CC/MLO view selector present; compression monitor visible |
| AC-R07-10-02 | FR-R07-10 | **Given** I select the CC view, **when** I start acquisition, **then** I observe the CC-specific parameters (compression force, breast thickness, ACR view type) displayed on the protocol panel. | VE + AT | CC-specific parameters displayed correctly on protocol panel |
| AC-R07-10-03 | FR-R07-10 | **Given** I select the MLO view, **when** I start acquisition, **then** I observe the MLO-specific parameters (compression force, breast thickness, ACR view type) displayed on the protocol panel. | VE + AT | MLO-specific parameters displayed correctly on protocol panel |
| AC-R07-10-04 | FR-R07-10 | **Given** the compression pressure exceeds the safe threshold, **when** the protocol panel updates, **then** I observe a warning "Compression pressure approaching limit — reduce compression" with the current pressure value highlighted in yellow. | VE + AT | Warning banner rendered; pressure value highlighted in yellow; contrast ≥4.5:1 |
| AC-R07-10-05 | FR-R07-10, NFR-R07-05 | **Given** the exam is complete, **when** I view the dose panel, **then** I observe the average glandular dose (AGD) displayed per ACR standards. | VE + AT | AGD value displayed; matches ACR calculation formula |

**Validator Gate Verdict**: AC-R07-10 achieves acceptance criteria **only if** mammography workflow provides CC/MLO view selection, compression monitoring with real-time pressure display, and ACR-compliant AGD dose tracking.

---

## Excluded Scope / Out of Scope

The following are explicitly **NOT** covered by these acceptance criteria and are out of scope for R07 Radiology Technician requirements:

### Out of Scope — Technical
1. **MRI/PET/CT/Ultrasound acquisition** (R06) — technician operates DR/CR/Fluoroscopy/Mammography only
2. **Patient registration** (R08) — technician does not register patients
3. **Scheduling** (R04) — coordinator schedules; technician executes
4. **QA protocol management** (R05) — separate role with its own requirements package
5. **DICOM image viewing/measurement tools for diagnostic interpretation** (R12/R18) — technician uses viewer for QA, not for diagnostic interpretation
6. **PACS archive management** (R01/R02) — backend handles PACS push; technician triggers it
7. **AI/CAD integration** (v3.2+ roadmap) — not in v3.0 scope
8. **Mobile native app** — PWA only; mobile view is responsive adaptation

### Out of Scope — Clinical
1. **Radiologist diagnostic interpretation** (R12/R18) — technician acquires images, radiologist interprets
2. **Contrast administration** — technician triggers, nurse (R11) administers
3. **Patient consent** — handled by registration (R08) and nursing (R11)
4. **Critical findings escalation** (R12/R18) — technician logs incidents; radiologist manages escalation
5. **Billing** (R09) — outside technician scope

### Out of Scope — Operational
1. **Shift handoff report** (R04) — coordinator generates; technician contributes data
2. **Utilization dashboard** (R04) — coordinator views; technician data feeds it
3. **Staffing roster** (R04) — coordinator manages; technician is assigned
4. **Audit log retention policy** (R01) — system manages retention; technician generates entries

---

## Quality Gate Summary

| Artifact | Completeness | Feasibility | Usability | Validator |
|----------|--------------|-------------|-----------|-----------|
| 01-user-requirements.md | ✅ All FR/NFR with IDs | ✅ Performance quantified | ✅ Error/empty states specified | ✅ 4 new APIs flagged |
| 02-workflow-maps.md | ✅ 5 workflows with Mermaid | ✅ All states (loading/error/success) | ✅ Friction points flagged | ✅ Integration touchpoints mapped |
| 03-user-stories.md | ✅ 10 stories with Given/When/Then | ✅ Dependencies listed | ✅ A11y + performance ACs | ✅ 4-phase priority order |
| 04-ui-ux-requirements.md | ✅ 8 screens, all 6 states per component | ✅ Tokens referenced | ✅ Keyboard nav specified | ✅ Contrast ratios measured |
| 05-metrics-slas.md | ✅ 10 metrics, 4 SLA tiers | ✅ Measurement method specified | ✅ Dashboards assigned | ✅ 3-tier SLA definitions |
| 06-acceptance-criteria.md | ✅ 10 AC groups, FR/NFR mapping | ✅ Verification methods (AT/VE/PM/AL) | ✅ Observable outcomes | ✅ Validator gate per AC group |

**Overall Verdict**: From the visual evidence, structured requirements, and measurable acceptance criteria, I observe the R07 Radiology Technician requirements package — **Goal ACHIEVED** with the following conditions:

1. **4 new API endpoints required** (flagged in FR-R07 requirements) — must be designed and implemented before R07 workflows functional.
2. **Cornerstone3D integration** — real-time image QA overlay requires Cornerstone3D event timing integration.
3. **DICOM header parsing** — dose data extraction from DICOM headers must be robust across all modalities.
4. **WebSocket push to radiologist** — critical path for exam completion handoff.
5. **PACS archive integration** — async image push with retry logic required.
6. **Fluoroscopy DAP tracking** — requires continuous dose monitoring during live fluoroscopy.
7. **Mammography AGD calculation** — requires ACR-compliant dose calculation per view.

**Next Steps**:
1. Delegate API contract design to `frontend-to-backend-requirements` skill
2. Delegate RESTful resource design to `rest-api-design` skill
3. Schedule stakeholder review with R07 radiology technicians
4. Prioritize Phase 1 user stories (US-R07-01, 02, 03, 04, 05) for MVP
5. Conduct usability testing with 2-3 radiology technicians before full implementation