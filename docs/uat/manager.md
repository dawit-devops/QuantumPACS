# Manager UAT Walkthrough

## Prerequisites

```bash
cd backend && .venv/bin/python ../scripts/seed_uat.py --persona manager
```

Seeds: 3 exams across ready / in_progress / completed+PAID (dashboard aggregate).

## Walkthrough

### 1. Manager Dashboard

| Step | Action | Expected Outcome |
|------|--------|------------------|
| 1 | Login as `test.super_admin` / `Test@123456` | Dashboard loads with aggregate cards |
| 2 | Verify total counts | 3 exams visible in summary |
| 3 | Verify status breakdown | Ready (1), In Progress (1), Completed (1) |

### 2. Financial Overview

| Step | Action | Expected Outcome |
|------|--------|------------------|
| 4 | View the revenue summary | 1 PAID charge: $850.00 |
| 5 | Verify unbilled count | 0 unbilled (manager scope) |
| 6 | Check aging report | Aging buckets render correctly |

### 3. Worklist Monitoring

| Step | Action | Expected Outcome |
|------|--------|------------------|
| 7 | Navigate to the Tracking Board | All 3 exams visible |
| 8 | Apply filter by status | List filters correctly |
| 9 | Apply date range filter | List filters by date |

### 4. Denial Rate

| Step | Action | Expected Outcome |
|------|--------|------------------|
| 10 | View Denial Rework section | Shows denial statuses (none in manager scope) |
| 11 | Verify filter controls | Status and payer filters work |

## Expected Data

- `exams`: 3 rows (ready, in_progress, completed)
- `ris_charges`: 1 PAID ($850.00, CPT 71250)
- `reports`: 1 final (CT Chest)

## Acceptance Criteria

- [ ] Dashboard aggregates show correct exam counts per status
- [ ] Revenue summary reflects PAID charges
- [ ] Tracking Board displays all exams with working filters
- [ ] Aging report renders without error
- [ ] Denial Rework section shows correct zero-state