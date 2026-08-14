# Page Overrides — Resident Console (Supervised Viewer + Draft Editor)

> **PROJECT:** QuantumPACS Resident Console
> **Page:** `/reading/:examId` (resident mode) + Draft editor
> **Page Type:** Clinical reading workstation

> ⚠️ Rules here **override** MASTER.md. Extends the existing `ReadingConsole.tsx` / `ReportPanel.tsx` / `CornerstoneElement.tsx` split console — do not build a parallel editor.

---

## Layout

- **Split console** (reuse `ResizableSplit.tsx`): viewer left + right column stack of [Attending Guidance (top, green tint)] → [Report (bottom)].
- Guidance panel collapses with `G` (like `[`/`]` collapses report) → viewer resizes, progressive disclosure.
- Header (reuse console header): Back · Accession · priority/status tags · **supervising attending chip** · autosave indicator · primary action (Submit).

## Resident report state machine (overrides Draft→Preliminary→Final stepper)

`Draft → Submitted (Awaiting Review) → In Review → Final (Co-signed)` — and `Returned for Revision → Draft (unlocked, feedback banner)`. Preliminary/Final are staff-only concepts; hide them from residents.

## Components

- **AttendingGuidancePanel** — green tint (`rgba(16,185,129,.05)`); attending preliminary notes + suggested areas of focus; live "Updated" pulse via `/ws`; placeholder when empty ("Attending guidance not yet available — proceed with independent interpretation").
- **DraftStatusBar** — DRAFT badge (`DraftOutlined`+text), per-section word count + completeness dot, live "Saving… / Saved HH:MM:SS / Unsaved changes" (autosave 3s, `ReadingConsole.tsx`).
- **ReportPanel resident mode** — `Submit for Attending Review` primary button (replaces Sign); `Ctrl+S` manual save; revision-return banner with inline highlighted feedback.
- **Prior toggle** — "Compare priors" in SeriesNavigator area to load earlier study series in the same console.

## Keyboard map (add to `KeyboardShortcuts.tsx`)

| Key | Action |
|-----|--------|
| `G` | Toggle attending guidance |
| `Ctrl+S` | Save draft |
| `Ctrl+Enter` | Submit for review (in editor) |
| `N` | Next study (like Sign & Next) |

## States

- **Loading**: viewer `Spin` + guidance/report `Skeleton`.
- **Empty (no guidance)**: placeholder (still read-only usable).
- **Error**: red `Alert` in pane, Retry; draft never lost (autosave retry loop).
- **Disabled**: Submit disabled until impression non-empty AND completeness check passes.

## A11y

- `aria-label="Attending guidance for study {accession}"`, `aria-label="Draft report for study {accession}"`.
- Screen-reader announce: "Draft auto-saved", "Study {accession} assigned — attending Dr. {name}".
- Mobile (<768): guidance collapses to bottom-sheet; report full-screen; touch targets 44px.
