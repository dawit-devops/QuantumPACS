# Implementation Roadmap — Radiology Technician (R07)

**Role ID**: R07
**Generated**: 2026-08-03
**Version**: 1.2.0

---

## Dependency Graph

```
FR-R07-01 (Worklist) — IMPLEMENTED
├── FR-R07-02 (Patient Verification) — IMPLEMENTED — depends on worklist exam selection
├── FR-R07-03 (Protocol Selection) — IMPLEMENTED — depends on exam detail
├── FR-R07-04 (Image Acquisition & QA) — IMPLEMENTED — depends on protocol start
├── FR-R07-05 (Dose Documentation) — IMPLEMENTED — depends on acquisition data
├── FR-R07-06 (Safety Checks) — IMPLEMENTED — depends on protocol/contrast flag
├── FR-R07-07 (Exam Completion) — IMPLEMENTED — depends on all above
├── FR-R07-08 (Incident Logging) — IMPLEMENTED — depends on QA reject workflow
├── FR-R07-09 (Fluoroscopy Workflow) — GATED — depends on acquisition framework
└── FR-R07-10 (Mammography Workflow) — GATED — depends on acquisition framework
```

---

## FR Implementation Status

> **Codebase reality (verified 2026-08-03)**: the shared exam lifecycle is shipped
> end-to-end (backend `api/exams.py`, routes in `api/routes.py`: `/exams`,
> `/exams/{id}`, `/identity-confirm`, `/protocol`, `/acquisitions`,
> `/acquisitions/{aid}/{decision}`, `/dose`, `/safety-checks`, `/complete`,
> `/incidents`, `/overrides`, `/protocols`; frontend `frontend/src/technologist/`;
> tables `exams`, `acquisitions`, `safety_checks`, `incidents`,
> `protocol_overrides`, `protocols` in `backend/db/exams.py`). Technicians share
> this lifecycle with R06 — no dedicated technician UI or role exists.

### Implemented (Passing ACs)

| FR/NFR ID | Summary | AC Coverage | Effort |
|-----------|---------|-------------|--------|
| FR-R07-01 | **Modality Worklist** — `TechnologistWorklist.tsx` at `/exams`; 30s auto-refresh; data via `GET /worklist?modality=` | AC-R07-01-01..05 | M |
| FR-R07-02 | **Patient Identity Verification** — `POST /exams/{id}/identity-confirm` (spec name `confirm-patient`) | AC-R07-02-01..05 | S |
| FR-R07-03 | **Exam Protocol Selection** — `GET /exams/{id}/protocol`, `GET /protocols?modality=` | AC-R07-03-01..04 | M |
| FR-R07-04 | **Image Acquisition and QA** — `POST /exams/{id}/acquisitions`; `POST /exams/{id}/acquisitions/{aid}/{decision}` (accept/reject/retake) — covers DR/CR | AC-R07-04-01..05 | M |
| FR-R07-05 | **Dose Documentation** — `GET/POST /exams/{id}/dose` (DLP, CTDIvol per acquisition) | AC-R07-05-01..05 | M |
| FR-R07-06 | **Patient Safety Checks** — `POST /exams/{id}/safety-checks`; `safety_checks` table | AC-R07-06-01..05 | S |
| FR-R07-07 | **Exam Completion and Handoff** — `POST /exams/{id}/complete`; status push via LISTEN/NOTIFY | AC-R07-07-01..04 | M |
| FR-R07-08 | **Retake/Incident Logging** — `GET/POST /exams/{id}/incidents`; `incidents` table | AC-R07-08-01..04 | S |
| NFR-R07-01..10 | Perf/responsiveness ACs tied to implemented screens | AC-R07-* | — |

### Missing (Not Started — GATED)

| FR/NFR ID | Summary | Blocking Dependency | AC | Effort |
|-----------|---------|---------------------|----|--------|
| FR-R07-09 | **Fluoroscopy-Specific Workflow** (live mode, spot/cine, DAP tracking) | No `dap` column in `acquisitions`; no `/fluoroscopy-start`, `/spot-capture`, `/cine-start`, `/cine-stop` endpoints | AC-R07-09-01..05 | L |
| FR-R07-10 | **Mammography-Specific Workflow** (CC/MLO, compression monitoring, AGD) | No `agd` column in `acquisitions`; no mammo-specific endpoints; tomosynthesis v3.1 | AC-R07-10-01..05 | L |
| FR-R07-11 | **AI-assisted image QA** (artifact/positioning detection) | No AI integration; v3.2 scope | — | L |
| FR-R07-12 | **Automated dose optimization suggestions** | No dose-baseline job | — | L |
| FR-R07-13 | **RIS-driven automated protocol selection** | No HL7 ORM integration | — | L |

---

## Implementation Phases

### Phase 1: Core Worklist and Exam Preparation (MVP)
**Status**: ✅ Implemented (FR-R07-01, 02, 03)

**Shipped APIs** (names differ from original spec — confirmed):
1. `GET /api/v2/worklist?modality=` — technician worklist (spec: `/api/v2/worklists/technician`)
2. `GET /api/v2/exams/{id}` — exam detail with patient + protocol
3. `POST /api/v2/exams/{id}/identity-confirm` — patient identity confirmation (spec: `confirm-patient`)
4. `GET /api/v2/exams/{id}/protocol` — protocol parameters
5. `POST /api/v2/exams/{id}/acquisitions` — start/record acquisition (spec: `start-acquisition`)

**Frontend components shipped**: shared R06 console — `TechnologistWorklist.tsx`,
`ExamConsole.tsx` (exam detail: demographics, protocol panel, confirm button),
`SimulatedPreview.tsx`. (Spec's `TechnicianWorklist` is realized as the shared
worklist with modality filtering.)

---

### Phase 2: Image QA and Dose Tracking
**Status**: ✅ Implemented (FR-R07-04, 05)

**Shipped APIs**:
1. `POST /api/v2/exams/{id}/acquisitions/{acquisition_id}/{decision}` — accept/reject/retake (spec: separate `acquire`/`reject`)
2. `GET/POST /api/v2/exams/{id}/dose` — dose + cumulative tracking (spec: `dose-baseline` GET + `dose-log` POST)

**Frontend**: acquisition decision buttons + dose display in `ExamConsole.tsx`.
**Note**: real-time SNR/artifact indicators remain aspirational (FR-R07-11 GATED).

---

### Phase 3: Safety Checks, Completion, and Incident Logging
**Status**: ✅ Implemented (FR-R07-06, 07, 08)

**Shipped APIs**:
1. `POST /api/v2/exams/{id}/safety-checks` — safety check confirmation
2. `POST /api/v2/exams/{id}/complete` — exam complete, push, notify radiologist
3. `GET/POST /api/v2/exams/{id}/incidents` — incident logging

**Frontend**: safety/complete/incident actions in `ExamConsole.tsx`.

---

### Phase 4: Modality-Specific Workflows (Fluoroscopy & Mammography)
**Status**: ❌ Missing — GATED (FR-R07-09, 10)

**Not shipped**: `/api/v2/exams/{id}/fluoroscopy-start`, `/spot-capture`,
`/cine-start`, `/cine-stop` — no fluoroscopy-specific endpoints exist; no `dap`
(fluoroscopy) or `agd` (mammography) columns in the `acquisitions` table;
`FluoroscopyWorkflow` / `MammographyWorkflow` components do not exist.

**Blocked by**: acquisition-schema extension (`dap`/`agd` columns) + fluoro/mammo
endpoints. v3.1 backlog candidate.

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
| `dap` column + `/fluoroscopy-*` endpoints (not in schema/routes) | FR-R07-09 | AC-R07-09-01..05 | Fluoroscopy live/spot/cine/DAP GATED — v3.1 |
| `agd` column + mammo endpoints (not in schema/routes) | FR-R07-10 | AC-R07-10-01..05 | Mammography CC/MLO/compression/AGD GATED — v3.1 |
| AI inference integration | FR-R07-11 | — | AI-assisted image QA — v3.2 |
| Dose-baseline job (DRL thresholds) | FR-R07-12 | — | Dose optimization — v3.1 |
| HL7 ORM integration (R15) | FR-R07-13 | — | RIS protocol selection — v3.1 |

## Next Steps

1. Update roadmap each sprint as FR/NFR status changes
2. Validate remaining ACs (FR-R07-01..08) against the shipped exam console via backend tests + E2E
3. Plan v3.1 backlog: FR-R07-09 fluoro workflow (DAP schema + endpoints), FR-R07-10 mammo workflow (AGD schema), FR-R07-12/13
