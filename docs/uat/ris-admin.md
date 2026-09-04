# RIS Admin UAT Walkthrough

## Prerequisites

```bash
cd backend && .venv/bin/python ../scripts/seed_uat.py --persona ris-admin
```

Seeds: 2 report templates, 3 coding-map rows, 1 extra resource (US Room).

## Walkthrough

### 1. Template Manager

| Step | Action | Expected Outcome |
|------|--------|------------------|
| 1 | Login as `test.tenant_admin` / `Test@123456` | Admin console loads |
| 2 | Navigate to "Report Templates" | Template list shows defaults + UAT entries |
| 3 | Open "UAT CT Chest" template | Findings/impression pre-populated |
| 4 | Edit the impression template | Text saves (autosave visible) |
| 5 | Create a new template | Form validates; template appears in list |

### 2. Coding Map

| Step | Action | Expected Outcome |
|------|--------|------------------|
| 6 | Navigate to "Coding" section | Coding map table shows UAT rows |
| 7 | Verify CT HEAD → 70450 mapping | Procedure-to-CPT link correct |
| 8 | Add a new mapping | New row saved and displayed |
| 9 | Deactivate a mapping | Active flag toggles, row grayed out |

### 3. Resource Management

| Step | Action | Expected Outcome |
|------|--------|------------------|
| 10 | Navigate to "Resources" | Resource list shows all: defaults + UAT US Room |
| 11 | Edit "UAT US Room" | Change location → "Floor 2" |
| 12 | Save | Resource updated |
| 13 | Add a new resource | Form validates; resource appears in list |

### 4. User Management

| Step | Action | Expected Outcome |
|------|--------|------------------|
| 14 | Navigate to "Users" | User list shows all test.* users |
| 15 | Filter by role | List filters correctly |
| 16 | Deactivate a user | Status → inactive; user cannot log in |

## Expected Data

- `ris_report_templates`: 2 UAT rows (CT Chest, MR Brain)
- `ris_coding_map`: 3 rows (CT HEAD, CT ABDOMEN, CXR 1V)
- `ris_resources`: 1 UAT row (US Room)
- `users`: standard seed users (seed_test_users.py)

## Acceptance Criteria

- [ ] Template manager reads, creates, and edits templates
- [ ] Coding map displays and updates procedure-to-billing-code mappings
- [ ] Resource management adds, edits, and lists resources
- [ ] User management shows all built-in role users
- [ ] All admin CRUD operations persist correctly