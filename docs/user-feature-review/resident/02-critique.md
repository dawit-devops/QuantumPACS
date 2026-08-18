# 02 — Critique (wearing the resident's hat)

## CRIT-1 — Schedule Board is a dead end (Critical)
- **Where**: nav → Acquisition → Schedule; `frontend/src/index.tsx:265` gates `/schedule-board` on SCHEDULE_READ; backend `schedule` endpoint requires WORKLIST_READ.
- **Experience**: "I click Schedule and the page tells me 'Missing permission: WORKLIST_READ'. I'm not an admin — what am I supposed to do? The nav shouldn't show me things I can't open."
- **Dimensions**: Discoverability (misleading nav), Trust.
- **Evidence**: `02-schedule-board-failure.png`.

## HIGH-1 — "Claimed today" stat is actually the total (High)
- **Where**: `frontend/src/radiologist/ResidentHome.tsx:212` — `Statistic title="Claimed today" value={totalMine}` where `totalMine = mine.length` (line 115). It is not today-scoped.
- **Experience**: "The number says 'Claimed today' but it grows with my whole queue — it's the total. I can't trust my progress numbers."
- **Dimensions**: Trust, Accuracy.

## MED-1 — Teaching Library is a permanent placeholder (Medium)
- **Where**: `frontend/src/radiologist/ResidentHome.tsx:230-234` — Empty card: "will land here once the teaching-file workflow ships."
- **Experience**: "A whole card on my home page that always says 'coming soon'. Either ship a minimal version or hide it."
- **Dimensions**: Trust, Efficiency (wasted screen space).

## MED-2 — No revision filter on the worklist (Medium)
- **Where**: `frontend/src/radiologist/ReadingWorklist.tsx` filters — Report status dropdown lacks a `returned`/`needs revision` value.
- **Experience**: "My attending returned three drafts with feedback. I have to hunt for them — the queue doesn't let me filter to just the ones I need to redo."
- **Dimensions**: Efficiency.

## MED-3 — Form controls missing id/name (Medium, a11y)
- **Where**: console issue "A form field element should have an id or name attribute (count: 2)" on worklist filter selects (`frontend/src/radiologist/ReadingWorklist.tsx`).
- **Experience**: "Screen readers can't tell me what these dropdowns are."
- **Dimensions**: Accessibility (WCAG 2.1 AA).

## LOW-1 — "Not started" vs queue leaving semantics (Low)
- **Where**: `ResidentHome.tsx:116-118` — an exam leaves the queue once FINAL; worklist empty-state copy says "No studies awaiting interpretation. Completed exams appear here."
- **Experience**: "My co-signed exam vanished from the worklist — I'd expect to still see it in my history until I navigate to Files."
- **Dimensions**: Consistency (history lives elsewhere).

## LOW-2 — Notifications have no in-app "go to exam" from returned items (Low)
- **Where**: notifications popover items are buttons with no visible navigation target.
- **Experience**: "I get 'returned for revision' but the notification itself doesn't open the draft."
- **Dimensions**: Efficiency.

## What works well (positive evidence)
- Landing on Resident Home is correct and the queue counts poll on the same 30s cadence as the worklist.
- Co-sign + return notifications carry useful detail (signer, feedback text).
- Report stepper (Draft → Submitted → Co-signed) makes the supervision model legible.
- Permission gates bounce unauthorized surfaces correctly (probe `/users` → landing).
- FINAL banner with signer name + timestamp builds trust.
