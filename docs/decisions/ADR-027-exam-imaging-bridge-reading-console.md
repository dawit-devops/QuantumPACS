# ADR-027: Exam→Imaging Bridge and the Split Reading Console

## Status
Accepted

## Date
2026-08-13

## Context

Reading flow before this change: the radiologist clicked a handed-off exam on
the reading worklist (`/reading`, backed by `Reports.reading_list`) and was
taken to a **text-only** report page (`ReportEditor` at `/reading/:examId`).
Imaging lived in a separate module: the detail viewer (`frontend/src/detail`,
keyed by a `FileRecord` id) opened studies by browsing the file tree, never
from an exam. The exam and the DICOM store were bridged only by shared tags —
an exam carries `accession_number` + `patient_id` (MRN) and the modality
stored the study under that same accession — but no code connected them.

This forced a multi-window workflow: open the exam to write the report, then
separately find the study in the viewer to look at images. That breaks the
radiologist's core loop and is the most common PACS usability complaint
(PRD-v3 R12). The design spec `specs/reading-console_design.md` (Phase 4)
requires viewer + report on one screen, series navigation in-console, a
resizable split, `[`/`]` report-pane collapse, and **Sign & Next** returning
to the worklist.

## Decision

### (a) Backend: `GET /api/v2/reports/{exam_id}/images`

A new `ExamImagesHandler` in `backend/api/reports.py` resolves an exam's
DICOM tree:

- Looks up the exam by id (404 if absent), then matches
  `studies.accession_number = exams.accession_number` **and**
  `patients.patient_id = exams.patient_id` (`_exam_imaging` in
  `backend/api/reports.py`). The MRN is a second key because accessions can
  collide across patients; the accession is required because an exam has no
  study UID until the modality stores data.
- Returns the same `patient.studies[].series[].files[]` tree shape that
  `GET /api/v2/files/{id}` returns (via `Patient.get_extra`), filtered to the
  studies belonging to this exam's accession — priors under other accessions
  stay out of the console.
- Returns `{"data": {"imaging": false}}` when no DICOM exists yet. Front-desk
  exams legitimately reach the worklist before the modality stores anything,
  so "no imaging" is a first-class response, not an error.

Registered at `backend/api/routes.py` under the v2 `/reports/{exam_id}/images`
route, gated `REPORT_READ` like the report endpoints.

### (b) Frontend: `ReadingConsole` reuses the existing viewer unchanged

The route `/reading/:examId` now renders `ReadingConsole`
(`frontend/src/radiologist/ReadingConsole.tsx`), which composes:

- **`CornerstoneElement` unchanged** — the same component `Detail` mounts.
  It is imported via `React.lazy` so the report-only fallback never pulls the
  rendering engine. The console hands it the same props Detail uses (`file`,
  `files`, `changeFile`, `image`, `progressive`, `onAnnotationsChange`,
  `onRequestHelp`, `enableReadingPresets`), where `file` is the selected
  `FileRecord` enriched with the series modality (reading presets) and exam
  patient context (metadata panel). Reuse, not fork: any viewer fix benefits
  both screens.
- **`useExamImaging` hook** — fetches `reports/{examId}` and
  `reports/{examId}/images` in parallel, and keeps
  selected-study/series/file as **id-derived** state so a reload preserves the
  radiologist's place where possible. `changeFile(index)` (slider/arrows) maps
  to the current series' files array.
- **`SeriesNavigator`** — study/series selection and a file slider above the
  viewport, replacing the separate detail-page navigation.
- **`ReportPanel`** — the report content (findings/impression/recommendations,
  templates, autosave, Mark Preliminary, Sign) extracted verbatim from the old
  `ReportEditor`; the editor component and its CSS are deleted.
- **`ResizableSplit`** (dependency-free) — draggable splitter between viewer
  and report, with the ratio persisted in `localStorage` per storage key.
- **`[` / `]`** collapse the report pane to a slim tab; the Sign action lives
  in the console header so it stays reachable while collapsed. A focus guard
  (shared with the viewer) ignores keys inside inputs and antd overlays.
- **Responsive**: below the `md` breakpoint the console stacks viewport over
  report instead of splitting, per the design spec.

### (c) Filter-preserving queue flow: Sign & Next

`ReadingWorklist` serializes its active filters (status, modality, search,
radiologist=me, physician) into the query string when opening an exam
(`/reading/:examId?status=...&search=...`). `ReadingConsole` parses the same
filters out of `location.search` and fetches the identical filtered queue
from `reports/reading-list` on mount. **Sign & Next** then jumps directly to
the next unread exam in that queue — the item after the current one in the
worklist's sort order (STAT → urgent → routine, FIFO within tier; the queue
by construction excludes final-signed exams, so the next item is unread) —
keeping the query string so each successive console keeps the same filters.
When the queue is exhausted (or failed to load) it degrades to navigating
back to `/reading` with the same query. The worklist seeds its filter state
from the URL on mount, so any return lands on the exact queue view left.

### (d) A second bug fix surfaced by the bridge

The console's parallel loading exposed that the WebSocket `open` message could
carry a `wadouri:` URL instead of a file id (`backend/api/ws.py`); the handler
fed it to a bigint-typed `Files.get_extra` lookup and crashed on every viewer
mount. The handler now normalizes file-id and wadouri forms. (Also fixed:
`Reports.reading_list` bound three parameters to a single `$idx` placeholder,
so any worklist search 500'd — the search box had been broken.)

## Alternatives Considered

- **Key the bridge by study UID instead of accession+MRN**: rejected — the
  exam has no study UID until the modality stores data, and the worklist must
  render before that. Accession is the only identifier shared by both
  systems at handoff.
- **Embed the viewer into the old `ReportEditor` page**: rejected — the
  editor had no layout for a viewport, and embedding would have duplicated
  Detail's mounting/annotation wiring instead of reusing `CornerstoneElement`.
- **Frontend joins exams to files client-side** (fetch the full file tree and
  match in the browser): rejected — leaks every patient's imaging to the
  client and duplicates the join in every consumer; the backend bridge is the
  single source of truth.
- **Refuse exams with no DICOM** (`404`/error): rejected — front-desk exams
  with pending imaging are a normal state; the report must still be writable
  in full width.
- **Persist the split ratio server-side**: rejected — it is a per-workstation
  ergonomic preference, not shared state; `localStorage` (the viewer's own
  storage convention) is the right scope.

## Consequences

- **One screen, one workflow**: the radiologist reads images and writes the
  report without leaving the console; Sign & Next flows back to the filtered
  queue.
- **Zero viewer divergence**: `CornerstoneElement` remains the single
  rendering path for both Detail and the console; the console adds a new
  composition, not a new rendering implementation.
- **First-class no-imaging state**: exams pending DICOM store render a
  full-width report with an explanatory banner instead of an empty viewport.
- **New coupling surface**: the bridge depends on exam metadata (`accession`,
  `patient_id`) matching what the modality stored; if ingestion ever stops
  copying those tags, the bridge silently reports `imaging: false`. The
  MRN+accession compound key bounds (but does not eliminate) this risk.
- **Query-string state is the contract** between worklist and console;
  navigating to `/reading/:examId` without a query still works (filters just
  reset, and Sign & Next falls back to the worklist).
- **The console's queue snapshot ages**: Sign & Next reads the queue as of
  console mount; a new exam stored mid-reading appears on the next console's
  (or the worklist's) fetch, not retroactively. Acceptable — the FIFO order
  still holds for the exams the radiologist was looking at.

## References

- PRD-v3.md R12 — Radiologist reading workflow
- `specs/reading-console_design.md` — Phase 4 design spec
- ADR-006: Frontend Architecture — React, Vite, Ant Design, Cornerstone3D
- ADR-018: DICOMweb API (viewer loading path context)
