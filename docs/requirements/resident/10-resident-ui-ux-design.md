# UI/UX Design — Radiology Resident (R13) Supervised Reading Surface

**Author**: UI/UX designer (picking up `09-resident-hat-review-handoff.md`)
**Date**: 2026-08-14
**Stack**: React + Ant Design v6 + Cornerstone3D (Vite)
**Design system**: extends live tokens in `frontend/src/common/tokens.css` + `theme.ts`; persisted master + page overrides in `design-system/quantumpacs-resident-console/` (MASTER.md, pages/resident-console.md, pages/supervised-worklist.md)
**Validation**: ui-ux-pro-max (Accessible & Ethical healthcare style; Figtree; data-dense status/priority patterns; bullet/gauge charts with text fallbacks)

---

## 0. Design Direction

- **One system, one role-mode**: do NOT fork the staff console. Reuse `ReadingWorklist.tsx`, `ReadingConsole.tsx`, `ReportPanel.tsx`, `CornerstoneElement.tsx` and flip them into a **resident mode** via `hasPermission`/role — the same surfaces the attending uses, with supervision semantics layered on.
- **Supervision is the brand**: every resident screen answers "where is this in the supervision loop and who is my attending?" — color language from the existing cyan/teal healthcare palette (`#0E7490` primary, teal success, amber warning, red error), with **status tinted rails/badges** that always pair icon + text with color.
- **Trust through feedback**: live autosave state, live guidance "Updated", notification-push (not polling) for worklist — reduce resident anxiety about losing work or missing STAT studies.
- **Keyboard-complete**: the resident's hands are on the mouse + keys; all core actions must have shortcuts (`G`, `Ctrl+S`, `Ctrl+Enter`, `N`).

---

## 1. Design Tokens (additions to `tokens.css` / `theme.ts`)

| Token | Value (light) | Value (dark) | Use |
|-------|---------------|--------------|-----|
| `--resident-draft-bg` | `rgba(8,145,178,0.05)` | `rgba(34,211,238,0.12)` | DRAFT badge + draft editor rail |
| `--resident-guidance-bg` | `rgba(16,185,129,0.05)` | `rgba(52,211,153,0.12)` | Attending guidance panel |
| `--resident-submitted-bg` | `rgba(245,158,11,0.05)` | `rgba(251,191,36,0.12)` | Awaiting-review / returned states |
| `--resident-review-bg` | `rgba(99,102,241,0.05)` | `rgba(129,140,248,0.12)` | In-review state (indigo alt) |
| `--resident-teaching-bg` | `rgba(168,85,247,0.05)` | `rgba(192,132,252,0.12)` | Teaching file components |
| `--resident-feedback-bg` | `rgba(245,158,11,0.05)` | `rgba(251,191,36,0.12)` | Feedback items |
| `--resident-consult-bg` | `rgba(220,38,38,0.05)` | `rgba(248,113,113,0.12)` | On-call consult banner |
| `--stat-border` | `var(--color-error)` | `var(--color-error)` | 4px STAT left border |
| `--focus-ring-color` | `var(--color-primary)` | `var(--color-primary)` | already exists (tokens.css:300) |

Badge rule: **every status = icon + text + color** (never color alone). STAT = red border + pulsing dot + "STAT".

---

## 2. Resident Home (new landing for the `resident` role)

Replaces dumping residents on the staff worklist. Three cards + header; each deep-links.

```
┌────────────────────────────────────────────────────────────────────────┐
│ QuantumPACS · Resident           [ Dr. J. Resident ] [ 🔔 ]  [ 👤 ]   │
│ ┌─────────────────────────┬─────────────────────────┬───────────────┐ │
│ │  My Queue        [Open] │  Feedback & Progress    │ Teaching Lib  │ │
│ │  STAT    2  (red dot)   │  Agreement rate  92% ▓▓▓│  Drafted   12 │ │
│ │  Urgent  5  (amber)     │  Interpreted  47 (bar)  │  Pending    3 │ │
│ │  Routine 12             │  Avg time 9m 40s (line) │  Published  8 │ │
│ │  Attending: Dr. A.      │  ↓ trend (arrow+text)   │               │ │
│ └─────────────────────────┴─────────────────────────┴───────────────┘ │
│  Recent feedback (3 latest items, amber tint, click → dashboard)      │
└────────────────────────────────────────────────────────────────────────┘
```

- **Queue card**: counts by priority with STAT pulse; attending chip; CTA → worklist with `?radiologist=me`.
- **Feedback card**: agreement-rate **bullet chart** (target marker + text %, AAA per chart guidance), interpreted-count bar, avg-time + trend with arrow+text (never color alone).
- **Teaching card**: draft/pending/published counts → teaching library.
- Charts: use existing chart lib (or custom SVG); all values visible as text (not hover-only).

---

## 3. Supervised Worklist (S-R13-01) — `ReadingWorklist.tsx` resident mode

```
[Back: Resident Home]  Reading Worklist — "live" ●  last updated 14:03:22
[Status ▾][Modality ▾][Search patient/accession][Attending ▾] ☑ Assigned to me  [Refresh]
┌─┬─────────┬────────────┬────────┬─────────┬───────────────┬──────────┬───────────────┐
│P│Accession│ Patient    │Modality│Protocol │Supervising    │Status    │Action         │
│█│A2026-01 │J.R. · 4821 │CT      │Chest HR │Dr. A. Singh   │🟡RETURNED│Continue▸ / ↩  │
│ │A2026-02 │M.K. · 1044 │MR      │Brain    │Dr. A. Singh   │🔵DRAFT   │Read Study     │
│█│A2026-03 │T.P. · 7730 │DX      │CXR      │— (coordinator) │⚪PENDING │Read Study     │
└─┴─────────┴────────────┴────────┴─────────┴───────────────┴──────────┴───────────────┘
```
- STAT rows: **4px red left border + pulsing dot** + `STAT` tag; new-arrival toast "Study {accession} assigned — attending Dr. {name}" + optional audio.
- **WebSocket push** (subscribe `reading-list.changed`/`exam.completed` via `ws.ts`), polling fallback 30s; "live" indicator with last-updated.
- **PHI minimized**: Patient = initials + MRN last-4; full name on hover/row-open.
- Supervision Status badge: PENDING / DRAFT / AWAITING REVIEW / IN REVIEW / RETURNED / CO-SIGNED (icon+text).
- Action column: Read / Continue; **Submit for Review** inline when a draft is ready; Returned rows show amber `RollbackOutlined` "Returned" chip with a tooltip → opens console with revision banner.
- Empty: "No studies assigned to you" + "Assign exams to me" CTA (not a bare text locale).
- Keyboard: Tab rows, Enter open; responsive <768 → card list (no horizontal scroll).

---

## 4. Resident Console (S-R13-02 + draft editor S-R13-03) — `ReadingConsole.tsx` resident mode

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ ← Back | Report A2026-01  [STAT] [AWAITING REVIEW]  Dr. A. Singh · saved 14:02│
│                                [G] Guidance  [Submit for Attending Review]   │
├──────────────────────────────────────────┬───────────────────────────────────┤
│ SeriesNavigator  [Compare priors ▾] [Measures]│ ╭─ Attending Guidance ────────╮│
│ ┌────────────────────────────────────┐  │ │ Dr. A. Singh · "Updated" pulse   ││
│ │  Cornerstone viewer                │  │ │ "Compare with 2025 CT chest —    ││
│ │  (progressive, presets, tools)     │  │ │  watch RLL nodule stability.     ││
│ │                                     │  │ │  Suggested focus: lung windows" ││
│ └────────────────────────────────────┘  │ ╰──────────────────────────────────╯│
│  [MeasurementPanel ▸]                  │ ╭─ Draft Report ────────────────────╮│
│                                         │ │ [DRAFT] Findings 214w ●  ✓saved   ││
│                                         │ │ Impression  48w ●                  ││
│                                         │ │ Recommendations 12w                 ││
│                                         │ │ [Template ▾]  [Ctrl+S]  [Submit ▸] ││
│                                         │ ╰───────────────────────────────────╯│
└──────────────────────────────────────────┴───────────────────────────────────┘
```
- **Split** via existing `ResizableSplit.tsx`; right column = Guidance (green tint, top) + Report (bottom). `G` toggles guidance; `[`/`]` collapses report (existing).
- **Guidance panel**: attending preliminary notes + areas of focus; live "Updated" pulse via WS; placeholder when empty ("Attending guidance not yet available — proceed with independent interpretation"); still usable.
- **Resident status stepper**: Draft → Submitted → In Review → Final(Co-signed), with Returned→Draft loop. Preliminary/Final **hidden** for residents (staff-only).
- **DraftStatusBar**: DRAFT badge (icon+text), per-section word count + completeness dot, live autosave indicator — "Saving…" → "Saved HH:MM:SS" → "Unsaved changes" (retry loop on failure; never lose a draft). `Ctrl+S` manual save.
- **Submit for Attending Review** primary button (replaces Sign for residents): disabled until impression non-empty AND completeness check passes; on submit → locks editor, status AWAITING REVIEW, notify attending (≤5s), green toast.
- **Returned for revision**: amber banner with section-linked feedback; report unlocked; feedback highlighted inline.
- **Compare priors**: "Compare priors" entry in SeriesNavigator loads earlier-study series in a companion viewport (reuse `CompanionViewportGrid.tsx`).
- Mobile (<768): guidance → bottom-sheet; report full-screen; 44px targets.

---

## 5. Attending Review Queue (S-R13-04, R12 side) — new

```
Resident Review  —  drafts awaiting co-sign
[Accession | Resident | Modality | Submitted | Status ▾ | Review]
┌─────────┬────────────┬────────┬───────────┬──────────────┬────────┐
│A2026-01 │Dr. J. Res. │CT      │14:01      │AWAITING     │Review ▸│
└─────────┴────────────┴────────┴───────────┴──────────────┴────────┘
```
- Side-by-side modal/route: resident draft findings left, attending editor right, inline comments; **Approve & Co-sign** / **Return for Revision** (section-level feedback modal). Resident notified both ways. (Backend: submit/approve/return endpoints — Phase B of 09.)

---

## 6. Teaching File Capture (S-R13-05) — modal from console

- Thumbnail-strip multi-select (existing `ThumbnailStrip.tsx`) with checkmarks + reorder.
- Fields: key images, findings, diagnosis, differential, key learning points, tags (anatomy/pathology/modality).
- **De-identification** banner (auto-strip PHI tags + burned-in; A4) shown on open.
- Submit for Attending Approval → status PENDING APPROVAL, locked; PUBLISHED badge on approval; RETURNED for revision unlocks with feedback.
- Purple tint (`--resident-teaching-bg`).

---

## 7. Exam List / Portfolio (S-R13-06)

- Filterable table: Date / Accession / Modality / Body Part / Diagnosis / Attending / Review Status / Interpretation Time; filters date-range, modality, body part, diagnosis, attending, review status.
- Metric summary cards: total interpreted, avg interpretation time, draft→final turnaround, **attending revision rate** (text + badge, not color alone).
- **Export CSV** button (columns match residency requirements) with progress feedback.
- Empty: "No studies interpreted yet."

---

## 8. Feedback Dashboard (S-R13-07)

- **Bullet charts** (agreement rate per modality vs target) + **line** (interpretation-time trend) + **bar** (studies by body part) + feedback feed (amber tint, category chips: interpretation / technique / communication).
- Every chart shows values as **text**, targets as markers — AAA, never color-position only.
- Progress toward rotation milestones (Progress bars).
- Access: resident + their attending + program director (R03); not other residents (A7).

---

## 9. On-Call Consult (S-R13-08)

- Modal from console: study prefilled, urgency (routine/urgent/emergent), description.
- Submit → red tint banner "Consult requested — expected response <15m" + notify on-call attending (R12/R18); cannot re-request same study while pending.
- Status lifecycle: REQUESTED → IN PROGRESS → COMPLETED; written guidance saved to study record (chat/screen-share optional later).

---

## 10. Protocol Learning (S-R13-09) & Case Conference (S-R13-10)

- **Protocol Learning**: side panel on protocol select — clinical indication, key sequences + purpose, artifacts, normal variants, red flags; "Mark Reviewed" + progress tracker (reviewed/total, %).
- **Case Conference**: tag study (badge), list view, de-identified **Generate Presentation** (PDF/PPT) export with draft + final report + discussion points; attending approval gate (status APPROVED FOR CONFERENCE).

---

## 11. Interaction & Motion

- Hover/focus transitions 150–300ms (`--duration-fast/normal`, easing standard).
- Pulsing STAT dot: `@keyframes pulse` on the dot only (not layout-shifting); disabled under `prefers-reduced-motion`.
- Autosave indicator transitions between states with fade (250ms).
- Guidance "Updated" pulse: subtle amber dot for 2s, then clears.
- No decorative animation; all motion conveys state (arrival, save, update).

---

## 12. Accessibility (WCAG 2.2 AA)

- Contrast ≥4.5:1 everywhere; tinted bgs keep AA text (use 700-level text colors on tints).
- Full keyboard: worklist Tab/Enter, `G`, `Ctrl+S`, `Ctrl+Enter`, `N`, `[`/`]`, Esc closes modals.
- Focus ring 3px primary on all interactive elements.
- ARIA: `aria-label="Supervised worklist for {resident_name}"`, `aria-label="Attending guidance for study {accession}"`, `aria-label="Draft report for study {accession}"`; live regions announce "Draft auto-saved", "Study {accession} assigned — attending Dr. {name}".
- Status always icon + text + color; touch targets ≥44×44 on touch.

---

## 13. Responsive

| Breakpoint | Behavior |
|------------|----------|
| ≥1024 | Split console: viewer + guidance + report; full tables |
| 768–1023 | Guidance collapsible; stacked dashboard cards |
| <768 | Worklist→card list; guidance→bottom-sheet; report full-screen; teaching modal full-screen; touch targets 44px |

---

## 14. Implementation Mapping (to existing code)

| Screen | Build on | New |
|--------|----------|-----|
| Resident Home | `dashboard/AdminDashboard.tsx` card patterns, `common/StatCard.tsx` | `ResidentHome.tsx` + `/resident` landing in `navigator.ts` (`ROLE_WORKSPACE`) |
| Worklist | `ReadingWorklist.tsx` (+ WS via `ws.ts`, `useTenantRefetch`) | attending column, supervision badge, STAT border, PHI initials |
| Console | `ReadingConsole.tsx`, `ReportPanel.tsx`, `CornerstoneElement.tsx`, `ResizableSplit.tsx` | `AttendingGuidancePanel`, `DraftStatusBar`, resident stepper/submit, prior compare (`CompanionViewportGrid`) |
| Review queue | `PeerReviewInbox.tsx` modal pattern | `AttendingReviewQueue.tsx` (side-by-side) |
| Teaching / Consult / Protocol / Conference | existing `Modal`, `ThumbnailStrip`, `Progress`, `Select` | `TeachingFileCapture.tsx`, `ConsultRequest.tsx`, `ProtocolLearning.tsx`, `ConferencePrep.tsx` |
| Portfolio / Feedback | `common/StatCard.tsx`, chart lib | `ExamListPortfolio.tsx`, `FeedbackDashboard.tsx` |

---

## 15. Dev Hand-off Checklist (acceptance framing)

**Phase A (role + baseline)** — A1 role split/grant; A2 WS push; A3 STAT row; A4 PHI initials.
**Phase B (supervised core)** — B1 attending assignment data; B2 guidance channel + panel; B3 submit/approve/return endpoints + review queue + report-panel re-model (stepper, badge, completeness, `Ctrl+S`, Submit); B4 prior compare.
**Phase C (portfolio/feedback)** — C1 exam log + CSV; C2 feedback dashboard; C3 peer-review → resident feedback loop.
**Phase D (educational)** — D1 teaching files + de-identification; D2 consult; D3 protocol learning; D4 conference export.

Verify per `docs/requirements/resident/06-acceptance-criteria.md` + NFRs (autosave ≤10s, worklist staleness ≤30s, WCAG 2.2 AA, keyboard operability). Start with **B3** (unlocks the persona), then **A2/A3/A4**, then resident-home landing.

---

### References
- Review: `09-resident-hat-review-handoff.md`
- Requirements: `docs/requirements/resident/01–08`
- Persisted design system: `design-system/quantumpacs-resident-console/`
- Live tokens: `frontend/src/common/tokens.css`, `frontend/src/common/theme.ts`, `docs/design-tokens.json`
