# User Requirements — Staff Radiologist (R12)

## Functional Requirements

| ID | Requirement | Priority | Notes |
|----|-------------|----------|-------|
| FR-R12-01 | The system SHALL present the radiologist a reading worklist of studies assigned/available for interpretation, sorted by priority (STAT first) with modality, patient, exam, and time info. | Must | `GET /reports/reading-list` (REPORT_READ), fed by exam handoff (R06) |
| FR-R12-02 | The system SHALL allow the radiologist to open a study in the viewer from the worklist or study browser, rendering series/instances via DICOMweb. | Must | `GET /dicomweb/studies/{uid}` chain, `Detail.tsx` |
| FR-R12-03 | The system SHALL provide full viewer toolset: pan, zoom, window/level, and measurements (length, rectangle ROI, ellipse ROI, angle, arrow) with keyboard shortcuts (keys 1–7/E). | Must | `KeyboardShortcuts.tsx`, `viewer/tools.ts` |
| FR-R12-04 | The system SHALL support multi-series navigation via thumbnail strip with keyboard navigation (arrow keys, page up/down). | Must | `ThumbnailStrip.tsx` |
| FR-R12-05 | The system SHALL persist annotations/measurements per study and re-load them on reopening (client sync via `useAnnotationSync`). | Should | Confirm backend persistence endpoint |
| FR-R12-06 | The system SHALL allow the radiologist to view priors for the same patient with one action (dedicated priors list/load). | Should | GAP: confirm priors endpoint |
| FR-R12-07 | The system SHALL allow the radiologist to view study metadata, series details, and change history. | Must | `Detail.tsx`, `Changes.tsx`, `files/{id}/changes` |
| FR-R12-08 | The system SHALL allow the radiologist to access patient context (demographics, previous exams). | Must | `patient/Patient.tsx`, `GET /patients/{id}` |
| FR-R12-09 | The system SHALL provide structured reporting: create, edit, save, and sign reports (findings, impression, templates). | Must | `GET/PUT /reports/{exam_id}` (draft → preliminary → final), `POST /reports/{exam_id}/sign`, `GET /reports/templates` |
| FR-R12-10 | The system SHALL allow the radiologist to flag critical findings, triggering escalation/notification to the referring clinician. | Should | GAP: escalation endpoint + notification wiring |
| FR-R12-11 | The system SHALL allow the radiologist to manage study state (claimed/reading/done) with read-state indicators visible to the department. | Should | Worklist state via `GET/PUT /worklist/{id}` |
| FR-R12-12 | The system SHALL support the attending-review workflow: resident drafts → radiologist reviews, annotates, and signs. | Should | Partial: `/peer-reviews*` covers review of final signed reports; resident-draft attending-review queue not built |
| FR-R12-13 | The system SHALL allow sharing studies with colleagues (read-only or annotation) for consultation. | Should | `Share.tsx`, `/files/{id}/share` |
| FR-R12-14 | The system SHALL surface notification of new studies / urgent studies (e.g., STAT arrivals) in the worklist. | Should | `exam.completed` role notification + `/ws` push (NotificationBell) — implemented |
| FR-R12-15 | The system SHALL allow the radiologist to create and reuse keyboard-driven reading presets (window/level presets per modality, layout presets). | Could | `/reading-presets` + `/reading-presets/{id}` CRUD (window_level + layout per modality) — implemented |

## Non-Functional Requirements

| ID | Requirement | Target | Measurement |
|----|-------------|--------|-------------|
| NFR-R12-01 | Study opens in viewer (first rendered instance) | ≤ 2s p90 on LAN | Synthetic probe |
| NFR-R12-02 | Series/instance navigation response (INP) | ≤ 200ms p75 | RUM |
| NFR-R12-03 | Worklist load | ≤ 2s p90 | Synthetic probe |
| NFR-R12-04 | Worklist staleness (new/urgent arrivals) | ≤ 30s | Synthetic probe |
| NFR-R12-05 | Image rendering quality at zoom/pan | No re-fetch of full-frame for pan within loaded window; smooth at 60fps | Performance instrumentation |
| NFR-R12-06 | Keyboard-first operability | 100% of reading actions reachable without mouse | Keyboard-pass test |
| NFR-R12-07 | WCAG 2.1 AA where applicable | Zero serious axe violations (non-viewer UI) | axe-core |
| NFR-R12-08 | Viewing continues during ES outage | Viewer/study load unaffected by ES | Failure-injection test |
| NFR-R12-09 | Concurrent sessions | 50 concurrent reading sessions (existing requirement) | Load test |
| NFR-R12-10 | Report save reliability | Autosave ≤ 10s cadence; no lost drafts on connection drop | Integration test |

## Codebase Status (verified 2026-08-03)

**Implemented**: viewer + tools, multi-series navigation, annotations (client sync;
persistence endpoint to confirm), metadata/change history, patient context, share
links, audit. **Reading worklist** (`GET /reports/reading-list`), **structured
reporting** with templates/autosave/sign (`GET/PUT /reports/{exam_id}`,
`POST /reports/{exam_id}/sign`, `GET /reports/templates`), **peer review**
(`/peer-reviews*` — final signed reports), **reading presets**
(`/reading-presets*`), and **study-arrival notifications** (`exam.completed` +
WebSocket) shipped with merge 4d136e0. **GATED**: dedicated priors endpoint
(FR-R12-06), critical-findings escalation (FR-R12-10), resident-draft
attending-review queue (FR-R12-12 — peer review covers signed reports only). See
artifacts 04/07/08.

## Assumptions & Constraints

- **Reading is desktop-only**: viewer is not responsive to mobile; worklist may be usable on tablet.
- **Performance is clinical-safety-critical**: NFR-R12-01/02/05 are hard budgets; image loading is the primary pain point.
- **Escalation and priors remain gated**: FR-R12-06 (priors endpoint) and FR-R12-10 (critical-findings escalation) still need backend work; the resident-draft attending-review queue (FR-R12-12) is only partially covered by the peer-review workflow.
- **PHI**: full clinical access; audit logging of report actions required (R01/R02 audit patterns).
- **Search**: ES down → search degrades; worklist and direct study open must still work.
- **Annotations**: client-side sync exists; persistence backend must be confirmed before sprint commitment.
