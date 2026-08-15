# 03 — Hand-off to the dev team (prioritized)

## P0-1 — Schedule Board must not be offered to roles that can't open it
**User story**: As a resident, I want the nav to only show surfaces I can actually open, so I never hit a permission dead end.
**Fix options (pick one)**:
- (a) Grant `WORKLIST_READ` to `MATRIX_B_RES` (read-only schedule is in-scope for clinical roles), or
- (b) Hide/disable the Schedule item in the sidebar for roles lacking WORKLIST_READ.

**Acceptance criteria**:
1. As `test.resident`, opening `/schedule-board` renders the day's schedule (or a disabled nav item) — no "Missing permission" error banner.
2. As a role without SCHEDULE_READ, the Schedule item remains hidden.
3. Backend schedule endpoint rejects non-WORKLIST_READ roles only when the role also lacks SCHEDULE_READ (i.e., no regression for technologists).

**Affected**: `backend/api/permissions.py` (MATRIX_B_RES) and/or sidebar visibility (frontend/src/common/Sidebar.tsx); `frontend/src/index.tsx:265` gate.

## P0-2 — Fix "Claimed today" statistic to be today-scoped
**User story**: As a resident, I want progress numbers that mean what they say, so I can report my daily workload accurately.
**Acceptance criteria**:
1. `Claimed today` shows the count of exams claimed by the resident in the last 24h (or current day, per tenant TZ) — not the queue total.
2. The total is still visible as "Total claimed".
3. Backend exposes a `claimed_today` field (reading-list or a dedicated stats endpoint) rather than frontend date-math on a 30s poll.

**Affected**: `frontend/src/radiologist/ResidentHome.tsx:212`; reading-list/reports API.

## P1-1 — Worklist: add "Needs revision" filter + returned visibility
**User story**: As a resident, I want to filter my queue to drafts the attending returned, so I can redo them in one pass.
**Acceptance criteria**:
1. Report-status filter includes a `returned` value.
2. Reading-list API accepts `status=returned` (or equivalent) and returns exams with `review_feedback`.
3. Rows show a "Returned" tag with feedback tooltip, consistent with Resident Home.

**Affected**: `frontend/src/radiologist/ReadingWorklist.tsx`; `backend/api/reports.py` reading-list.

## P1-2 — a11y: give worklist filter selects id/name attributes
**User story**: As a screen-reader user, I want labeled filter dropdowns so I can use the queue without sighted assistance.
**Acceptance criteria**:
1. No "form field element should have an id or name attribute" console issue on `/reading`.
2. Each filter has a programmatically associated label.

**Affected**: `frontend/src/radiologist/ReadingWorklist.tsx` filter selects.

## P2-1 — Resident Home: replace Teaching Library placeholder or wire it minimally
**User story**: As a resident, I want a useful home card, not a permanent "coming soon".
**Acceptance criteria**: Either (a) hide the card until the teaching workflow ships, or (b) surface read-only curated cases (id, modality, description) from a `teaching_files` table.

**Affected**: `frontend/src/radiologist/ResidentHome.tsx:224-235`.

## P2-2 — Returned-notification deep link
**User story**: As a resident, I want to jump straight from a "returned for revision" notification into the draft.
**Acceptance criteria**: Notification item links to `/reading/{examId}`.

**Affected**: notifications payload/`frontend/src/notifications/*`.

---

## Definition of Done (for the whole hand-off)
- [ ] P0-1, P0-2, P1-1, P1-2 implemented and merged
- [ ] `backend/tests/` updated: schedule permission matrix, reading-list `returned` filter, `claimed_today` stat
- [ ] Frontend tsc + `npm run build` green; backend `pytest` green; ruff clean
- [ ] E2E (Phase 4) re-walk: Schedule no longer errors, Claimed-today ≠ total, revision filter returns expected rows, no a11y console issues
- [ ] Artifacts `00`–`06` written; evidence screenshots updated
