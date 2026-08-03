# User Requirements — Radiology Technician (R07)

**Version**: 1.0.0 (v3.0 scope)
**Status**: Draft
**Date**: 2026-08-02

---

## Functional Requirements

| ID | Requirement | Priority | Notes |
|----|-------------|----------|-------|
| FR-R07-01 | **Modality Worklist**: Display a filtered, paginated worklist of assigned exams for the logged-in technician. Columns: Accession, Patient (initials), Modality (DR/CR/Fluoroscopy/Mammography), Protocol, Priority (STAT/urgent/routine), Status (pending/in-progress/completed). Auto-refresh every 30s via WebSocket. STAT exams highlighted with red left border. | Must | Extends existing worklist component with DR/CR/Fluoroscopy/Mammography-specific filtering |
| FR-R07-02 | **Patient Identity Verification**: Before starting an exam, the system SHALL display patient demographics (name initials, MRN last 4 digits, DOB, sex) and require the technician to verify identity via a "Confirm Patient" button. If the patient has a prior study in the system, display a "Prior Study" indicator with comparison link. | Must | Patient safety critical; prevents misidentification errors |
| FR-R07-03 | **Exam Protocol Selection**: Display the assigned protocol with required views (AP/PA/Lateral/Oblique for DR/CR, CC/MLO for Mammography, spot views for Fluoroscopy), exposure parameters (kVp, mAs, SID, grid), and positioning instructions. Allow the technician to confirm protocol start. | Must | Protocol data from `protocols` table; dynamic based on exam type |
| FR-R07-04 | **Image Acquisition and QA**: During image acquisition, display real-time image preview with quality indicators (exposure indicator, positioning indicator, artifact detection). Allow technician to flag images as "reject" with reason code (motion, artifact, positioning, exposure, collimation, grid_error). Rejects trigger an on-screen alert and require re-acquisition. | Must | Real-time image QA; reject tracking for retake analysis |
| FR-R07-05 | **Dose Documentation**: Automatically log dose parameters (DAP, DLP where applicable, kVp, mAs, exposure time, SID) for each exam. Display cumulative dose for the patient across all studies in the current encounter. Flag if cumulative dose exceeds protocol ACR benchmark. | Must | ALARA principle; regulatory compliance; feeds R05 QA dashboard |
| FR-R07-06 | **Patient Safety Checks**: Before contrast administration (Fluoroscopy only), display patient allergy/contrast reaction history prominently. Require technician to confirm "No known allergies" or document known allergies and severity. For pregnant patients, display radiation warning and require confirmation before proceeding. | Must | Patient safety; regulatory requirement; feeds incident logging |
| FR-R07-07 | **Exam Completion and Handoff**: On exam completion, the technician marks the exam as "Complete" which triggers: (1) status update in worklist, (2) notification to radiologist (R12) worklist, (3) automatic push of images to PACS archive, (4) generation of exam summary with dose data and view compliance. | Must | Cross-role handoff to R12 radiologist; PACS integration |
| FR-R07-08 | **Retake/Incident Logging**: When an image is rejected or an incident occurs (patient motion, equipment malfunction, contrast reaction), allow the technician to log the incident with: study UID, incident type (positioning, artifact, protocol_deviation, patient_motion, equipment_malfunction, contrast_extravasation), description, and severity. On submission, notify R05 QA team and R12 radiologist if severity is high. | Must | Feeds R05 QA workflow; medico-legal documentation |
| FR-R07-09 | **Fluoroscopy-Specific Workflow**: Provide fluoroscopy-specific acquisition workflow including: live fluoroscopy mode with continuous imaging, spot image capture, cine recording, and dose tracking (DAP cumulative). Allow technician to toggle between fluoroscopy modes and capture spot images during the procedure. | Should | Modality-specific workflow; dose tracking critical for fluoroscopy |
| FR-R07-10 | **Mammography-Specific Workflow**: Provide mammography-specific acquisition workflow including: CC and MLO view selection, compression monitoring with real-time pressure display, exposure parameter auto-calculation based on breast thickness and composition, and ACR-compliant dose tracking. | Should | Modality-specific workflow; ACR compliance for mammography |

## Non-Functional Requirements

| ID | Requirement | Target | Measurement |
|----|-------------|--------|-------------|
| NFR-R07-01 | Worklist load time (LCP) | ≤ 2.0s | Lighthouse CI, RUM |
| NFR-R07-02 | Image preview latency (from acquisition) | ≤ 500ms | Frontend timing |
| NFR-R07-03 | Exam completion handoff notification | ≤ 5s to radiologist worklist | WebSocket latency |
| NFR-R07-04 | Dose parameter logging | ≤ 100ms per acquisition | Backend timing |
| NFR-R07-05 | Reject image processing | ≤ 2s from flag to rejection recorded | Backend timing |
| NFR-R07-06 | Worklist real-time sync staleness | ≤ 30s from exam status change | WebSocket + DB trigger |
| NFR-R07-07 | WCAG 2.2 AA compliance | 100% (keyboard-intensive workflow) | axe-core CI + manual |
| NFR-R07-08 | Image QA contrast ratio | ≥ 4.5:1 for all overlay text on preview | Visual measurement |
| NFR-R07-09 | Concurrent exam capacity | ≥ 3 simultaneous exams per technician | k6 WebSocket scenario |
| NFR-R07-10 | Protocol parameter display | All parameters visible without scrolling on desktop (≥1024px) | Visual verification |

## Codebase Status (verified 2026-08-03)

**Implemented**: FR-R07-01..08 via the shared exam lifecycle — `TechnologistWorklist`
at `/exams`, `ExamConsole` at `/exams/:id` (identity-confirm, protocol,
acquisitions + accept/reject/retake, dose, safety-checks, complete, incidents,
overrides), backend `backend/api/exams.py` + tables `exams`, `acquisitions`,
`safety_checks`, `incidents`, `protocol_overrides`, `protocols`; permissions
`EXAM_READ`/`EXAM_WRITE`/`WORKLIST_*` (no dedicated `technician` role — covered by
`technologist` grants). **GATED** (kept as v3.0 spec): FR-R07-09 fluoroscopy-specific
workflow (live/spot/cine/DAP) and FR-R07-10 mammography-specific workflow
(CC/MLO/compression/AGD) — no `dap`/`agd` columns in `acquisitions`, no
`/fluoroscopy-*` or mammo-specific endpoints. See artifacts 04/07/08 for the
verified presentation-layer mapping.

## Assumptions & Constraints

| # | Assumption / Constraint | Impact |
|---|-------------------------|--------|
| A1 | PHI: Patient initials and MRN last 4 digits shown on worklist; full PHI accessible via exam detail modal per HIPAA minimum necessary | FR-R07-01, FR-R07-02 |
| A2 | 4 new API endpoints required (flagged for `frontend-to-backend-requirements`) | FR-R07-02, FR-R07-05, FR-R07-07, FR-R07-08 |
| A3 | Image preview uses Cornerstone3D viewer; real-time QA overlays are client-side rendering on top of WADO-URI tiles | FR-R07-04 |
| A4 | Dose data comes from DICOM headers (DAP, DLP) parsed at acquisition time; no separate dose tracking system needed | FR-R07-05 |
| A5 | Contrast allergy data comes from EMR (R16) via HL7 ADT; if EMR feed is down, technician manually enters allergy info | FR-R07-06 |
| A6 | PACS archive push is handled by the backend DICOM store service; technician triggers via exam completion | FR-R07-07 |
| A7 | Fluoroscopy and Mammography workflows share the same acquisition framework but have different sequence templates and parameter sets | FR-R07-09, FR-R07-10 |
| A8 | Reject reason codes are standardized: motion, artifact, positioning, exposure, collimation, grid_error, other | FR-R07-04 |
| A9 | Patient pregnancy status is flagged in the patient record (from EMR R16); if not available, technician must manually confirm | FR-R07-06 |
| A10 | Fluoroscopy dose tracking uses DAP (Dose-Area Product) as the primary metric; mammography uses average glandular dose (AGD) | FR-R07-05, FR-R07-09, FR-R07-10 |