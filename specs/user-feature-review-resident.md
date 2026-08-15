# Technical Design — user-feature-review resident hand-off

Source: `docs/user-feature-review/resident/03-handoff.md` + `04-design.md`
Branch: `feature/resident-workflow-polish` (per user request; the skill default
`phase/user-feature-review-resident` is intentionally not created)

## Scope

| ID | Change | Layer | Status |
|----|--------|-------|--------|
| P0-1 | Schedule Board dead-end | backend grant + sidebar gate | implement |
| P0-2 | `claimed_today` stat honesty | backend + ResidentHome | implement |
| P1-1 | "Needs revision" filter | backend reading_list + worklist | implement |
| P1-2 | filter select a11y (id/aria-label) | worklist | implement |
| P2-1 | Teaching Library guided empty state | ResidentHome | implement |
| P2-2 | returned-notification deep link | — | already implemented (verify + note) |

## P0-1 — Schedule Board reachable by resident

**Backend** (`backend/api/permissions.py`): add `WORKLIST_READ` to
`MATRIX_B_RES` (read-only; NO `WORKLIST_WRITE`). Rationale: the Schedule Board
loads its day data from `GET /api/worklist` (ScheduleBoard.tsx:98) which is
gated `WORKLIST_READ` (backend/api/worklist.py:21); SCHEDULE_READ alone passes
the route gate but cannot load data → dead end.

**Frontend** (`frontend/src/common/Sidebar.tsx`): Schedule item permissions
`["SCHEDULE_READ"]` → `["WORKLIST_READ"]`. The sidebar `some()` semantics make
this a strict safety net: only roles that can actually load the board see the
item (no dead ends). The route gate (index.tsx:265 SCHEDULE_READ) stays.

**Side effect (accepted)**: resident gains the read-only "Modality Worklist"
nav item (sidebar worklist item gates WORKLIST_READ). It is a read-only DICOM
worklist view; consistent with the design's "read-only schedule is in-scope".

**Docs**: `docs/reaserch/RBAC_matrix_spec.md` Matrix B row.
**Tests**: `backend/tests/test_rbac_matrix.py` (resident holds WORKLIST_READ,
never WORKLIST_WRITE).

## P0-2 — `claimed_today` stat

Claim moment = draft report creation (Take → console autosave creates the
report row with `created_by` = user id; there is no `assigned_at` column on
exams, and `updated_at` is noisy). So:

- `backend/db/reports.py`: no change.
- `backend/api/reports.py` ReadingListHandler: when `radiologist == 'me'`,
  count reports `created_by = request.user.id AND created_at >= date_trunc('day', now())`
  and return `ok({'data': items, 'claimed_today': n})`.
- `frontend/src/radiologist/ResidentHome.tsx`: use `claimed_today` from the
  response for the "Claimed today" statistic; keep `Total claimed` (footer)
  as the queue total.

**Tests**: `backend/tests/test_reports_api.py` — claimed_today present only
with radiologist=me; count query uses the requesting user id.

## P1-1 — "Needs revision" filter

Returned reports revert to `status='draft'` with `review_feedback` set
(db/reports.py return_report). So "needs revision" = draft + feedback.

- `backend/db/reports.py` `reading_list()`: map `status == 'returned'` to
  `r.status = 'draft' AND r.review_feedback <> ''`.
- `frontend/src/radiologist/ReadingWorklist.tsx`: status Select gains
  `{ value: 'returned', label: 'needs revision' }` (lowercase label matches
  existing lowercase option labels; report status tag renders via existing
  "Returned" volcano tag on rows).

**Tests**: reading_list SQL contains the returned mapping (assert the
`where` clause via the fetch call args).

## P1-2 — a11y on filter selects

`frontend/src/radiologist/ReadingWorklist.tsx`: add `id` + `aria-label` to the
Report status and Modality Selects ("Report status", "Modality").

## P2-1 — Teaching Library empty state

`frontend/src/radiologist/ResidentHome.tsx:230-234`: replace bare placeholder
with guided empty state: "No curated teaching cases yet — ask your attending
to flag interesting studies during QA review." No dead button (nothing to
navigate to yet). Card stays until teaching workflow ships (design fallback).

## P2-2 — returned-notification deep link

Already shipped: `notify_user(..., '/reading/{exam_id}')` (reports.py:427) +
NotificationBell.tsx:146 navigates same-origin paths. Verify in Phase 4;
document only.

## Security checklist (fullstack-guardian)

| Check | Status |
|-------|--------|
| Auth | reading-list already `requires_permission(REPORT_READ)`; worklist `WORKLIST_READ` |
| Authz | claimed_today scoped to `request.user.id` (no IDOR); resident gets read-only grant only |
| Input | no new body input; status param passed through parameterized SQL |
| Output | no sensitive fields added; `claimed_today` is an integer |
| Rate limit | no new endpoint (field on existing) |
| Logging | no new security events (grant change is a code change, not runtime) |
