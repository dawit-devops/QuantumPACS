# Resident Workflow Polish — Implementation Summary

Phase 3 of the user-feature-review pipeline for `resident`.
Design: `04-design.md` (decisions D-1..D-6). Spec: `specs/user-feature-review-resident.md`.

## Hand-off items — status

| ID | Item | Status | Notes |
|----|------|--------|-------|
| P0-1 | Schedule Board dead-end (CRIT) | **DONE** | WORKLIST_READ granted to MATRIX_B_RES (read-only); sidebar Schedule item now gates on WORKLIST_READ so SCHEDULE_READ-only roles never see a dead end |
| P0-2 | "Claimed today" stat honesty (CRIT) | **DONE** | backend computes drafts started today (claim = first draft autosave, created_by=user); field only present for radiologist=me |
| P1-1 | "Needs revision" filter | **DONE** | status=returned maps server-side to draft + review_feedback <> ''; worklist option labeled "needs revision" |
| P1-2 | filter select a11y | **DONE** | id + aria-label on Report status and Modality selects |
| P2-1 | Teaching Library empty state | **DONE** | guided copy ("ask your attending…"); card stays until teaching workflow ships (design fallback) |
| P2-2 | returned-notification deep link | **DONE (pre-existing)** | `notify_user(..., f'/reading/{exam_id}')` + NotificationBell navigates `n.link` — verified live, no change needed |

## Changes

### Backend
- `api/permissions.py` — `MATRIX_B_RES` += `WORKLIST_READ` (no WORKLIST_WRITE; comment explains the Schedule Board data dependency).
- `api/reports.py` ReadingListHandler — `is_me` captured before `radiologist='me'` resolution; when own queue, count drafts created today (`created_by = user id AND created_at >= date_trunc('day', now())`); `claimed_today` only in payload for `radiologist=me` (other consumers keep payload shape).
- `db/reports.py` `reading_list()` — `status=returned` compiles to `r.status = 'draft' AND r.review_feedback <> ''` (returned reports revert to draft with feedback set).

### Frontend
- `common/Sidebar.tsx` — Schedule item `permissions: ["WORKLIST_READ"]` (endpoint it actually calls; route gate SCHEDULE_READ unchanged).
- `radiologist/ResidentHome.tsx` — reads `m.claimed_today` into state; "Claimed today" Statistic uses it (was queue total); Teaching Library guided empty state.
- `radiologist/ReadingWorklist.tsx` — status filter adds `returned` → label "needs revision"; `id`/`aria-label` on both filter selects.

### Docs
- `docs/reaserch/RBAC_matrix_spec.md` — Matrix B WORKLIST_READ row (PHYS ✓, RES ✓, COORD ✓).

### Tests
- `test_rbac_matrix.py` — `test_resident_reads_worklist_but_never_writes`.
- `test_reports_api.py` — `test_returned_status_maps_to_draft_with_feedback`, `test_claimed_today_only_for_own_queue`; `test_me_resolves_to_requesting_user` updated to mock fetchval.

## Verification

- pytest backend: 1645 passed, 1 skipped, 4 xfailed (full suite).
- ruff: clean.
- `tsc --noEmit`: clean.
- Live as test.resident (http://localhost:5173):
  - Schedule Board loads (Total 2, CT/MR lanes with E2E^Combined^Flow exams) — was 403 dead-end.
  - Resident Home "Claimed today: 1" (backend count; queue is empty so the old code would have shown 0).
  - Teaching Library guided copy renders.
  - Worklist status filter shows "needs revision"; `GET /api/reports/reading-list?status=returned` → 200.
  - Filter selects expose accessible names (aria-label).

## Deviations from design

- Teaching Library: design D-5 proposed an "Ask your attending" action button; implemented as guided copy only — no dead button (nothing to navigate to yet). Follow-up: button when the teaching-file workflow ships.
- D-1 sidebar safety net kept (Schedule gated on the real endpoint permission), plus the backend grant — both design branches implemented.
