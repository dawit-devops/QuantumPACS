# Implementation Roadmap — Staff Radiologist (R12)

## Artifact Status Overview

| # | Artifact | File | Status |
|---|----------|------|--------|
| 01 | User Requirements | `01-user-requirements.md` | done |
| 02 | Workflow Maps | `02-workflow-maps.md` | done |
| 03 | User Stories | `03-user-stories.md` | done |
| 04 | UI/UX Requirements | `04-ui-ux-requirements.md` | done |
| 05 | Metrics & SLAs | `05-metrics-slas.md` | done |
| 06 | Acceptance Criteria | `06-acceptance-criteria.md` | done |
| 07 | Traceability Matrix | `07-traceability.md` | partial |
| 08 | Implementation Roadmap | `08-implementation-roadmap.md` | partial |

## FR/NFR Implementation Status

> **Codebase reality (verified 2026-08-03)**: viewer, tools, annotations (client
> sync), metadata/change history, patient context, share links, and audit are
> implemented. Merge 4d136e0 shipped the **reading worklist, structured reporting
> (draft → preliminary → final + sign + templates), peer review, reading presets,
> and study-arrival notifications** (backend `api/reports.py`,
> `api/reading_presets.py`, `api/worklist.py`; frontend `src/radiologist/*`,
> `src/detail/viewer/*`). Still **GATED**: dedicated priors endpoint (FR-R12-06),
> critical-findings escalation (FR-R12-10), resident-draft attending-review queue
> (FR-R12-12 — peer review covers final signed reports only).

### Implemented (Passing ACs)

| FR/NFR ID | Summary | AC Coverage | Effort |
|-----------|---------|-------------|--------|
| FR-R12-01 | Reading worklist (assigned/available studies, priority-sorted) via `GET /reports/reading-list` | AC-R12-01, AC-R12-02 | S |
| FR-R12-02 | Open study in viewer from worklist/study browser (DICOMweb) | AC-R12-03, AC-R12-04, AC-R12-05 | S |
| FR-R12-03 | Full viewer toolset: pan/zoom/WW-WL/measurements + keyboard shortcuts | AC-R12-06, AC-R12-07, AC-R12-08 | S |
| FR-R12-04 | Multi-series navigation via thumbnail strip + keyboard nav | AC-R12-09 | S |
| FR-R12-05 (partial) | Annotation/measurement persistence — client sync exists; server persistence endpoint to confirm | AC-R12-10, AC-R12-11 | M |
| FR-R12-07 | Study metadata, series details, change history | AC-R12-14 | S |
| FR-R12-08 | Patient context (demographics, previous exams) via `/patients/{id}` | AC-R12-24 | S |
| FR-R12-09 | **Structured reporting**: draft → preliminary → final via `GET/PUT /reports/{exam_id}`, sign via `POST /reports/{exam_id}/sign`, template library via `GET /reports/templates` | AC-R12-20, AC-R12-21, AC-R12-30 | L |
| FR-R12-11 | Study state via worklist (`GET/PUT /worklist/{id}`) | AC-R12-18 | M |
| FR-R12-13 | Share studies with colleagues (`/files/{id}/share`) | AC-R12-19 | M |
| FR-R12-14 | Notification of new/urgent studies — `exam.completed` role notification + `/ws` push (NotificationBell) | AC-R12-27 | M |
| FR-R12-15 | Keyboard-driven reading presets — `/reading-presets` + `/reading-presets/{id}` (window_level + layout per modality) | AC-R12-26 | M |
| NFR-R12-01 | Study opens in viewer (first rendered instance) | AC-R12-03 | L |
| NFR-R12-03 | Worklist load | AC-R12-01 | L |
| NFR-R12-04 | Worklist staleness (new/urgent arrivals) | AC-R12-02 | L |
| NFR-R12-05 | Image rendering quality at zoom/pan | AC-R12-08 | L |
| NFR-R12-06 | Keyboard-first operability | AC-R12-14 | L |
| NFR-R12-10 | Report save reliability — autosave flush + dirty-retry (zero lost drafts) in `ReportEditor.tsx` | AC-R12-29 | L |

### Partially Implemented (GATED / Partial)

| FR/NFR ID | Summary | Blocking Dependency | AC | Effort |
|-----------|---------|---------------------|----|--------|
| FR-R12-12 | Attending-review workflow — peer review (`/peer-reviews*`) covers review of **final signed reports** (assign, submit discrepancy + comment, notify author); resident-draft review queue not built | R13 supervised-reading workflow + draft state machine | AC-R12-22, AC-R12-31 | L |

### Missing (Not Started — GATED)

| FR/NFR ID | Summary | Blocking Dependency | AC | Effort |
|-----------|---------|---------------------|----|--------|
| FR-R12-06 | Dedicated priors comparison endpoint | No priors API — depends on study search today | AC-R12-12, AC-R12-13 | M |
| FR-R12-10 | Critical-findings escalation | No escalation endpoint/notification wiring (sign notifies QA role only) | AC-R12-16, AC-R12-17 | M |
| NFR-R12-02 | Series/instance navigation response (INP) | Blocked on viewer perf work | — | L |
| NFR-R12-07 | WCAG 2.1 AA where applicable | Not yet scoped | — | L |
| NFR-R12-08 | Viewing continues during ES outage | ES-degrade path exists; formal test pending | — | L |
| NFR-R12-09 | Concurrent sessions | Not yet scoped | — | L |

## Blocking Dependencies

| Blocking Dependency | Blocks | AC | Impact |
|---------------------|--------|----|--------|
| Escalation + notification wiring for critical findings | FR-R12-10 | AC-R12-16, 17 | Critical-findings alerts cannot ship |
| Priors API decision | FR-R12-06 | AC-R12-12, 13 | Confirm dedicated priors endpoint vs study search + browser |
| Resident-draft attending-review workflow (R13) | FR-R12-12 | AC-R12-22 | Peer review exists; draft co-sign/supervision queue pending |

## Next Steps (highest priority)

1. **Raise critical-findings escalation with backend** — unblocks FR-R12-10; M effort
2. **Confirm priors API decision** — resolves FR-R12-06; M effort
3. **Scope resident-draft attending-review queue with R13** — peer review slice is shipped; draft-review workflow pending; L effort
4. **Confirm annotation persistence endpoint** — resolves FR-R12-05 partial status; M effort
5. **Update roadmap each sprint** as FR/NFR status changes
