# 01 — Hypothetical Flows (what a resident expects but the app lacks)

## HF-1: Take/claim a hand-off exam from the queue
- **User story**: As a resident, I want to claim an exam the attending handed off so I can draft a report on it.
- **Scenario**:
  1. Resident opens Reading Worklist (exists) ✅
  2. Sees unclaimed handed-off exams (exists — queue loads) ✅
  3. Clicks "Take" to claim it for themselves — **MISSING** (queue rows have no claim action visible; claiming only happens implicitly via navigation/assignment)
  4. Opens the exam — console loads (exists) ✅
- **Data impact**: `POST /api/exams/{id}/take` or reuse `assigned_radiologist` update; queue item claim state.

## HF-2: Follow up on returned draft (revision loop)
- **User story**: As a resident, I want to see which of my reports were returned with feedback and reopen them so I can address the attending's notes.
- **Scenario**:
  1. Notification "returned for revision" arrives (exists) ✅
  2. From the notification or home, resident sees the returned exam tagged "Returned" (exists — home shows `review_feedback` tooltip) ✅
  3. Resident wants a dedicated "Needs revision" filter on the worklist — **MISSING** (worklist has "Awaiting review" but no revision filter)
  4. Reopens and resubmits (console submit exists) ✅
- **Data impact**: report status `returned` filter in reading-list API.

## HF-3: Learning progress tracking
- **User story**: As a resident, I want to see my supervision progress (reports co-signed, cases read by modality) so I can demonstrate my training progress.
- **Scenario**:
  1. Feedback & Progress card shows counts (exists) ✅
  2. Resident wants a history/chart of co-signed vs returned over time — **MISSING** (static counters only)
  3. Teaching Library populated with curated cases — **MISSING** (placeholder "will land here once the teaching-file workflow ships")
- **Data impact**: teaching-file workflow (files tagged as teaching), progress history endpoint.

## HF-4: View schedule of upcoming exams without admin privileges
- **User story**: As a resident, I want to glance at the day's imaging schedule so I know what studies are coming.
- **Scenario**:
  1. Navigate to Schedule Board from nav (nav item exists) ✅
  2. Page loads — **FAILS**: "Missing permission: WORKLIST_READ" error banner; retry button loops
  3. Board should render day's schedule read-only
- **Data impact**: schedule endpoint should not require WORKLIST_READ for SCHEDULE_READ holders.

## HF-5: Peer case / teaching case sharing
- **User story**: As a resident, I want to flag an interesting case to the teaching library so attendings can curate it.
- **Scenario**:
  1. Open an exam in the console (exists) ✅
  2. "Add to teaching library" action on exam/report — **MISSING**
  3. Attending reviews and approves it into Teaching Library — **MISSING**
- **Data impact**: teaching_files table, review workflow, resident-facing flag action.

## HF-6: Co-sign status visibility at a glance
- **User story**: As a resident, I want to see which of my submitted reports are still awaiting attending co-sign, without opening each one.
- **Scenario**:
  1. Home "Awaiting review" counter exists ✅
  2. Worklist "Awaiting review" checkbox exists ✅
  3. Resident wants a distinct "Submitted — awaiting co-sign" tag with time-since-submit — **MISSING** (status tag shows `submitted` but no elapsed time)
- **Data impact**: submitted_at timestamp surfaced in reading-list rows.
