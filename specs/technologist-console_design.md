# Feature: Technologist Acquisition Console — UX Review & Enhancement Spec

Author: Technologist role review (wear-the-hat pass)
Date: 2026-08-13
Audience: dev team (frontend + backend)

## Purpose

This document is a working-hat critique of the current technologist UI
(`TechnologistWorklist`, `ExamConsole`, `SimulatedPreview`) written from the
perspective of a technologist operating a busy modality room. It lists what
exists, what works, what a real technologist would fight with, and a
prioritized set of concrete changes the team can pick up. Each item is
scoped to existing files/components so it can be planned without new
architecture.

## 1. Current State (what is implemented)

| Screen | Route | File | Implements |
|--------|-------|------|-----------|
| Technologist Worklist | `/exams` | `frontend/src/technologist/TechnologistWorklist.tsx` | Auto-refresh (30s, visibility-gated), status tabs with live counts, modality filter, patient/accession search, STAT pulse tag, `sessionStorage` filter persistence across back-nav, completed-handoff banner, priority sort |
| Exam Console | `/exams/:id` | `frontend/src/technologist/ExamConsole.tsx` | Patient identity verification, protocol select + start, modality workflows (CT/MR/PET/US/MG/DX sequence lists), simulated acquisition with dose params, QA accept/reject (reason modal), dose documentation with ACR benchmark progress, safety-checks record, complete + handoff, incident log modal, emergency override modal, read-only mode for `EXAM_READ`-only |
| Simulated preview | — | `frontend/src/technologist/SimulatedPreview.tsx` | Canvas "CT phantom" with window/level sliders, quality variants (good/noisy/artifact) |
| QA surfaces | `/qa/queue`, `/qa/review/:examId` | `frontend/src/qa/QAQueue.tsx`, `QAReviewForm.tsx` | Post-completion QA review queue, shared with QA roles |

Permissions: routes gated `EXAM_READ` (`index.tsx`), write actions gated
`EXAM_WRITE` via `hasPermission`; sidebar "Exams" item under Acquisition
workspace. Tests: `ExamConsole.test.tsx` (10 cases), `TechnologistWorklist.test.tsx`,
e2e `worklist-flow.spec.ts` seeds as `test.technologist`.

**What is already good (keep):**
- Filter persistence across the worklist → console → back loop via
  `sessionStorage` (R06 UX requirement).
- Read-only rendering for viewers (nurse/resident) — write affordances
  hidden, not shown-then-rejected.
- STAT priority sort + pulsing tag with `prefers-reduced-motion` honored.
- Visibility-gated 30s polling (no work when tab hidden; refetch on return).
- Per-status counts without disrupting the visible table.
- ACR benchmark dose progress bar with exception/active/normal states.

## 2. Critique — what a technologist would hit (by severity)

### P0 — Misleading / potentially unsafe

**C1. The window/level sliders do nothing.**
`SimulatedPreview.tsx` renders `wl.window`/`wl.level` into labels and the
slider values, but the canvas pixels are drawn with fixed gray shades — the
`wl` values never touch the image. A technologist dragging W/L sees numbers
change and the image stay identical. Worse than no control: it trains
distrust. Fix: either apply the window/level transform to the phantom (one
`ctx.getImageData` remap) or remove the sliders until the real viewport
lands.

**C2. No re-acquire / retake flow after a reject.**
`decideAcquisition(acqId, 'reject')` removes the acquisition from the pending
queue and is done. FR-R06-04 requires: *"Rejects trigger an on-screen alert
and require re-acquisition."* A technologist rejecting a motion-affected
series has no "Retake" — they must manually bump the series and re-acquire,
with no link between the rejected series and the retake. Rejection also
never surfaces the incident-logging path (FR-R06-08) even though
positioning/artifact/motion rejections *are* incidents.

### P1 — Workflow friction

**C3. The console is a vertical card stack, not an acquisition console.**
Everything is a full-width `Card` stacked down the page: identity, protocol,
acquisition, dose, safety, complete. On a 1080p screen the acquisition
preview is below the fold and the dose panel is a separate scroll away. R06
UI/UX spec (04-ui-ux-requirements.md S-R06-03/04) calls for a full-screen
acquisition view with the image front-and-center and dose in a persistent
side panel. A technologist glances between the patient, the image, and the
dose continuously — they need a 2-column or 3-column layout, not scroll.

**C4. No prior-study link at identity verification.**
FR-R06-02: *"If the patient has a prior study, display a 'Prior Study'
indicator with comparison link."* The identity card shows demographics only.
Comparison to a prior study is a core technologist sanity-check (is this the
right patient's anatomy/side?); `Patient.get_extra` already returns prior
studies, so the data exists.

**C5. Safety checks are a single "Record" button with hardcoded answers.**
`recordSafetyChecks` sends `answer: "confirmed"` for all three items
(allergies/pregnancy/renal). A technologist must *verify* each one; a single
all-or-nothing button means the un-verified items are indistinguishable from
the verified ones (FR-R06-06). There is no allergy history display (A5 says
EMR allergy data is expected) and no radiation warning treatment for the
pregnancy item.

**C6. Dose panel is a snapshot, not a per-series ledger.**
Cumulative totals + ACR % bar are shown, but there is no per-series table
(DLP per acquisition), no count of exposures, no "approaching benchmark"
warning state on the panel itself (the bar handles it, but the numbers don't
color). FR-R06-05 asks for cumulative dose *across the encounter* with a flag
when the benchmark is exceeded — the flag is only the bar status.

### P2 — Efficiency & polish

**C7. No new-exam arrival UX on the worklist.**
The 30s poll brings new assignments in silently (rows just change under the
cursor). NFR-R06-06 / the R06 a11y spec call for an announcement: "Exam
{accession} assigned" (aria-live) and a visual cue on the new row. The
radiologist side already does fade-in/STAT top-insert patterns in its spec —
mirror them here.

**C8. No `Ctrl+Shift+W` worklist shortcut.**
R06 UI/UX spec lists it as a secondary entry point. There is no keyboard
shortcut infrastructure on the technologist side at all (the radiologist
console has `[`/`]` + a shortcuts dialog to model after).

**C9. Worklist shows no "time in queue".**
A technologist triages by how long a ready/STAT exam has been waiting. The
table shows `completed_at` (handoff time) but not an elapsed/waiting column,
and no "needs attention" styling as exams age.

**C10. The modality "Worklist" sidebar item vs "Exams" is confusing.**
Sidebar shows both `Worklist` (the DICOM modality worklist, `/worklist`) and
`Exams` (the R06 exam list, `/exams`) under Acquisition. A technologist will
click the wrong one. Consider renaming `Worklist` → "Modality Worklist" and
`Exams` → "My Exams" (or merging if the modality worklist is not yet
functional).

**C11. No way to preview the actual acquired image from the console.**
The QA queue shows text + dose numbers only. The technologist cannot open the
acquired "image" (it's simulated, but the seam exists: `Detail`/`CornerstoneElement`
already render real DICOM at `/files/:id`, and the reading console just
proved `CornerstoneElement` is reusable). At minimum, the QA item should be a
thumbnail; the real upgrade is mounting the existing viewer for the exam's
acquisition.

## 3. Requirements (EARS format — the "should look" contract)

1. While a technologist works an exam in the console, the system shall keep
   the patient strip, the image viewport, and the dose/QA panel visible
   without vertical scrolling on desktop (≥1024px), per NFR-R06-10.
2. While a technologist adjusts window/level on an acquisition preview, the
   system shall visibly change the rendered image (or hide the control when
   no real viewport exists).
3. While a technologist rejects an acquisition, the system shall offer a
   "Retake" action that (a) records the reject reason, (b) links the
   rejected series to a new acquisition with an incremented series number,
   and (c) offers to log the rejection as an incident (FR-R06-04/08).
4. While a technologist opens an exam whose patient has prior studies, the
   identity card shall show a "Prior Study" indicator linking to the prior
   study in the viewer (FR-R06-02).
5. While a technologist records safety checks, the system shall require
   each check item to be individually confirmed and shall surface a
   radiation warning for the pregnancy item (FR-R06-06).
6. While a technologist acquires images, the dose panel shall list
   per-series dose entries in addition to cumulative totals, and shall flag
   the panel when the ACR benchmark is approached or exceeded (FR-R06-05).
7. While a new exam arrives on the technologist worklist during auto-refresh,
   the system shall announce it (aria-live) and visually distinguish the new
   row (NFR-R06-06, a11y).
8. While a technologist is in the exam area, the system shall support
   `Ctrl+Shift+W` to open the worklist.
9. While a technologist uses the worklist, the system shall show elapsed
   time since handoff for each ready/in-progress exam.
10. While a technologist reviews the QA queue, each pending acquisition
    shall be represented by a thumbnail (or a real viewport once the exam
    has DICOM) rather than text only.

## 4. Architecture (reuse, don't build new)

| Item | Approach | Files |
|------|----------|-------|
| Real viewport in console | Mount the existing `CornerstoneElement` (proven reusable by ReadingConsole) for exams that have DICOM via the exam→imaging bridge (`GET /reports/{exam_id}/images` pattern, but reuse the file-tree endpoint); keep `SimulatedPreview` as the no-DICOM fallback | `ExamConsole.tsx`, `SimulatedPreview.tsx`, `api/files.ts` |
| W/L actually works | Apply window/level remap in `SimulatedPreview` (remap grayscale via `wl` in the pixel loop) or delete the sliders behind the real viewport | `SimulatedPreview.tsx` |
| Retake flow | Backend: acquisitions already carry `series_number` + status; add optional `rejected_reason`/`superseded_by` linkage or reuse `incidents` row. Frontend: QA item gains "Retake" beside "Reject" | `ExamConsole.tsx`, `backend/api/exams.py`, `db/exams.py` |
| Prior-study indicator | `Patient.get_extra` already returns studies; pass `exam.patient_id` prior-study count into the identity card; link to `/files/{priorFileId}` or `/patients/{id}` | `ExamConsole.tsx` |
| Safety checklist | Replace single button with per-item confirm (Checkbox list) + pregnancy radiation `Alert`; send the checked answers, not hardcoded `confirmed` | `ExamConsole.tsx` |
| Per-series dose table | `exam.acquisitions` already carries per-series DLP/CTDIvol; render as a small table above the cumulative summary | `ExamConsole.tsx` |
| Worklist arrival UX | Track previous row set in `TechnologistWorklist`; diff on poll; add `aria-live="polite"` region + row highlight class | `TechnologistWorklist.tsx` + `.css` |
| Keyboard shortcut | `Ctrl+Shift+W` global keydown → navigate `/exams`; reuse the focus-guard pattern from `ReadingConsole` (`[`/`]`) | `TechnologistWorklist.tsx` or shared `hooks.ts` |
| Elapsed time | Client-side from `completed_at` (ticking interval) or a `waiting_since` column if the API exposes it; color-code after thresholds | `TechnologistWorklist.tsx` |
| QA thumbnails | Render `SimulatedPreview` mini (or real thumb via `image` wadouri when DICOM exists) for each pending acquisition | `ExamConsole.tsx` |

**Backend note:** most of this is frontend-only. The only backend touch is the
retake linkage (acquisitions) — and that could be deferred: a first cut can
record retakes purely by incrementing `series_number` client-side and logging
the reject reason on the existing `incidents` table.

## 5. Suggested build order (dev-team sprints)

1. **Sprint A (P0, small):** C1 — W/L actually transforms the phantom (or
   hides sliders). C2 — Retake button + reject-reason → incident offer.
2. **Sprint B (P1, medium):** C3 — 2/3-column console layout (patient strip
   top; viewport center; dose/QA right rail). C4 — prior-study link. C5 —
   interactive safety checklist + pregnancy warning.
3. **Sprint C (P2, small/medium):** C6 — per-series dose table. C7 — arrival
   announcement + row highlight. C8 — `Ctrl+Shift+W`. C9 — elapsed-time
   column. C10 — sidebar rename.
4. **Sprint D (stretch):** C11 — real `CornerstoneElement` viewport in the
   console via the exam→imaging bridge, replacing `SimulatedPreview` when
   DICOM exists. This is the payoff item and the natural follow-up to the
   reading console work.

## 6. Acceptance criteria (what "done" looks like)

- A technologist can complete a full exam without scrolling on a 1080p
  desktop (identity → protocol → acquire → QA → dose → safety → complete).
- Dragging W/L visibly changes the preview; controls never mislead.
- A rejected acquisition offers Retake; the retake appears as the next
  series; the reject reason is recorded and optionally logged as an incident.
- Identity card links prior studies; safety checks are individually
  confirmable with a pregnancy radiation warning.
- Dose panel lists per-series entries and flags benchmark approach/exceed.
- New worklist arrivals announce via aria-live and highlight the new row.
- `Ctrl+Shift+W` opens the worklist from anywhere in the exam area.
- Existing `ExamConsole.test.tsx` / `TechnologistWorklist.test.tsx` suites
  stay green; new cases cover retake, safety per-item, arrival diff, and
  shortcut.
