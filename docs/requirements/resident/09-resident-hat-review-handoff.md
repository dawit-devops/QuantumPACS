# Resident Hat Review — Walkthrough, Critique & Dev Hand-off (R13)

**Hat**: Radiology resident (R13 persona)
**Date**: 2026-08-14
**Method**: Walked the actual implementation (`frontend/src/radiologist/*`, `frontend/src/detail/*`, `backend/api/reports.py`, `backend/db/roles.py`, `backend/api/permissions.py`, `frontend/src/navigator.ts`) and compared it against the requirements package (`docs/requirements/resident/01`–`08`).
**Output**: Findings + prioritized hand-off backlog for the dev team.

---

## 1. Walkthrough — What a Resident Actually Gets Today (verified)

### 1.1 Identity & permissions
- The `resident` role **exists** (`backend/db/roles.py:19`, `backend/api/permissions.py:367`) but its grants come from **`MATRIX_B_RES`** (`backend/api/permissions.py:257–264`) — an **EMR-flavored** permission set:
  - Has: `REPORT_READ`, `STUDY_READ`, `VIEWER_READ`, `PATIENT_READ`, `CHART_READ`, `MED_ORDER_READ/WRITE`, `MAR_READ`, `ORDER_READ/WRITE`, `RESULTS_READ`, `SCHEDULE_READ`, `CARE_PLAN_WRITE`.
  - **Missing**: `REPORT_WRITE`, `REPORT_SIGN`, `PEER_REVIEW_WRITE`.
- The navigator maps `resident → reading` workspace (`frontend/src/navigator.ts:207–209`), so a resident lands on `/reading`.

### 1.2 What a resident can actually do
| Surface | What works | Gated away from residents |
|---------|-----------|---------------------------|
| **Reading Worklist** (`/reading`, `ReadingWorklist.tsx`) | Priority-sorted queue, filters (status/modality/search/physician/assigned-to-me), 30s polling refresh, STAT/urgent/routine tags, Read Study/Continue | **Take** (claim) — `canClaim = hasPermission("REPORT_WRITE")` (line 75) → **hidden for residents** (line 184) |
| **Reading Console** (`/reading/:examId`, `ReadingConsole.tsx`) | Split viewer + report, 3s autosave, templates, measurements, presets, `[`/`]` collapse, Sign modal with Sign & Next | Editing (`canWrite`), Signing (`canSign`) — **both false** → report pane renders **read-only** |
| **Report panel** (`ReportPanel.tsx`) | Draft→Preliminary→Final stepper, patient/exam card, findings/impression/recommendations, template select | Save Draft / Mark Preliminary / Sign buttons all hidden |
| **Peer Review** (`/peer-review`, `PeerReviewInbox.tsx`) | View queue of **signed** reports, open review modal, read original findings/impression | Submitting an outcome (`PEER_REVIEW_WRITE`) |
| **Files / Detail viewer** (`/files/:id`, `Detail.tsx`) | Viewer tabs (image/metadata/changes/share/management), thumbnail strip, annotations, keyboard shortcuts, reading presets | — |
| **Notifications** | Backend `notify_user`/`notify_role` + `/ws` socket exist (`ws.ts`, `reports.py:256`) | Worklist **polls**, never pushes — WS not wired to the queue |

### 1.3 The blunt truth
A resident account today is a **read-only bystander in a staff-radiologist UI**:
- Lands on a worklist they **cannot claim** from.
- Opens exams they **cannot draft** a report for (read-only textareas).
- Sees a **Draft → Preliminary → Final** stepper whose final two states they are **permission-blocked** from ever reaching.
- Has **zero supervision context**: no attending assignment, no guidance, no submit-for-review, no co-sign, no feedback, no portfolio.

The entire R13 persona (FR-R13-01…10, all `GATED` in `README.md`) is unimplemented. This is the single most important finding: **the "resident" role exists but implements the wrong resident** — the EMR `MATRIX_B_RES` resident (hospital ward clerk) rather than the R13 radiology trainee.

---

## 2. Hypothetical Resident-Scoped Functionality (the gap)

Assuming the R13 persona ships, here is the complete resident-scoped feature set — the current implementation has **none** of it:

1. **Supervised reading worklist** — my assigned studies, my supervising attending per row, supervision status (pending/in_review/completed), STAT left-border + audio, WS push.
2. **Attending guidance panel** — split-screen: viewer left, attending's preliminary notes/areas-of-focus right; real-time updates; `G` toggle; placeholder when absent.
3. **Draft with "Awaiting Attending Review" identity** — DRAFT badge, section word-counts, completeness indicator, `Ctrl+S`, **Submit for Attending Review** (locks the draft), revision-return with inline feedback highlights.
4. **Attending review/co-sign workflow** (R12 side) — resident review queue, side-by-side draft vs. final editor, inline comments, **Approve & Co-sign** / **Return for Revision**.
5. **Teaching file capture** — select key images from thumbnail strip, diagnosis/differential/key learning points/tags, de-identification (burned-in + DICOM tags), attending approval, published teaching library.
6. **Exam log / portfolio** — my interpreted studies, filters (date/modality/body part/diagnosis/attending/review status), metrics (interpretation time, draft→final turnaround, revision rate), CSV export for residency requirements.
7. **Feedback dashboard** — studies by modality/body part, interpretation-time trend, attending agreement rate, feedback themes, private attending notes.
8. **On-call consult** — "Request Attending Consult" → on-call attending/teleradiologist, priority notification, written-guidance fallback, status lifecycle (requested → in_progress → completed), guidance saved to study.
9. **Protocol learning** — educational annotations (why this protocol, key sequences, artifacts, normal variants, red flags), "Mark Reviewed", progress tracker.
10. **Case conference prep** — tag studies, de-identified presentation export (PDF/PPT), attending approval gate.

---

## 3. UI/UX Critique (resident's perspective on the current build)

### 3.1 Critical
- **C1 — Permission trap on landing.** The navigator sends residents to `/reading`, but `REPORT_WRITE`/`REPORT_SIGN` are absent, so the entire surface is inert: no Take, no editing, no signing. *An account that lands on a dead-end page with no explanation is a product failure — either grant the clinical perms to `resident` or split the role and build the real R13 surface.*
- **C2 — Worklist refresh is polling, not push.** 30s `setInterval` (`ReadingWorklist.tsx:99`) contradicts NFR-R13-06 (≤30s staleness, WS + DB trigger). STAT studies sit up to 30s unseen; a resident on call cannot miss an emergent exam.
- **C3 — No supervision identity anywhere.** No attending column, no "awaiting review" badge, no submit path. The resident cannot complete a single end-to-end supervised read: interpret → draft → submit → co-sign. The core loop of the persona is absent.

### 3.2 High
- **H1 — Wrong status model for residents.** The Draft→Preliminary→Final stepper (`ReportPanel.tsx:69–78`) and "Mark Preliminary"/"Sign Report" are staff-radiologist actions. A resident's path is Draft → *Submitted* → *In Review* → *Final (co-signed)*. Showing Preliminary/Final to a permission-blocked user is confusing dead UI.
- **H2 — No prior-study comparison.** Resident training is built on priors ("compare with 2025 CT"). The console shows only the current exam's series; there is no one-click "show priors" in the reading console (the Files study browser exists but is a separate surface).
- **H3 — Autosave UX is invisible.** Autosave exists (3s, `ReadingConsole.tsx:44`) but the only indicator is a timestamp (`saved 14:03:22`). No "Saving…" / "Saved" / "Unsaved changes" states, no `Ctrl+S` manual save (stories US-R13-03 promise it). A resident who sees nothing happening will not trust it.
- **H4 — STAT emphasis is weak.** STAT is a colored tag only (`PRIORITY_COLORS`, `ReadingWorklist.tsx:30–35`). AC-R13-01 requires a 4px red left border + pulsing animation + audio with visual equivalent. On a busy 20-row page a tag does not command attention.
- **H5 — PHI minimization not applied on the worklist.** `ReadingWorklist.tsx` renders full `patient_name` (line 134). Assumption A1 requires initials + MRN last-4 on queue surfaces.
- **H6 — Peer review is QA, not education.** The peer-review flow (`PeerReviewInbox.tsx`) reviews **signed** reports with a 4-level discrepancy scale — designed for R05 QA sampling. It does not return feedback to the resident, so it cannot feed FR-R13-07 or the learning loop.

### 3.3 Medium / polish
- **M1 — Keyboard coverage is viewer-only.** `KeyboardShortcuts.tsx` covers imaging tools; the console has only `[`/`]`. Missing: `G` (guidance toggle), `Ctrl+S` (save), `Ctrl+Enter` (submit/sign), `N` (next study).
- **M2 — No empty-state guidance.** When the worklist is empty the locale string is a wall of text; there is no CTA (e.g., "Assign exams to me from the technologist hand-off").
- **M3 — No resident context header.** The console header shows patient/accession/modality but never "Supervising attending: Dr. X" or "DRAFT — awaiting review" identity.
- **M4 — Mobile reading is a stack, not a design.** Console mobile mode is viewer (55vh) then report below — workable, but there is no mobile reporting presets or toolbar grouping (`MobileToolbar.tsx` exists only in Detail).
- **M5 — No case/portfolio affordances.** Nothing lets a resident mark "interesting case", tag for conference, or track personal case counts — the everyday habit of every trainee.

---

## 4. Proposed Look & Feel (vision for the R13 surface)

### 4.1 Design language
- **Supervision color language** reusing existing tokens: DRAFT = blue tint (`resident-draft-bg`), guidance = green tint, teaching = purple tint, feedback = amber tint, consult = red tint (as already specified in `04-ui-ux-requirements.md` §New Semantic Tokens). Consistent tinted left-rail per state.
- **Badge family**: `DRAFT`, `AWAITING ATTENDING REVIEW`, `IN REVIEW`, `RETURNED FOR REVISION`, `CO-SIGNED` — always text + color (never color alone), per WCAG 2.2 AA.
- **Stepper re-modeled for the supervised path**: Draft → Submitted → Attending Review → Final (co-signed). Preliminary/Final remain staff-only concepts.

### 4.2 Screen sketches (text-level)
- **Supervised Worklist**: priority column with 4px red left border on STAT rows (pulsing), columns Accession / Patient (initials + MRN-4) / Modality / Protocol / **Supervising Attending** / Status (badge) / Action; WS live-updates with a subtle "new study" toast + sound toggle; filter bar matches existing console round-trip pattern.
- **Supervised Viewer**: the existing split console, plus a right-side **Attending Guidance panel** (toggleable, `G`), collapsible like `[`/`]`; placeholder "Attending guidance not yet available — proceed with independent interpretation" when empty.
- **Draft Report Editor**: current `ReportPanel` + `DRAFT — Awaiting Attending Review` banner, per-section word count + completeness dot, live "Saving…/Saved" indicator, **Submit for Attending Review** primary button (replaces Sign for residents), revision-return banner with inline highlighted feedback.
- **Resident Home (new landing for `resident`)**: three-card dashboard — My Queue (counts by priority), Feedback & Progress (agreement gauge, case counts by modality), Teaching Library (recent published cases) — instead of dumping the resident on the staff worklist.
- **Portfolio/Exam List**: filterable table + metric summary cards (total, avg interpretation time, agreement rate, revision rate) + CSV export.
- **Teaching Capture modal**: thumbnail-strip multi-select with checkmarks + reorder, diagnosis/differential/learning points/tags, "Submit for Approval" with status badge lifecycle.

### 4.3 Interaction principles
- Keyboard-complete: `G`, `Ctrl+S`, `Ctrl+Enter` (submit), `N` (next), all discoverable via the existing `?` help.
- Every state change (submit, return, co-sign) yields a notification via the existing `/ws` + notification bell — no polling.
- Everything de-identified on teaching/conference surfaces; PHI minimized on queue surfaces.

---

## 5. Hand-off to Dev Team (prioritized backlog)

### Phase A — Fix the role & unblock the persona (must, ~1 sprint)
- **A1. Role split**: either (a) add `REPORT_WRITE` (+ optionally `REPORT_SIGN`) to `MATRIX_B_RES`, or (b) better: create the clinical `radiology_resident` role with `REPORT_READ/WRITE` and keep `resident` EMR-scoped. Update `backend/api/permissions.py`, `backend/db/roles.py`, migration, `navigator.ts` workspace mapping, RBAC matrix doc (`docs/reaserch/RBAC_matrix_spec.md`).
- **A2. Reading worklist WS push**: subscribe the worklist to `exam.completed`/`reading-list.changed` via `ws.ts`; keep polling as fallback. (NFR-R13-06)
- **A3. STAT row treatment**: 4px red left border + pulse on STAT rows; audio toggle. (AC-R13-01)
- **A4. PHI minimization on worklist**: initials + MRN last-4. (A1)

### Phase B — Supervised reading core (must, next sprint)
- **B1. Attending assignment data**: `resident_id`/`attending_id` on the reading-list query + column. New endpoints: `GET /reports/supervised-list` (or extend `reading_list`), attending-assignment CRUD for R04.
- **B2. Attending guidance channel**: `GET/PUT /exams/{id}/guidance`, WS event `guidance.updated`; guidance panel component with `G` toggle.
- **B3. Draft submit / review / co-sign**: `POST /reports/{exam_id}/submit`, `POST /reports/{exam_id}/approve` (attending co-sign), `POST /reports/{exam_id}/return` (section-level feedback); resident-side lock + revision banner; R12 "Resident Review Queue" entry; notifications both ways. (FR-R13-04 — the largest blocker)
- **B4. Report panel re-model**: supervised stepper, DRAFT badge, word counts + completeness, `Ctrl+S`, Submit button (gated by role), "Saving…/Saved" indicator. (FR-R13-03 slices)

### Phase C — Portfolio & feedback (should)
- **C1. Exam log/portfolio**: `GET /reports/my-exams` + filters + CSV export; metrics (interpretation time, draft→final turnaround, revision rate). (FR-R13-06)
- **C2. Feedback dashboard**: `GET /residents/{id}/feedback` aggregates; charts (modality bar, time trend, agreement gauge, themes); private attending notes. (FR-R13-07)
- **C3. Peer-review feedback loop**: route reviewer comments back to the resident's feedback feed. (H6)

### Phase D — Educational features (could / later)
- **D1. Teaching files**: `POST /teaching-files`, de-identification service (strip PHI tags + burned-in), approval flow, library view. (FR-R13-05)
- **D2. On-call consult**: `POST /exams/{id}/consults`, routing to on-call R12/R18, status lifecycle, guidance persisted to study. (FR-R13-08)
- **D3. Protocol learning**: educational annotations on protocols + "Mark Reviewed" + progress. (FR-R13-09)
- **D4. Case conference**: tag + de-identified PDF/PPT export + attending approval. (FR-R13-10)

### Acceptance framing
Each Phase B–D item should satisfy the corresponding AC in `06-acceptance-criteria.md` and keep the existing NFR targets (autosave ≤10s, worklist staleness ≤30s, WCAG 2.2 AA, keyboard operability). The console/report state machine in `ReadingConsole.tsx` and `ReportPanel.tsx` is the primary refactor surface — prefer extending it with role-aware modes over a parallel editor.

**Top 3 to start**: A1 (role grant fix), B3 (submit/co-sign — unlocks the entire persona), A2 (WS push).
