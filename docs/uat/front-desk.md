# Front-Desk (Receptionist) UAT Walkthrough

## Prerequisites

```bash
cd backend && .venv/bin/python ../scripts/seed_uat.py --persona front-desk
```

Seeds: 1 ARRIVED patient order with completed CXR, BILLED charge.

## Walkthrough

### 1. Patient Check-in (Kiosk)

| Step | Action | Expected Outcome |
|------|--------|------------------|
| 1 | Open the kiosk URL `/checkin?token=uat-tok-front-1` (or generate a valid token) | Kiosk page loads |
| 2 | Verify patient info displays | "UAT^FrontDesk^Patient" shown with visit summary |
| 3 | Click "Confirm Arrival" | POST succeeds; status → ARRIVED |
| 4 | Verify success screen | Confirmation message shown |

### 2. Front Desk Dashboard

| Step | Action | Expected Outcome |
|------|--------|------------------|
| 5 | Login as `test.receptionist` / `Test@123456` | Front desk dashboard loads |
| 6 | View today's scheduled patients | UAT patient visible in the list |
| 7 | Verify ARRIVED status badge | Badge shows "ARRIVED" |

### 3. Patient Registration

| Step | Action | Expected Outcome |
|------|--------|------------------|
| 8 | Click "Register New Patient" | Registration form opens |
| 9 | Enter demo patient data | Form validates required fields |
| 10 | Submit | Patient created; confirmation shown |

### 4. Consent Management

| Step | Action | Expected Outcome |
|------|--------|------------------|
| 11 | Open the patient's consent form | Consent checkbox visible |
| 12 | Toggle consent grant | Consent status updates |
| 13 | Verify consent audit log | Audit entry created in portal.consent_blocked |

## Expected Data

- `ris_orders`: 1 ARRIVED order
- `exams`: 1 completed CR exam
- `ris_charges`: 1 BILLED charge (CPT 71045, $120.00)
- `reports`: 1 final report (CXR)

## Acceptance Criteria

- [ ] Kiosk check-in confirms arrival and shows success
- [ ] Front desk dashboard shows scheduled patients
- [ ] Patient registration creates a new patient record
- [ ] Consent toggle creates audit entries
- [ ] ARRIVED status is reflected in the patient flow