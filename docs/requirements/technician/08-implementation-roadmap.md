# Implementation Roadmap — Radiology Technician (R07)

**Role ID**: R07
**Generated**: 2026-08-02
**Version**: 1.0.0

---

## Dependency Graph

```
FR-R07-01 (Worklist)
├── FR-R07-02 (Patient Verification) — depends on worklist exam selection
├── FR-R07-03 (Protocol Selection) — depends on exam detail
├── FR-R07-04 (Image Acquisition & QA) — depends on protocol start
├── FR-R07-05 (Dose Documentation) — depends on acquisition data
├── FR-R07-06 (Safety Checks) — depends on protocol/contrast flag
├── FR-R07-07 (Exam Completion) — depends on all above
├── FR-R07-08 (Incident Logging) — depends on QA reject workflow
├── FR-R07-09 (Fluoroscopy Workflow) — depends on acquisition framework
└── FR-R07-10 (Mammography Workflow) — depends on acquisition framework
```

---

## Implementation Phases

### Phase 1: Core Worklist and Exam Preparation (MVP)
**Status**: Missing — no implementation started
**Dependencies**: None

| Artifact | What's Lacking | What's Done |
|----------|---------------|-------------|
| 01 User Requirements | FR-R07-01, FR-R07-02, FR-R07-03 | — |
| 02 Workflow Maps | W1, W2 | — |
| 03 User Stories | US-R07-01, US-R07-02, US-R07-03 | — |
| 04 UI/UX | S-R07-01, S-R07-02 | — |
| 05 Metrics | M-R07-01, M-R07-06 | — |
| 06 ACs | AC-R07-01, AC-R07-02, AC-R07-03 | — |
| 07 Traceability | All FR→AC mappings | — |
| 08 Roadmap | This document | ✅ |

**Key APIs needed**:
1. `GET /api/v2/worklists/technician` — fetch technician worklist
2. `GET /api/v2/exams/{id}` — fetch exam detail with patient + protocol
3. `POST /api/v2/exams/{id}/confirm-patient` — confirm patient identity
4. `GET /api/v2/exams/{id}/protocol` — fetch protocol parameters
5. `POST /api/v2/exams/{id}/start-acquisition` — start image acquisition

**Frontend components needed**:
1. `TechnicianWorklist` — extends existing worklist with DR/CR/Fluoroscopy/Mammography filtering
2. `ExamDetailPanel` — patient demographics + protocol + confirm button
3. `ProtocolPanel` — protocol parameters display + start button
4. `AcquisitionView` — Cornerstone3D viewer with QA overlay

**Estimated effort**: Large (3-4 sprints)

---

### Phase 2: Image QA and Dose Tracking
**Status**: Missing — depends on Phase 1
**Dependencies**: Phase 1 complete

| Artifact | What's Lacking | What's Done |
|----------|---------------|-------------|
| 01 User Requirements | FR-R07-04, FR-R07-05 | — |
| 02 Workflow Maps | W2 (QA portion) | — |
| 03 User Stories | US-R07-04, US-R07-05 | — |
| 04 UI/UX | S-R07-03, S-R07-04 | — |
| 05 Metrics | M-R07-02, M-R07-04, M-R07-05, M-R07-07, M-R07-09 | — |
| 06 ACs | AC-R07-04, AC-R07-05 | — |
| 07 Traceability | FR-R07-04, FR-R07-05 mappings | — |

**Key APIs needed**:
1. `POST /api/v2/exams/{id}/acquire` — record image acquisition with dose
2. `POST /api/v2/exams/{id}/reject` — flag image as rejected
3. `GET /api/v2/exams/{id}/dose-baseline` — fetch cumulative dose + ACR benchmark
4. `POST /api/v2/exams/{id}/dose-log` — log dose parameters

**Frontend components needed**:
1. `QAOverlay` — real-time image quality indicators on Cornerstone3D viewer
2. `RejectModal` — reject reason dropdown + description textarea
3. `DosePanel` — live dose tracking with cumulative total and benchmark comparison
4. `AcceptButton` / `RejectButton` — keyboard shortcuts (A/R) for QA

**Estimated effort**: Medium (2 sprints)

---

### Phase 3: Safety Checks, Completion, and Incident Logging
**Status**: Missing — depends on Phase 2
**Dependencies**: Phase 2 complete

| Artifact | What's Lacking | What's Done |
|----------|---------------|-------------|
| 01 User Requirements | FR-R07-06, FR-R07-07, FR-R07-08 | — |
| 02 Workflow Maps | W3, W4, W5 | — |
| 03 User Stories | US-R07-06, US-R07-07, US-R07-08 | — |
| 04 UI/UX | S-R07-05, S-R07-06 | — |
| 05 Metrics | M-R07-03, M-R07-08, M-R07-10 | — |
| 06 ACs | AC-R07-06, AC-R07-07, AC-R07-08 | — |
| 07 Traceability | FR-R07-06, FR-R07-07, FR-R07-08 mappings | — |

**Key APIs needed**:
1. `POST /api/v2/exams/{id}/safety-check` — record safety check confirmation
2. `POST /api/v2/exams/{id}/complete` — mark exam complete, push to PACS, notify radiologist
3. `POST /api/v2/exams/{id}/incident` — log incident with severity

**Frontend components needed**:
1. `SafetyCheckModal` — allergy/pregnancy safety check before contrast
2. `CompletionPanel` — exam completion summary with dose data and view compliance
3. `IncidentLogModal` — incident type dropdown + severity selector + description

**Estimated effort**: Medium (2 sprints)

---

### Phase 4: Modality-Specific Workflows (Fluoroscopy & Mammography)
**Status**: Missing — depends on Phase 3
**Dependencies**: Phase 3 complete

| Artifact | What's Lacking | What's Done |
|----------|---------------|-------------|
| 01 User Requirements | FR-R07-09, FR-R07-10 | — |
| 02 Workflow Maps | W2 (acquisition portion) | — |
| 03 User Stories | US-R07-09, US-R07-10 | — |
| 04 UI/UX | S-R07-07, S-R07-08 | — |
| 05 Metrics | M-R07-02, M-R07-04 | — |
| 06 ACs | AC-R07-09, AC-R07-10 | — |
| 07 Traceability | FR-R07-09, FR-R07-10 mappings | — |

**Key APIs needed**:
1. `POST /api/v2/exams/{id}/fluoroscopy-start` — start fluoroscopy live mode
2. `POST /api/v2/exams/{id}/spot-capture` — capture spot image
3. `POST /api/v2/exams/{id}/cine-start` — start cine recording
4. `POST /api/v2/exams/{id}/cine-stop` — stop cine recording
5. `GET /api/v2/exams/{id}/protocol` — returns modality-specific workflow template

**Frontend components needed**:
1. `FluoroscopyWorkflow` — live fluoroscopy + spot capture + cine recording + DAP tracker
2. `MammographyWorkflow` — CC/MLO view selection + compression monitoring + AGD tracker

**Estimated effort**: Medium (2 sprints)

---

## Status Summary

| Artifact | Status | Phase |
|----------|--------|-------|
| 01 User Requirements | ✅ Complete | — |
| 02 Workflow Maps | ✅ Complete | — |
| 03 User Stories | ✅ Complete | — |
| 04 UI/UX Requirements | ✅ Complete | — |
| 05 Metrics & SLAs | ✅ Complete | — |
| 06 Acceptance Criteria | ✅ Complete | — |
| 07 Traceability Matrix | ✅ Complete | — |
| 08 Implementation Roadmap | ✅ Complete | — |

## Blocking Dependencies

| Blocking Dependency | Blocks | AC | Impact |
|---------------------|--------|----|--------|
| Backend `/exams/*` endpoints + `EXAM_*` permission slugs (not in `permissions.py`) | FR-R07-01..10 | AC-R07 acquisition ACs | Entire acquisition workflow (incl. fluoro/mammo) GATED until backend exists |
| `protocols` / `image_acquisitions` schema (not in DB) | FR-R07-03..05 | AC-R07 protocol/dose ACs | Protocol + dose features cannot ship without schema |

## Next Steps

1. Delegate API contract design to `frontend-to-backend-requirements` skill
2. Delegate RESTful resource design to `rest-api-design` skill
3. Prioritize Phase 1 user stories (US-R07-01, 02, 03, 04, 05) for MVP
4. Schedule stakeholder review with R07 radiology technicians
5. Conduct usability testing with 2-3 radiology technicians before full implementation