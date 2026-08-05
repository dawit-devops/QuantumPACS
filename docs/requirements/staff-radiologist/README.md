# Requirements Package — R12 Staff Radiologist

| Field | Value |
|-------|-------|
| **Version** | 1.3.0 |
| **Status** | approved |
| **Generated** | 2026-08-03 |
| **Changelog** | [CHANGELOG.md](CHANGELOG.md) |

## Codebase Alignment (verified 2026-08-03)

**Presentation layer**: role-based; see artifact 04 — "Role-Based Routing &
Navigation": Files, Patient, Viewer, Metrics; Admin tab only with `USER_ADMIN`;
share-link mode hides everything but the Image tab. Routes `/reading`,
`/reading/:examId`, `/peer-review` in `frontend/src/index.tsx`; sidebar entries in
`frontend/src/common/Sidebar.tsx`.

**Implemented**: viewer + tools, multi-series navigation, annotations (client sync;
persistence endpoint to confirm), metadata/change history, patient context, share
links, audit. **Reading worklist** (`GET /reports/reading-list` — priority-sorted,
status/modality/search filters, REPORT_READ), **structured reporting**
(`GET/PUT /reports/{exam_id}` with draft → preliminary → final state machine;
`POST /reports/{exam_id}/sign` with REPORT_SIGN, impression requirement, audit log
+ QA notify; `GET /reports/templates` seeded template library per modality —
backend `api/reports.py`, frontend `src/radiologist/ReadingWorklist.tsx`,
`ReportEditor.tsx`), **peer review** (`/peer-reviews/reviewers`,
`/peer-reviews`, `/peer-reviews/{id}`, `/peer-reviews/{id}/submit` — assigned
review of final signed reports with discrepancy level + comment, author notified;
frontend `src/radiologist/PeerReviewInbox.tsx`), **reading presets**
(`/reading-presets` + `/reading-presets/{id}` — per-user window_level + layout
presets per modality, REPORT_READ/WRITE; frontend
`src/detail/viewer/ReadingPresetsPanel.tsx`, `presets.ts`, `useReadingPresets.ts`),
**study-arrival notifications** (`exam.completed` role notification on exam
handoff in `api/exams.py` + `/ws` WebSocket push + NotificationBell).
Permissions: `REPORT_READ/WRITE/SIGN`, `PEER_REVIEW_READ/WRITE` in
`api/permissions.py`; built-in `radiologist` role carries the full reading set.
**GATED**: priors endpoint (FR-R12-06), critical-findings escalation (FR-R12-10),
resident-draft attending-review queue (FR-R12-12 — peer review covers final signed
reports only).

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

- **Priors comparison** — no explicit "load priors for patient" endpoint; currently depends on study search + browser. Confirm behavior.
- **Critical findings escalation** — no escalation endpoint (stat alert to referring clinician); report sign currently notifies the QA role only (`api/reports.py`); escalation wiring pending (same as R01/R02 gap).
- **Resident-draft attending review** — peer review (`/peer-reviews*`) covers final signed reports; the resident-draft review/co-sign queue (R13) is not built.
- **Reading session state** — annotations sync exists client-side (`useAnnotationSync.ts`); confirm persistence endpoint.
