# Requirements Package — R12 Staff Radiologist

| Field | Value |
|-------|-------|
| **Version** | 1.2.0 |
| **Status** | draft |
| **Generated** | 2026-08-03 |
| **Changelog** | [CHANGELOG.md](CHANGELOG.md) |

## Codebase Alignment (verified 2026-08-03)

**Presentation layer**: role-based; see artifact 04 — "Role-Based Routing &
Navigation": Files, Patient, Viewer, Metrics; Admin tab only with `USER_ADMIN`;
share-link mode hides everything but the Image tab.

**Implemented**: viewer + tools, multi-series navigation, annotations (client sync;
persistence endpoint to confirm), metadata/change history, patient context, share
links, audit. **GATED**: structured reporting (FR-R12-09), critical-findings
escalation (FR-R12-10), attending-review queue (FR-R12-12), priors endpoint
(FR-R12-06), peer review — no reporting backend exists (largest gap).

## Role Summary

**Persona**: Staff radiologist interpreting studies and producing reports.
**Access tier**: Clinical reading — `STUDY_READ`, `WORKLIST_READ`, `PATIENT_READ`, `FILE_READ` (+ share/annotation capabilities).
**Context**: High-volume reading sessions at a workstation; prioritizes speed and accuracy; heavy keyboard use; relies on priors, measurements, and structured reporting.

## Artifact Index

| # | Artifact | File |
|---|----------|------|
| 01 | User Requirements | `01-user-requirements.md` |
| 02 | End-to-End Workflow Maps | `02-workflow-maps.md` |
| 03 | User Stories | `03-user-stories.md` |
| 04 | UI/UX Requirements | `04-ui-ux-requirements.md` |
| 05 | Metrics & SLAs | `05-metrics-slas.md` |
| 06 | Acceptance Criteria (validator-gated) | `06-acceptance-criteria.md` |
| 07 | Traceability Matrix | `07-traceability.md` |
| 08 | Implementation Roadmap | `08-implementation-roadmap.md` |

## Cross-Role Dependencies

- **R04 Service Coordinator** — prioritizes/assigns studies into the reading worklist.
- **R06/R07 Technologist/Technician** — complete exams (MPPS) that enter the reading queue.
- **R13 Resident** — drafts under R12 supervision (attending review workflow).
- **R18 Teleradiologist** — shares the reading worklist in off-hours (preliminary vs final).
- **R03 Service Director / R05 QA** — consume reading KPIs (turnaround, quality scores).
- **R14 Referring Clinician** — receives R12's reports.
- **R15/R16 RIS/EMR** — report delivery channels.

## Grounding Sources

- Viewer frontend: `frontend/src/detail/` (`Detail.tsx`, `CornerstoneElement.tsx`, `ThumbnailStrip.tsx`, `MeasurementPanel.tsx`, `KeyboardShortcuts.tsx`, `Management.tsx`, `Changes.tsx`, `Share.tsx`, `viewer/` — camera/tools/useAnnotationSync)
- Study browsing: `frontend/src/dicomweb/StudyBrowser.tsx`; DICOMweb API `backend/api/dicomweb.py` (studies/series/instances with pagination, modality validation)
- Worklist: `frontend/src/worklist/` (`Worklist.tsx`, `CreateEntry.tsx`); API `backend/api/worklist.py` (WORKLIST_READ/WRITE, station AEs)
- Patient: `frontend/src/patient/Patient.tsx`; `backend/api/patient.py`
- Prior docs: `docs/User-Stories.md`, `docs/UX-Functionality.md` (§2.1–2.2 reading), `docs/PRD-v3.md`, `docs/component-specs.md`
- R01/R02 packages (same conventions): `docs/requirements/super-admin/`, `docs/requirements/tenant-admin/`

## Flagged Gaps (backend — must be raised before sprint commitment)

- **Structured reporting** — NO reporting endpoints exist (create/render/sign reports, impression templates). This is the largest gap; entire reporting workflow is pending backend.
- **Priors comparison** — no explicit "load priors for patient" endpoint; currently depends on study search + browser. Confirm behavior.
- **Critical findings escalation** — no escalation endpoint (stat alert to referring clinician); likely via notifications (backend event wiring needed, same as R01/R02 gap).
- **Peer review** — no review/quality workflow endpoints (R05-related).
- **Reading session state** — annotations sync exists client-side (`useAnnotationSync.ts`); confirm persistence endpoint.
