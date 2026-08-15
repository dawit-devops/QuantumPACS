# 04 — Design Proposal (ui-ux-pro-max)

Input: `03-handoff.md` + `01-hypothetical-flows.md`
Product type: healthcare / PACS (SaaS clinical tool)
Stack: React 19 + Vite + Ant Design v6 (frontend/package.json)

## 0. Design-system alignment check

ui-ux-pro-max recommends **"Accessible & Ethical"** style for healthcare
(high contrast, 16px+ text, keyboard nav, WCAG AA+, semantic) with
cyan + health-green palette and Figtree/Noto Sans typography.

The codebase **already implements this system** — `frontend/src/common/tokens.css`
uses Figtree headings, Inter/Noto Sans body, cyan-700 primary (`#0e7490`, AA on
white), teal success, amber warning, red error, full focus-ring + motion
tokens (150/250ms, reduced-motion respected). **Conclusion: no token changes
are needed.** Every design below reuses existing primitives; the work is
component-level.

Design-intelligence checks applied (search.py):
- Empty states: "Show helpful message and action — never blank screens" →
  Teaching Library card (P2-1) gets an actionable empty state, not a bare "coming soon".
- Deep linking: "URLs reflect current state" → returned-notification deep link (P2-2).
- Table handling / forms: filter selects need labels (P1-2).
- Loading/feedback: stats must have skeleton/error states (already present via `mine === null` spin + error Alert).

---

## D-1 (P0-1) Schedule Board reachability

**Problem**: nav offers a surface the role cannot open (backend wants WORKLIST_READ).
**Design decision — option (b), hide, plus permission fix (a)**:
1. **Backend (primary)**: grant `WORKLIST_READ` to `MATRIX_B_RES`
   (backend/api/permissions.py:257). Read-only schedule is a clinical
   expectation (HF-4); it does not grant write.
2. **Frontend (safety net)**: sidebar Schedule item renders only when the
   user has `WORKLIST_READ` **or** `SCHEDULE_READ` + the schedule endpoint's
   actual permission — never surface dead ends. Mirrors the existing
   `PermissionRoute` philosophy (index.tsx:265).

**Component**: `frontend/src/common/Sidebar.tsx` item visibility predicate;
**Interaction**: none new — nav item appears/disappears consistently.

## D-2 (P0-2) "Claimed today" stat honesty

**Problem**: `Claimed today` = queue total (ResidentHome.tsx:212).
**Design decision**:
1. Backend exposes `claimed_today` (count of exams claimed by resident in the
   current day, tenant TZ) in the reading-list payload or a `/reports/resident-stats` endpoint.
2. Frontend: `Statistic title="Claimed today" value={stats.claimed_today}` —
   label and value must share one source of truth. Keep `Total claimed`
   (`rh-total` footer) as the queue total.
3. Add a 24h-trend affordance later (bullet chart per ui-ux-pro-max chart
   domain: values always visible as text, AAA) — **not required now**, note as follow-up.

**Component**: Ant `Statistic` + `Tag`; no new tokens.

## D-3 (P1-1) "Needs revision" filter

**Problem**: returned drafts are not filterable.
**Design decision**:
1. Worklist report-status `Select` gains a `returned` value
   ("Needs revision") alongside draft/submitted/final.
2. Rows for returned exams render the existing `volcano` "Returned" tag
   (already used on ResidentHome.tsx:292-295) with a feedback `Tooltip` —
   consistent cross-surface language.
3. `reading-list` API accepts the status filter (query param), returns
   `review_feedback`.

**Component**: Ant `Select` options + `Tag` + `Tooltip`; filter labeled via
`aria-label`/`id` (ties to D-4).

## D-4 (P1-2) a11y: filter select labels

**Problem**: "form field element should have an id or name attribute" ×2.
**Design decision**: give each filter `Select` an `id` + `aria-label`
("Report status", "Modality"), matching Ant v6 accessibility guidance.
Verify via console (no `[issue]` messages) + keyboard tab order.

## D-5 (P2-1) Teaching Library card

**Problem**: permanent placeholder.
**Design decision — ship minimal read-only (b)**:
1. New `teaching_files` table (id, study_id, modality, description,
   submitted_by, status) — **Phase 3 scope; if not ready, hide the card**.
2. Card states:
   - Empty (no curated cases): `Empty` with **action button**
     "Ask your attending to curate a case" (guides, per empty-state rule) —
     not a bare "coming soon" text.
   - Populated: list of cases (modality tag + description), click → detail
     viewer (FILE_READ), reusing `.rh-exam` row pattern (ResidentHome.css:58-73).
3. Hidden entirely behind a feature flag until the workflow exists (fallback).

## D-6 (P2-2) Notification deep link

**Problem**: returned-notification does not open the draft.
**Design decision**: notification payload includes `link: "/reading/{examId}"`
(the exams backend `_notify_role` already builds links — exams.py:526); the
popover item wraps in a navigation onClick to that link. Deep-link rule:
"URLs reflect current state" (search.py: navigation/deep-linking, Medium).

---

## Conflicts with existing patterns

| Decision | Existing pattern | Conflict | Resolution |
|----------|------------------|----------|------------|
| D-1 grant WORKLIST_READ to resident | RBAC spec says resident is Matrix B read-mostly; WORKLIST_READ not in MATRIX_B_RES | Matrix drift if unchecked | Keep it **read-only**; update `docs/reaserch/RBAC_matrix_spec.md` §4/§5 + tests; do NOT grant WORKLIST_WRITE |
| D-2 new stats field | reading-list payload is queue-focused | Payload bloat | Compute in same endpoint (single query), document field |
| D-5 teaching_files | no teaching workflow exists in ADRs | New scope | Gate behind flag; ADR-022 branch discipline — separate branch if it grows |
| D-3 `returned` status filter | statuses enumerated in REPORT_STATUS_COLORS (draft/preliminary/submitted/final) | `returned` is a report state, not a color map | Keep tag styling via existing `volcano` tooltip pattern; do not add to REPORT_STATUS_COLORS (it is not a final report state) |

## Interaction & motion summary
- All transitions reuse `--duration-fast/normal` + `--easing-standard`; no new motion.
- 44×44px touch targets on nav rows (existing `rh-exam` padding ≈ 40px → bump to 44px).
- `prefers-reduced-motion`: unchanged (tokens already respect it).

## Verification plan (feeds Phase 4)
1. `/schedule-board` as `test.resident` renders schedule (D-1) — no error banner.
2. Home shows `Claimed today` ≠ total (D-2).
3. `status=returned` filter returns expected rows + feedback tooltip (D-3).
4. No a11y console issues on `/reading` (D-4).
5. Teaching Library shows guided empty state or curated cases (D-5).
6. Returned notification navigates to `/reading/{examId}` (D-6).
