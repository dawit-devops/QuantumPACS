# Backend Requirements: R07 Radiology Technician

## Context

The Technician is the operator for DR, CR, Fluoroscopy, and Mammography —
positioning, acquisition, image QC, retakes, and exam completion. Functionally
the same operator workflow as R06 Technologist but for projection/x-ray
modalities, with two modality-specific additions: a **fluoroscopy workflow**
(live mode, spot capture, cine recording, DAP tracking) and a **mammography
workflow** (CC/MLO views, compression monitoring, AGD tracking). Same WebSocket
real-time requirements as R06.

**Screens (new)**: Technician Worklist, Exam Detail Panel, Protocol Panel,
Acquisition View + QA Overlay, Dose Panel, Safety Check Modal, Incident Log
Modal, Fluoroscopy Workflow, Mammography Workflow.

**Personas**: P2 (Technician). **Access tier**: operator per exam.

## Screens/Components

### Technician Worklist

**Purpose**: See assigned DR/CR/Fluoro/Mammo exams, prioritize STAT work.

**Data I need**: exams assigned to the technician (patient initials + MRN last 4,
accession, modality, protocol, priority, status), modality filtering, real-time
updates on assignment/completion (≤5 s).

### Exam Detail Panel

**Purpose**: Verify patient identity, review protocol before acquiring.

**Data I need**: patient demographics, protocol (views, kVp, mAs, SID, grid),
safety flags (allergy/pregnancy — fluoroscopy contrast).

**Actions**: confirm patient, review protocol.

### Acquisition View + QA Overlay

**Purpose**: Capture images with per-image QA.

**Data I need**: live preview, exposure/positioning/artifact QA indicators,
accept/reject state per image.

**Actions**: accept/reject with reason; record acquisition (with dose).

### Dose Panel

**Purpose**: Track dose — DAP for fluoroscopy, AGD for mammography.

**Data I need**: per-acquisition dose (kVp, mAs, DAP, AGD), cumulative totals,
benchmark comparison.

### Fluoroscopy Workflow

**Purpose**: Live fluoro + spot/cine capture with DAP tracking.

**Data I need**: live-mode state, spot image capture results, cine recording
start/stop, cumulative DAP.

**Actions**: start live mode, capture spot, start/stop cine, monitor DAP.

**States to handle**: idle, live, spot, cine, complete; live-mode indicator.

### Mammography Workflow

**Purpose**: CC/MLO acquisition with compression + AGD tracking.

**Data I need**: view selection (CC/MLO), compression pressure, AGD values.

**Actions**: select view, monitor compression, record AGD.

**States to handle**: idle, cc, mlo, complete; compression warning.

### Safety Check / Incident Log / Exam Completion

Identical shape to R06 (pre-contrast safety checklist, structured incident
logging, exam completion → PACS push + radiologist notification).

## Uncertainties
- [ ] Fluoroscopy DAP: recorded by the modality/backend or entered in the UI?
- [ ] Mammography compression monitoring: is pressure streamed live or entered
  per-view?
- [ ] Same worklist contract as R06 — confirm one shared implementation rather
  than a parallel one.
- [ ] RBAC/permission slugs for the technician role overlap R06 (`EXAM_*`) —
  confirm the two roles share permissions.

## Questions for Backend
- Can the fluoroscopy/mammography workflows reuse the same exam + acquisition
  endpoints as R06, with modality-specific dose fields?
- What triggers live mode / cine recording — backend-managed sessions or
  UI-managed with backend persistence?

## Discussion Log

_(pending backend review)_
