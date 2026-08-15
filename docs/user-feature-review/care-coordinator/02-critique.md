# 02 — Critique: care_coordinator (Phase 1)

Critique as the test.user — what the care coordinator experiences, wants, and is
blocked by. Severity: Critical (blocks the task) / High (major friction) /
Medium (annoyance) / Low (polish).

---

## C1 — **Critical**: My job doesn't exist in this app
I hold grants for care plans, orders, encounters, medication-order views, and
prior auth — but **none of those have a screen**. I searched the sidebar: Files,
Account, Reading. Every one of my defining permissions is a ghost. If I'm a care
coordinator, this app is a read-only radiology portal with my name on the door.

- Severity: **Critical** · Flows: HF-1, HF-2, HF-3, HF-6
- Evidence: grant→surface audit (`00-inventory.md`); `CARE_PLAN_WRITE` etc. exist
  only as labels in `src/api/roles.ts`.

## C2 — **Critical**: The Schedule Board is a dead end I can reach
I have `SCHEDULE_READ`, so `/schedule-board` renders for me — then tells me
"Failed to load schedule · Missing permission: WORKLIST_READ" and shows a Retry
button that cannot succeed. This is a permission cliff *inside* a granted page.
Worse: the sidebar hides the Schedule item entirely (it now gates on
`WORKLIST_READ`), so I can't even discover that the page exists — I only hit it
by guessing the URL. The resident fix (R13) added `WORKLIST_READ` to the resident
row with exactly this rationale; care_coordinator (and physician) still have the
bug.

- Severity: **Critical** · Flow: HF-4
- Evidence: `07-16-schedule-board.png`; `GET /api/v2/worklist → 403`.

## C3 — **High**: The Files page is a dead end I'm shown
Files appears in my sidebar unconditionally, and the route allows me in
(STUDY_READ passes the route gate) — but the page then fails to load with
"Missing permission: FILE_READ" and a Retry that can't succeed. Either I should
have read access to files (read-only FILE_READ matches STUDY_READ/VIEWER_READ I
already hold) or the page shouldn't be shown to me.

- Severity: **High** · Evidence: `06-15-files-state.png`; `GET /api/v2/files → 403`.

## C4 — **High**: I land on the radiologist's worklist
My home is "Reading Worklist — handed-off exams awaiting interpretation". I don't
interpret exams. It's an empty list for me (0 rows) and it reads as a
misconfiguration. I have no surface of my own, so the app routes me to whoever
else's job is closest.

- Severity: **High** · Flow: HF-7 · Evidence: `01-10-reading-worklist.png`.

## C5 — **Medium**: Reading what I *can* read is awkward
I can view patients and their studies fine (`/patients/13` renders demographics,
study list, series). But there's no report summary on the patient page for me —
the results I'm allowed to read (`REPORT_READ`/`RESULTS_READ`) aren't surfaced
where I'd look.

- Severity: **Medium** · Flow: HF-5.

## C6 — **Medium**: No feedback when things 403
Pages that fail show a "Missing permission" line and Retry — but no hint of
*who can fix it* or *where I should go instead*. As a user I'm left guessing
whether the app is broken or I'm not allowed.

- Severity: **Medium** · Evidence: console 6× 403 with no in-UI guidance.

## C7 — **Low**: Discoverability of my (few) working tools
Patient search and the viewer are buried under paths I have to know. The Files
page looks like a search surface but is dead, which erodes trust in the search
box that does work.

- Severity: **Low**.

## C8 — **Low**: Account/permission display mismatch
My Account page lists 13 grants — including the 5 with no surface — reinforcing
the feeling that I *should* have features I can't find.

- Severity: **Low**.

---

### Summary
- **Critical: 2** (C1 role-void, C2 schedule dead end) · **High: 2** (C3 files
  dead end, C4 wrong landing) · **Medium: 2** · **Low: 2**
