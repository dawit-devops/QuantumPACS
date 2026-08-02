# Backend Requirements: R06 Radiology Technologist

## Context

The Technologist operates MRI, PET, CT, Fluoroscopy, Mammography, and Ultrasound
modalities: exam preparation and patient positioning, image acquisition and QA,
dose documentation, safety checks, exam completion and handoff to the
radiologist, and retake/incident logging. Per-exam, high-throughput, real-time
workflow at the modality console, with a dual-monitor worklist + viewer setup.
Worklist updates must arrive in near-real-time (assignments from R04, exam
completion to R12) — this is a **WebSocket-driven** role.

**Screens (new)**: Technologist Worklist, Exam Detail Panel, Protocol Panel,
Acquisition View (Cornerstone3D with QA overlay), QA Overlay, Dose Panel,
Safety Check Modal, Incident Log Modal, Emergency Override Modal.

**Personas**: P2 (Technologist). **Access tier**: operator per exam
(`WORKLIST_READ`, `EXAM_READ`, `EXAM_WRITE`).

## Screens/Components

### Technologist Worklist

**Purpose**: See assigned exams, prioritize STAT work, open exam detail.

**Data I need to display**: exams assigned to the technologist — patient
initials + MRN last 4 (minimum necessary), accession, modality, protocol,
priority (STAT highlighted), status, scheduled time; auto-refresh/WS update
(≤5 s after R04 assignment, ≤30 s staleness target).

**Actions**: filter by modality/status, open an exam, sort by priority.

**States to handle**: empty, loading, error, STAT highlight, exam that another
technologist just took (row disappears).

### Exam Detail Panel

**Purpose**: Verify patient identity and review exam context before acquiring.

**Data I need**: patient demographics (full PHI here per minimum necessary),
accession, requested procedure, protocol, allergy/pregnancy/contrast flags
(from HL7 ADT), scheduled info.

**Actions**: confirm patient identity (blocks acquisition until done).

**States to handle**: idle, loading, confirmed, error; identity-mismatch warning.

### Protocol Panel

**Purpose**: Review protocol parameters before starting acquisition.

**Data I need**: protocol sequences (kVp, mAs, exposure, slice thickness, etc.),
safety conflict warnings.

**Actions**: review, start acquisition.

**States to handle**: idle, loading, error, started.

### Acquisition View + QA Overlay

**Purpose**: Capture images with real-time QA.

**Data I need**: live/preview image stream (Cornerstone3D), acquisition records,
QA indicators (SNR, contrast, artifact flags).

**Actions**: accept/reject images with reason, record acquisition (with dose),
start/stop acquisition.

**States to handle**: idle, acquiring, paused, complete; accept/reject per image;
rejected images counted and reason-captured.

### Dose Panel

**Purpose**: Track cumulative dose vs. ACR benchmarks.

**Data I need**: per-acquisition dose values (kVp, mAs, DLP, CTDIvol), cumulative
dose, ACR benchmark comparison; warning/danger thresholds.

**Actions**: log dose (auto or manual entry), view cumulative totals.

**States to handle**: idle, loading, warning, danger (color-coded banners).

### Safety Check Modal

**Purpose**: Structured pre-contrast safety checks.

**Data I need**: allergy/pregnancy flags from EMR, contrast check checklist.

**Actions**: confirm each safety item (required before contrast).

### Exam Completion & Handoff

**Purpose**: Close the exam and hand off to the radiologist.

**Data I need**: completion confirmation, PACS push status.

**Actions**: mark exam complete → triggers PACS push (C-STORE) and notifies the
radiologist worklist (≤5 s).

### Incident Log Modal

**Purpose**: Structured retake/incident logging.

**Data I need**: incident type, severity, description, linked study; QA inbox
delivery.

**Actions**: submit incident → notification to R05/R12.

### Emergency Override

**Purpose**: Protocol override for emergencies.

**Data I need**: override justification, protocol comparison, audit trail.

**Actions**: request override with justification (audited).

## Uncertainties
- [ ] Dose data source: auto-logged by the modality/backend, or entered manually
  in the UI? The acquisition + dose endpoints imply capture-side logging.
- [ ] Worklist updates: are they pushed (WebSocket LISTEN/NOTIFY) or polled?
- [ ] Protocol registry: does the backend hold the authoritative protocol
  parameters (per R05), or does the technologist UI maintain its own copy?
- [ ] Identity verification: is a failed confirmation reversible, and does it
  alert anyone?
- [ ] RBAC slugs `EXAM_READ`/`EXAM_WRITE` are proposed but not yet in the
  permission registry.
- [ ] Emergency override: does the backend enforce approval workflow, or is it a
  logged justification only?

## Questions for Backend
- On exam completion, does the backend perform the PACS C-STORE push and return
  status, or is the UI expected to drive it?
- What WebSocket events does the technologist worklist need to subscribe to?
- Are safety-check and dose records part of the acquisition record, or separate
  writes?

## Discussion Log

_(pending backend review)_
