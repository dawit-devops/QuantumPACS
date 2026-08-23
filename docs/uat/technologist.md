# Technologist UAT Walkthrough

## Prerequisites

```bash
cd backend && .venv/bin/python ../scripts/seed_uat.py --persona technologist
```

Seeds: 3 exams on the technologist worklist (1 ready, 1 in_progress, 1 scheduled).

## Walkthrough

### 1. Technologist Console — Worklist

| Step | Action | Expected Outcome |
|------|--------|------------------|
| 1 | Login as `test.technologist` / `Test@123456` | Console loads with worklist |
| 2 | Observe the worklist table | 3 exams visible: UAT-TECH-01 (ready), UAT-TECH-02 (in_progress), UAT-TECH-03 (scheduled) |
| 3 | Verify status badges/colors | Each status shows distinct styling |

### 2. Acquire Exam

| Step | Action | Expected Outcome |
|------|--------|------------------|
| 4 | Click the "ready" exam (UAT-TECH-01) | Exam detail panel opens |
| 5 | Click "Start Exam" | Status changes to "in_progress" |
| 6 | Verify the worklist updates | Badge now shows "in_progress" |

### 3. QA and Complete

| Step | Action | Expected Outcome |
|------|--------|------------------|
| 7 | Mark acquisition as complete | Status → "QA" |
| 8 | Pass QA checks | Status → "completed" |
| 9 | Verify exam moves from worklist | Completed exam no longer shown in active worklist |

### 4. Safety Check

| Step | Action | Expected Outcome |
|------|--------|------------------|
| 10 | Access the safety check form for the exam | Form loads with contrast/radiation fields |
| 11 | Submit safety confirmation | Safety record created |

## Expected Data

- `exams` table: 3 rows with `assigned_technologist` = test.technologist
- `worklist_entries` table: 3 matching rows
- Status transitions: ready → in_progress → QA → completed

## Acceptance Criteria

- [ ] Technologist worklist shows all assigned exams
- [ ] Clicking an exam opens detail panel
- [ ] "Start Exam" transitions status correctly
- [ ] QA workflow completes successfully
- [ ] Safety check form works and persists