# Implementation Roadmap — Radiology Technologist (R06)

**Role ID**: R06
**Generated**: 2026-08-02
**Version**: 1.0.0

---

## Dependency Graph

```
FR-R06-01 (Worklist)
├── FR-R06-02 (Patient Verification) — depends on worklist exam selection
├── FR-R06-03 (Protocol Selection) — depends on exam detail
├── FR-R06-04 (Image Acquisition & QA) — depends on protocol start
├── FR-R06-05 (Dose Documentation) — depends on acquisition data
├── FR-R06-06 (Safety Checks) — depends on protocol/contrast flag
├── FR-R06-07 (Exam Completion) — depends on all above
├── FR-R06-08 (Incident Logging) — depends on QA reject workflow
├── FR-R06-09 (Emergency Override) — depends on protocol panel
└── FR-R06-10 (Modality Workflows) — depends on acquisition framework
```

---

## Implementation Phases

### Phase 1: Core Worklist and Exam Preparation (MVP)
**Status**: Missing — no implementation started
**Dependencies**: None

| Artifact | What's Lacking | What's Done |
|----------|---------------|-------------|
| 01 User Requirements | FR-R06-01, FR-R06-02, FR-R06-03 | — |
| 02 Workflow Maps | W1, W2 | — |
| 03 User Stories | US-R06-01, US-R06-02, US-R06-03 | — |
| 04 UI/UX | S-R06-01, S-R06-02 | — |
| 05 Metrics | M-R06-01, M-R06-06 | — |
| 06 ACs | AC-R06-01, AC-R06-02, AC-R06-03 | — |
| 07 Traceability | All FR→AC mappings | — |
| 08 Roadmap | This document | ✅ |

**Key APIs needed**:
1. `GET /api/v2/worklists/technologist` — fetch technologist worklist
2. `GET /api/v2/exams/{id}` — fetch exam detail with patient + protocol
3. `POST /api/v2/exams/{id}/confirm-patient` — confirm patient identity
4. `GET /api/v2/exams/{id}/protocol` — fetch protocol parameters
5. `POST /api/v2/exams/{id}/start-acquisition` — start image acquisition

**Frontend components needed**:
1. `TechnologistWorklist` — extends existing worklist with modality filtering
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
| 01 User Requirements | FR-R06-04, FR-R06-05 | — |
| 02 Workflow Maps | W2 (QA portion) | — |
| 03 User Stories | US-R06-04, US-R06-05 | — |
| 04 UI/UX | S-R06-03, S-R06-04 | — |
| 05 Metrics | M-R06-02, M-R06-04, M-R06-05, M-R06-07, M-R06-09 | — |
| 06 ACs | AC-R06-04, AC-R06-05 | — |
| 07 Traceability | FR-R06-04, FR-R06-05 mappings | — |

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
| 01 User Requirements | FR-R06-06, FR-R06-07, FR-R06-08 | — |
| 02 Workflow Maps | W3, W4, W5 | — |
| 03 User Stories | US-R06-06, US-R06-07, US-R06-08 | — |
| 04 UI/UX | S-R06-05, S-R06-06, S-R06-07 | — |
| 05 Metrics | M-R06-03, M-R06-08, M-R06-10 | — |
| 06 ACs | AC-R06-06, AC-R06-07, AC-R06-08 | — |
| 07 Traceability | FR-R06-06, FR-R06-07, FR-R06-08 mappings | — |

**Key APIs needed**:
1. `POST /api/v2/exams/{id}/safety-check` — record safety check confirmation
2. `POST /api/v2/exams/{id}/complete` — mark exam complete, push to PACS, notify radiologist
3. `POST /api/v2/exams/{id}/incident` — log incident with severity
4. `POST /api/v2/exams/{id}/override-protocol` — emergency protocol override

**Frontend components needed**:
1. `SafetyCheckModal` — allergy/pregnancy safety check before contrast
2. `CompletionPanel` — exam completion summary with dose data and sequence compliance
3. `IncidentLogModal` — incident type dropdown + severity selector + description
4. `OverrideModal` — emergency protocol override with justification

**Estimated effort**: Medium (2 sprints)

---

### Phase 4: Modality-Specific Workflows and Emergency Override
**Status**: Missing — depends on Phase 3
**Dependencies**: Phase 3 complete

| Artifact | What's Lacking | What's Done |
|----------|---------------|-------------|
| 01 User Requirements | FR-R06-09, FR-R06-10 | — |
| 02 Workflow Maps | W2 (acquisition portion) | — |
| 03 User Stories | US-R06-09, US-R06-10 | — |
| 04 UI/UX | S-R06-03 (modality-specific views) | — |
| 05 Metrics | M-R06-02, M-R06-04 | — |
| 06 ACs | AC-R06-09, AC-R06-10 | — |
| 07 Traceability | FR-R06-09, FR-R06-10 mappings | — |

**Key APIs needed**:
1. `GET /api/v2/exams/{id}/protocol` — returns modality-specific workflow template
2. `POST /api/v2/exams/{id}/override-protocol` — emergency protocol override

**Frontend components needed**:
1. `CTWorkflow` — CT-specific acquisition sequence (localizer → contrast → diagnostic)
2. `MRIWorkflow` — MRI-specific acquisition sequence with collapsible parameter sections
3. `PETWorkflow` — PET-specific workflow with dose calibration and uptake timer
4. `UltrasoundWorkflow` — real-time capture with annotation and freeze/measure tools
5. `MammographyWorkflow` — CC/MLO view workflows with compression monitoring

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
| Backend `/exams/*` endpoints + `EXAM_*` permission slugs (not in `permissions.py`) | FR-R06-01..10 | AC-R06 acquisition ACs | Entire acquisition workflow GATED until backend exists |
| `protocols` / `image_acquisitions` schema (not in DB) | FR-R06-03..05 | AC-R06 protocol/dose ACs | Protocol + dose features cannot ship without schema |

## Next Steps

1. Delegate API contract design to `frontend-to-backend-requirements` skill
2. Delegate RESTful resource design to `rest-api-design` skill
3. Prioritize Phase 1 user stories (US-R06-01, 02, 03, 04, 05) for MVP
4. Schedule stakeholder review with R06 radiology technologists
5. Conduct usability testing with 2-3 radiology technologists before full implementation