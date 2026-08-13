# Feature: Split Reading Console (images left · report right)

## Current State

`/reading/:examId` renders `ReportEditor` (`frontend/src/radiologist/ReportEditor.tsx`) — a text-only page. The Cornerstone3D viewer lives on a different route, `/files/:id` (`frontend/src/detail/Detail.tsx`), which resolves a study/series/file tree from `getFile()` (`frontend/src/api/files.ts`) and mounts `CornerstoneElement` (`frontend/src/detail/CornerstoneElement.tsx`).

A radiologist must therefore juggle two tabs to read + report: the Report Editor (text) and the Files viewer (images). The report has a complete lifecycle already — draft/preliminary/final steps, template application, 3s autosave, sign gating on non-empty impression (`ReportEditor.tsx`, FR-R12-09) — but it is decoupled from the images.

The viewer is already radiologist-ready and reusable as-is: `CornerstoneElement` accepts `file`, `files`, `changeFile`, `image` (wadouri), `enableReadingPresets`, `onAnnotationsChange`, `focusAnnotationUID`, and gates the reading-presets panel + layout grid on `REPORT_READ` (`CornerstoneElement.tsx` + `detail/viewer/useReadingPresets.ts`).

**The gap:** an `exam` (UUID, has `accession_number`) is not linked to `files`/`studies`/`series` in the API today. `Detail` gets its tree from `getFile(id)` by file id; there is no way to resolve imaging from an exam id. The console needs that bridge plus a report pane docked beside the viewer.

## Requirements (EARS Format)

While a radiologist opens an exam from the reading worklist, when the exam has DICOM available, the system shall render the viewer (left pane) and report editor (right pane) on the same screen.
While the reading console is open, when the radiologist switches series, the system shall load the selected series in the viewport without leaving the console.
While the reading console is open, when the radiologist signs the report, the system shall return them to the reading worklist with their filters preserved.
While the reading console is open, when the report pane is collapsed, the system shall keep the Sign action available in the console header.
While the reading console is open, when no DICOM matches the exam, the system shall render the report in full-width with a "no imaging available" notice instead of an empty viewport.
While a user without `REPORT_READ` opens the console, the system shall keep the route closed (existing `ClinicalRoute` gate).

## Architecture

### [Backend] — One new endpoint

**New `GET /api/v2/reports/{exam_id}/images`** (gated `REPORT_READ`, in `api/reports.py`):

- Resolves the exam via `Exams(conn).get(exam_id)` (`backend/db/exams.py`).
- Resolves the DICOM tree by joining `files` → `studies` on `accession_number = exam.accession_number` (and patient id), reusing the row→tree shape that `Detail` already consumes (`FileRecord.patient.studies[].series[].files[]`, `frontend/src/api/files.ts`).
- Returns `{ study, series, files }` or a `{ imaging: false }` marker when no match (exams from the front-desk flow may legitimately have no DICOM yet).

| Component | Status | File |
|-----------|--------|------|
| `ExamReportHandler.get()` — exam + report | ✅ Existing | `api/reports.py` |
| `ExamImagesHandler` — exam → imaging tree | 🔧 New | `api/reports.py` + route in `api/routes.py` |
| `Exams.get()` — exam row lookup | ✅ Existing | `db/exams.py` |
| Files/studies/series tree shape | ✅ Existing | `db/files.py`, `db/study.py` (same joins `Detail` uses) |

**Open question (verify before S2):** accession-number join coverage on existing data. If accession numbers do not reliably match between `exams` and `files`/`studies`, add a backfill or an `exam_id` → `study_id` mapping migration.

### [Frontend] — New console, reused viewer + extracted report

**Route change** (`frontend/src/index.tsx`): `/reading/:examId` element swaps `ReportEditor` → `ReadingConsole` (same `ClinicalRoute permission="REPORT_READ"` gate).

**New components:**

| Component | File | Role |
|-----------|------|------|
| `ReadingConsole` | `frontend/src/radiologist/ReadingConsole.tsx` | Owns all state; composes header + split + panes; handles `Sign & next` |
| `ResizableSplit` | `frontend/src/common/ResizableSplit.tsx` | Dependency-free pointer-event splitter (flex-basis + localStorage persistence); no splitter library added |
| `SeriesNavigator` | `frontend/src/radiologist/SeriesNavigator.tsx` | Series dropdown + file slider (lifts what `Detail` builds in breadcrumbs, `Detail.tsx`) |
| `ReportPanel` | `frontend/src/radiologist/ReportPanel.tsx` | **Extracted** from `ReportEditor` — templates, Findings/Impression/Recommendations, autosave, status steps, sign modal |
| `useExamImaging` | `frontend/src/radiologist/useExamImaging.ts` | Fetches `reports/{examId}` + `reports/{examId}/images` in parallel; holds `selectedSeries`/`selectedFile` |

**Extraction rule:** `ReportEditor` keeps its route shell (back button, loading/error states); all report *content* moves into `ReportPanel` receiving `{ exam, report, canWrite, canSign }` + change callbacks. `ReportEditor` is deleted once the console lands (no route change needed — same path).

### Component tree

```
/reading/:examId
└── ReadingConsole (withSidebar)
    ├── ConsoleHeader exam report onSign onNext
    ├── ResizableSplit left=<ViewportPane/> right=<ReportPane/>
    │     ├── ViewportPane
    │     │     ├── SeriesNavigator            (new — series dropdown + slider)
    │     │     ├── CornerstoneElement         (REUSED, unchanged)
    │     │     │     ├── ReadingPresetsPanel  (already inside, REPORT_READ-gated)
    │     │     │     ├── CompanionViewportGrid(already inside)
    │     │     │     └── ThumbnailStrip       (already inside)
    │     │     └── MeasurementPanel           (REUSED from Detail)
    │     └── ReportPane (role="complementary")
    │           └── ReportPanel                (extracted from ReportEditor)
    └── KeyboardShortcuts                      (REUSED) + pane-toggle key

Hooks:
├── useExamImaging(examId)        (NEW)
├── useReadingPresets(...)        (REUSED — pass file.modality)
└── useAnnotationSync(...)        (REUSED inside CornerstoneElement, unchanged)
```

### Data flow — exam → viewport props

`useExamImaging(examId)` derives the exact props `CornerstoneElement` already expects:

| CE prop | Source |
|---|---|
| `file` | selected `FileRecord` (has `id`, `modality`, `tools_state`) |
| `files` | `selectedSeries.files` (slider + thumbnail strip) |
| `image` | `wadouri:${API_URL}/files/${file.id}/data` (same pattern as `Detail.tsx`) |
| `changeFile` | set `selectedFile` to sibling within series |
| `enableReadingPresets` | `hasPermission("REPORT_READ")` → true |
| `onAnnotationsChange` | feed `MeasurementPanel` |
| `visible` | always true on this route |

### Reuse inventory (nothing rebuilt)

| Concern | Reused from | Status |
|---|---|---|
| Image rendering, tools, W/L, layouts, annotations | `CornerstoneElement` + `detail/viewer/*` | unchanged |
| Per-modality reading presets | `useReadingPresets` | unchanged |
| Measurements panel + CSV | `MeasurementPanel`, `parseAnnotations` | unchanged |
| Series thumbnails / instance slider | `ThumbnailStrip`, CE Slider | unchanged |
| Keyboard shortcuts (1–9, R/H/V/I, P/L/S/C/F, arrows) | `KeyboardShortcuts` + CE key handler | unchanged |
| Report lifecycle (draft/prelim/final, autosave, templates, sign gating) | `ReportEditor` internals | extracted, not rewritten |
| RBAC | `ClinicalRoute` + `REPORT_READ/WRITE/SIGN` | unchanged |

### New behavior (thin layer only)

1. **Series switching in-console** — `SeriesNavigator` swaps `selectedSeries` and resets `selectedFile` to its first instance; CE's image-swap effect handles the rest (`setStack`, `cache.purgeCache`).
2. **Sign & next** — after `signReport()` succeeds, navigate to `/reading` with worklist filters preserved in the query string (v1; a next-exam cursor can come later).
3. **Report pane toggle** — `[` / `]` collapses the report to a slim vertical tab; `Sign Report` moves to the header while collapsed. Console key handler must reuse the CE input/overlay focus guard pattern (never steal keys inside inputs, `.ant-select`, dialogs).
4. **Collapsible metadata** — reuse CE's built-in `Metadata` collapse.

### Responsive & accessibility

- `Grid.useBreakpoint()` (already used in `Detail`): below `md`, stack vertically — viewport on top (min-height 55vh), report below.
- Splitter is dependency-free (~40 lines: pointer events + flex-basis, stored in localStorage per user). `react-resizable-panels` is the fallback if keyboard-resize is required for free.
- Keep CE's `role="application"` viewport + `aria-live` readouts. Add `aria-label` to the splitter handle ("Resize report panel") and `role="complementary"` on `ReportPane`.
- Screen-reader ordering: report pane after the viewport in the DOM (right sibling) — tab order is viewport → series nav → report.

## Security

| Check | Status |
|-------|--------|
| Auth required | ✅ New images endpoint behind `REPORT_READ` (`@requires_permission`) |
| Route gate | ✅ `/reading/:examId` keeps existing `ClinicalRoute` (`REPORT_READ`, clinical roles only) |
| PHI exposure | ✅ Images served via the same wadouri `/files/{id}/data` path + auth middleware; no new storage path |
| Input validation | ✅ `exam_id` path param validated by existing handler patterns; Pydantic schemas on report PUT unchanged |
| Tenant isolation | ✅ Endpoint resolves through `get_conn()` + `effective_tenant` like sibling report endpoints |
| Audit logging | ✅ Existing `report.saved` / `report.signed` events unchanged |
| Accessibility of new controls | ✅ Splitter handle + report pane labeled (see above) |

## Implementation Plan

### Phase 1: Report extraction + console shell (no backend changes)

- [ ] **1a**: Extract `ReportPanel` from `ReportEditor` (templates, three text areas, autosave, status steps, sign modal)
- [ ] **1b**: Add `ReadingConsole` rendering header + report-only (images endpoint stubbed → full-width report + "no imaging available" notice)
- [ ] **1c**: Keep existing `ReportEditor.test.tsx` suite green against `ReportPanel`

### Phase 2: Images bridge

- [ ] **2a**: Backend `reports/{exam_id}/images` endpoint + route registration
- [ ] **2b**: `useExamImaging` hook; `ViewportPane` mounts real `CornerstoneElement`
- [ ] **2c**: Verify exam↔study accession join on existing data; backfill or mapping migration if coverage is insufficient

### Phase 3: Split + series navigation

- [ ] **3a**: `ResizableSplit` (dependency-free) + `SeriesNavigator`
- [ ] **3b**: Report pane collapse (`[`/`]`) + `Sign Report` in collapsed header
- [ ] **3c**: `Sign & next` returning to `/reading` with filters preserved

### Phase 4: Verify & polish

- [ ] **4a**: Run `tsc --noEmit` and `vite build`
- [ ] **4b**: E2E — worklist → console → series switch → measure → template → sign → back to worklist
- [ ] **4c**: Responsive check at <576px; unit tests for `ResizableSplit` + `SeriesNavigator`
