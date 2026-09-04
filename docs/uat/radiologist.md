# Radiologist UAT Walkthrough

## Prerequisites

```bash
cd backend && .venv/bin/python ../scripts/seed_uat.py --persona radiologist
```

Seeds: 2 completed exams (CT + MR) with study/series/files, 1 final report and 1 draft report.

## Walkthrough

### 1. Reading Console — Queue View

| Step | Action | Expected Outcome |
|------|--------|------------------|
| 1 | Login as `test.radiologist` / `Test@123456` | Dashboard loads with reading queue |
| 2 | Observe the reading queue | 2 exams visible: CT Head (completed) + MR Brain (completed) |
| 3 | Note the report status badges | CT: "Final" badge; MR: "Draft" badge |

### 2. Open and Read Study

| Step | Action | Expected Outcome |
|------|--------|------------------|
| 4 | Click the CT Head exam in the queue | Viewer opens with the CT series |
| 5 | Use window/level, pan, zoom tools | Viewer responds correctly |
| 6 | Scroll through the series | All slices render |

### 3. Finalize Report

| Step | Action | Expected Outcome |
|------|--------|------------------|
| 7 | Open the CT Head report | Findings and impression pre-populated |
| 8 | Click "Sign" | Report status changes to "final" |
| 9 | Confirm the exam leaves the queue | Queue count decrements |

### 4. Draft Report Editing

| Step | Action | Expected Outcome |
|------|--------|------------------|
| 10 | Open the MR Brain exam | Report shows "draft" status |
| 11 | Edit findings field | Text saves (autosave indicator) |
| 12 | Click "Sign" | Report status → "final" |

## Expected Data

- `reports` table: 2 rows (1 final, 1 draft → final after sign)
- `studies` + `series` + `files` populated for both
- Reading console queue shows exams with completed status

## Acceptance Criteria

- [ ] Radiologist can view completed exams in reading queue
- [ ] Viewer renders DICOM pixel data
- [ ] Report can be drafted, edited, and signed
- [ ] Signed reports move out of the queue
- [ ] Autosave persists draft edits