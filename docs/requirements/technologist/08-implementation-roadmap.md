# Implementation Roadmap — Radiology Technologist (R06)

**Role ID**: R06
**Generated**: 2026-08-03
**Version**: 1.2.0

---

## Dependency Graph

```
FR-R06-01 (Worklist) — IMPLEMENTED
├── FR-R06-02 (Patient Verification) — IMPLEMENTED — depends on worklist exam selection
├── FR-R06-03 (Protocol Selection) — IMPLEMENTED — depends on exam detail
├── FR-R06-04 (Image Acquisition & QA) — IMPLEMENTED — depends on protocol start
├── FR-R06-05 (Dose Documentation) — IMPLEMENTED — depends on acquisition data
├── FR-R06-06 (Safety Checks) — IMPLEMENTED — depends on protocol/contrast flag
├── FR-R06-07 (Exam Completion) — IMPLEMENTED — depends on all above
├── FR-R06-08 (Incident Logging) — IMPLEMENTED — depends on QA reject workflow
├── FR-R06-09 (Emergency Override) — IMPLEMENTED — depends on protocol panel
└── FR-R06-10 (Modality Workflows) — IMPLEMENTED — depends on acquisition framework
```

---

## FR Implementation Status

> **Codebase reality (verified 2026-08-03)**: the R06 exam lifecycle is shipped
> end-to-end — backend `api/exams.py` (routes in `api/routes.py`:
> `/exams`, `/exams/{id}`, `/identity-confirm`, `/protocol`, `/acquisitions`,
> `/acquisitions/{aid}/{decision}`, `/dose`, `/safety-checks`, `/complete`,
> `/incidents`, `/overrides`, `/protocols`), frontend `frontend/src/technologist/`
> (`TechnologistWorklist.tsx` at `/exams`, `ExamConsole.tsx` at `/exams/:id`,
> `SimulatedPreview.tsx`), tables in `backend/db/exams.py` (`exams`, `acquisitions`,
> `safety_checks`, `incidents`, `protocol_overrides`, `protocols`), permissions
> `EXAM_READ`/`EXAM_WRITE`/`WORKLIST_*` + `technologist` built-in role.

### Implemented (Passing ACs)

| FR/NFR ID | Summary | AC Coverage | Effort |
|-----------|---------|-------------|--------|
| FR-R06-01 | **Modality Worklist** — `TechnologistWorklist.tsx` at `/exams`; 30s auto-refresh, STAT highlighting; data via `GET /worklist?modality=` | AC-R06-01-01..05 | M |
| FR-R06-02 | **Patient Identity Verification** — `POST /exams/{id}/identity-confirm` (spec name `confirm-patient`) | AC-R06-02-01..05 | S |
| FR-R06-03 | **Exam Protocol Selection** — `GET /exams/{id}/protocol`, `GET /protocols?modality=`; ExamConsole protocol panel with parameter review | AC-R06-03-01..04 | M |
| FR-R06-04 | **Image Acquisition and QA** — `POST /exams/{id}/acquisitions`; `POST /exams/{id}/acquisitions/{aid}/{decision}` (accept/reject/retake); `SimulatedPreview.tsx` | AC-R06-04-01..05 | M |
| FR-R06-05 | **Dose Documentation** — `GET/POST /exams/{id}/dose` (DLP, CTDIvol per acquisition) | AC-R06-05-01..05 | M |
| FR-R06-06 | **Patient Safety Checks** — `POST /exams/{id}/safety-checks`; `safety_checks` table (checked_at, flags) | AC-R06-06-01..05 | S |
| FR-R06-07 | **Exam Completion and Handoff** — `POST /exams/{id}/complete`; status push via LISTEN/NOTIFY to R12/R04 worklists | AC-R06-07-01..04 | M |
| FR-R06-08 | **Retake/Incident Logging** — `GET/POST /exams/{id}/incidents`; `incidents` table | AC-R06-08-01..04 | S |
| FR-R06-09 | **Emergency Protocol Override** — `POST /exams/{id}/overrides`; `protocol_overrides` table with justification + audit | AC-R06-09-01..04 | S |
| FR-R06-10 | **Modality-Specific Workflows** — `MODALITY_WORKFLOWS` in ExamConsole (CT/MR/PET/US); per-modality protocol presets | AC-R06-10-01..06 | M |
| NFR-R06-01..10 | Perf/responsiveness/contrast/capacity ACs tied to implemented screens | AC-R06-* | — |

**Remaining GATED** (kept as v3.0/v3.1 spec): FR-R06-11 AI-assisted image QA
(v3.2 — no AI inference integration), FR-R06-12 automated dose optimization
suggestions (no dose-baseline job), FR-R06-13 RIS-driven automated protocol
selection (no HL7 ORM integration).

---

## Implementation Phases

### Phase 1: Core Worklist and Exam Preparation (MVP)
**Status**: ✅ Implemented (FR-R06-01, 02, 03)

**Shipped APIs** (names differ from original spec — confirmed):
1. `GET /api/v2/worklist?modality=` — technologist worklist (spec: `/api/v2/worklists/technologist`)
2. `GET /api/v2/exams/{id}` — exam detail with patient + protocol
3. `POST /api/v2/exams/{id}/identity-confirm` — patient identity confirmation (spec: `confirm-patient`)
4. `GET /api/v2/exams/{id}/protocol` — protocol parameters
5. `POST /api/v2/exams/{id}/acquisitions` — start/record acquisition (spec: `start-acquisition`)

**Frontend components shipped**: `TechnologistWorklist.tsx` (worklist with modality
filter + 30s auto-refresh + STAT highlighting), `ExamConsole.tsx` (exam detail:
demographics, protocol panel, confirm button), `SimulatedPreview.tsx` (preview pane;
real modality capture remains on modality console).

---

### Phase 2: Image QA and Dose Tracking
**Status**: ✅ Implemented (FR-R06-04, 05)

**Shipped APIs**:
1. `POST /api/v2/exams/{id}/acquisitions/{acquisition_id}/{decision}` — accept/reject/retake (spec: separate `acquire`/`reject`)
2. `GET/POST /api/v2/exams/{id}/dose` — dose + cumulative tracking (spec: `dose-baseline` GET + `dose-log` POST)

**Frontend components shipped**: acquisition decision buttons in `ExamConsole.tsx`,
dose display (DLP/CTDIvol). **Note**: `QAOverlay`/`DosePanel` live-indicator
components from the original spec remain partially aspirational — the console
renders dose values server-side via `SimulatedPreview.tsx`; real-time SNR/artifact
flags are GATED (FR-R06-11).

---

### Phase 3: Safety Checks, Completion, and Incident Logging
**Status**: ✅ Implemented (FR-R06-06, 07, 08)

**Shipped APIs**:
1. `POST /api/v2/exams/{id}/safety-checks` — safety check confirmation
2. `POST /api/v2/exams/{id}/complete` — exam complete, push, notify radiologist
3. `GET/POST /api/v2/exams/{id}/incidents` — incident logging
4. `POST /api/v2/exams/{id}/overrides` — emergency protocol override

**Frontend**: safety/complete/incident/override actions in `ExamConsole.tsx`.

---

### Phase 4: Modality-Specific Workflows and Emergency Override
**Status**: ✅ Implemented (FR-R06-09, 10)

**Shipped**: `POST /api/v2/exams/{id}/overrides` (emergency override with
justification + audit trail), `MODALITY_WORKFLOWS` (CT/MR/PET/US) + per-modality
protocol presets in ExamConsole. **Note**: `MammographyWorkflow` (CC/MLO with
compression monitoring) and ultrasound freeze/measure tools are GATED — see R07
FR-R07-10 for mammography specifics.

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
| AI inference integration | FR-R06-11 | AC-R06 AI ACs (v3.2) | AI-assisted image QA — v3.2 backlog |
| Dose-baseline job (DRL thresholds) | FR-R06-12 | — | Automated dose optimization suggestions — v3.1 backlog |
| HL7 ORM integration (R15) | FR-R06-13 | — | RIS-driven protocol selection — v3.1 backlog |

## Next Steps

1. Update roadmap each sprint as FR/NFR status changes
2. Validate remaining ACs against the shipped exam console (backend tests + E2E in `frontend/src/test/ExamConsole.test.tsx`)
3. Plan v3.1 backlog: FR-R06-12 dose optimization, FR-R06-13 RIS protocol selection
