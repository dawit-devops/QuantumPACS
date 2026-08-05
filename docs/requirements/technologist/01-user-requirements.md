# User Requirements — Radiology Technologist (R06)

**Version**: 1.0.0 (v3.0 scope)
**Status**: Draft
**Date**: 2026-08-02

---

## Functional Requirements

| ID | Requirement | Priority | Notes |
|----|-------------|----------|-------|
| FR-R06-01 | **Modality Worklist**: Display a filtered, paginated worklist of assigned exams for the logged-in technologist. Columns: Accession, Patient (initials), Modality, Protocol, Priority (STAT/urgent/routine), Status (pending/in-progress/completed). Auto-refresh every 30s via WebSocket. STAT exams highlighted with red left border. | Must | Extends existing worklist component with modality-specific filtering and auto-refresh |
| FR-R06-02 | **Patient Identity Verification**: Before starting an exam, the system SHALL display patient demographics (name initials, MRN last 4 digits, DOB, sex) and require the technologist to verify identity via a "Confirm Patient" button. If the patient has a prior study in the system, display a "Prior Study" indicator with comparison link. | Must | Patient safety critical; prevents misidentification errors |
| FR-R06-03 | **Exam Protocol Selection**: Display the assigned protocol with required sequences, parameters (kVp, mAs, slice thickness, contrast), and body position instructions. Allow the technologist to confirm protocol start. If protocol parameters conflict with patient safety (e.g., contrast allergy), flag with warning. | Must | Protocol data from `protocols` table; dynamic based on exam type |
| FR-R06-04 | **Image Acquisition and QA**: During image acquisition, display real-time image preview with quality indicators (signal-to-noise, contrast, artifact detection). Allow technologist to flag images as "reject" with reason code (motion, artifact, positioning, exposure). Rejects trigger an on-screen alert and require re-acquisition. | Must | Real-time image QA; reject tracking for retake analysis |
| FR-R06-05 | **Dose Documentation**: Automatically log dose parameters (DLP, CTDIvol, kVp, mAs, exposure time) for each exam. Display cumulative dose for the patient across all studies in the current encounter. Flag if cumulative dose exceeds protocol ACR benchmark. | Must | ALARA principle; regulatory compliance; feeds R05 QA dashboard |
| FR-R06-06 | **Patient Safety Checks**: Before contrast administration, display patient allergy/contrast reaction history prominently. Require technologist to confirm "No known allergies" or document known allergies and severity. For pregnant patients, display radiation warning and require confirmation before proceeding. | Must | Patient safety; regulatory requirement; feeds incident logging |
| FR-R06-07 | **Exam Completion and Handoff**: On exam completion, the technologist marks the exam as "Complete" which triggers: (1) status update in worklist, (2) notification to radiologist (R12) worklist, (3) automatic push of images to PACS archive, (4) generation of exam summary with dose data and sequence compliance. | Must | Cross-role handoff to R12 radiologist; PACS integration |
| FR-R06-08 | **Retake/Incident Logging**: When an image is rejected or an incident occurs (patient motion, equipment malfunction, contrast reaction), allow the technologist to log the incident with: study UID, incident type (positioning, artifact, protocol_deviation, patient_motion, equipment_malfunction, contrast_extravasation), description, and severity. On submission, notify R05 QA team and R12 radiologist if severity is high. | Must | Feeds R05 QA workflow; medico-legal documentation |
| FR-R06-09 | **Emergency Protocol Override**: In emergency situations (trauma, STAT), allow the technologist to override standard protocol parameters (e.g., reduce sequences, skip non-critical acquisitions) with a justification field. Override is logged with timestamp and justification for audit trail. | Should | Clinical flexibility; audit trail required |
| FR-R06-10 | **Modality-Specific Workflows**: Provide modality-specific acquisition workflows: CT (localizer → contrast → diagnostic series), MRI (localizer → sequence list with parameters), PET (dose calibration → uptake period → acquisition), Ultrasound (real-time capture with annotation capability), Mammography (CC/MLO views with compression monitoring). | Must | Each modality has its own acquisition protocol and workflow |

## Non-Functional Requirements

| ID | Requirement | Target | Measurement |
|----|-------------|--------|-------------|
| NFR-R06-01 | Worklist load time (LCP) | ≤ 2.0s | Lighthouse CI, RUM |
| NFR-R06-02 | Image preview latency (from acquisition) | ≤ 500ms | Frontend timing |
| NFR-R06-03 | Exam completion handoff notification | ≤ 5s to radiologist worklist | WebSocket latency |
| NFR-R06-04 | Dose parameter logging | ≤ 100ms per acquisition | Backend timing |
| NFR-R06-05 | Reject image processing | ≤ 2s from flag to rejection recorded | Backend timing |
| NFR-R06-06 | Worklist real-time sync staleness | ≤ 30s from exam status change | WebSocket + DB trigger |
| NFR-R06-07 | WCAG 2.2 AA compliance | 100% (keyboard-intensive workflow) | axe-core CI + manual |
| NFR-R06-08 | Image QA contrast ratio | ≥ 4.5:1 for all overlay text on preview | Visual measurement |
| NFR-R06-09 | Concurrent exam capacity | ≥ 3 simultaneous exams per technologist | k6 WebSocket scenario |
| NFR-R06-10 | Protocol parameter display | All parameters visible without scrolling on desktop (≥1024px) | Visual verification |

## Codebase Status (verified 2026-08-03)

**Implemented**: R06 exam lifecycle shipped end-to-end — `TechnologistWorklist.tsx`
(30s auto-refresh, `/worklist`), `ExamConsole.tsx` (`/exams`, `/exams/:id`:
identity-confirm, protocol, acquisitions + accept/reject/retake decision, dose,
safety-checks, complete, incidents, overrides; `/protocols`), `SimulatedPreview.tsx`.
Backend `backend/api/exams.py` + tables `exams`, `acquisitions`, `safety_checks`,
`incidents`, `protocol_overrides`, `protocols`; permissions `EXAM_READ`/`EXAM_WRITE`/
`WORKLIST_READ`/`WORKLIST_WRITE` + `technologist` built-in role. FR-R06-01..10 map to
shipped endpoints (see artifact 07). **GATED** (kept as v3.0/v3.1 spec):
FR-R06-11 AI-assisted image QA (v3.2), FR-R06-12 automated dose optimization,
FR-R06-13 RIS-driven protocol selection (no HL7 ORM integration).

## Assumptions & Constraints

| # | Assumption / Constraint | Impact |
|---|-------------------------|--------|
| A1 | PHI: Patient initials and MRN last 4 digits shown on worklist; full demographics in patient detail modal per HIPAA minimum necessary | FR-R06-01, FR-R06-02 |
| A2 | 5 new API endpoints required (flagged for `frontend-to-backend-requirements`) | FR-R06-02, FR-R06-04, FR-R06-07, FR-R06-08 |
| A3 | Image preview uses Cornerstone3D viewer; real-time QA overlays are client-side rendering on top of WADO-URI tiles | FR-R06-04 |
| A4 | Dose data comes from DICOM headers (CTDIvol, DLP) parsed at acquisition time; no separate dose tracking system needed | FR-R06-05 |
| A5 | Contrast allergy data comes from EMR (R16) via HL7 ADT; if EMR feed is down, technologist manually enters allergy info | FR-R06-06 |
| A6 | PACS archive push is handled by the backend DICOM store service; technologist triggers via exam completion | FR-R06-07 |
| A7 | Emergency protocol override is a clinical decision; the system logs the override but does not prevent it | FR-R06-09 |
| A8 | Modality-specific workflows share the same acquisition framework but have different sequence templates and parameter sets | FR-R06-10 |
| A9 | Reject reason codes are standardized: motion, artifact, positioning, exposure, patient_movement, equipment_malfunction, other | FR-R06-04 |
| A10 | Patient pregnancy status is flagged in the patient record (from EMR R16); if not available, technologist must manually confirm | FR-R06-06 |