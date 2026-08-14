# Page Overrides — Supervised Worklist

> **PROJECT:** QuantumPACS Resident Console
> **Page:** `/reading` (resident mode) — extends `ReadingWorklist.tsx`
> **Page Type:** Data-dense worklist

---

## Layout

- Same filter bar + Table as `ReadingWorklist.tsx`; **replace 30s polling with `/ws` push** (subscribe `reading-list.changed` / `exam.completed` via `ws.ts`; keep polling as fallback). Last-updated timestamp + "live" pulse.
- **STAT rows**: 4px left border `--color-error` + pulsing dot + `STAT` text tag (AC-R13-01). Optional audio toggle (default on for STAT/urgent).
- **PHI minimization** (A1): Patient column = initials + MRN last-4; full name revealed on open (tooltip or hover) only.
- Row double-click / Enter opens console (existing).

## Columns (add to existing)

| Column | Change |
|--------|--------|
| Priority | Keep tags; add left border/pulse for STAT |
| Patient | Initials + MRN-4 |
| **Supervising Attending** | NEW — `Dr. {name}` chip |
| **Supervision Status** | NEW — badge: Pending / In Review / Returned / Co-signed |
| Report | Keep status badge |
| Action | Read / Continue / **Submit for Review** (when draft ready) |

## States

- **Loading**: skeleton rows (existing).
- **Empty**: "No studies assigned to you" + "Assign exams to me" hint + refresh CTA (better than current wall-of-text locale).
- **Error**: red banner + Retry (existing pattern).
- **New arrival**: subtle toast/sound "Study {accession} assigned" + row flash.

## A11y / Responsive

- Rows keyboard-focusable, Enter opens (existing `onRow`).
- Mobile (<768): card-list layout, no horizontal scroll.
- `aria-label="Supervised worklist for {resident_name}"`.
