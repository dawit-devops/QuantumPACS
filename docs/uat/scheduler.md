# Scheduler UAT Walkthrough

## Prerequisites

```bash
cd backend && .venv/bin/python ../scripts/seed_uat.py --persona scheduler
```

Seeds: 2 resources (CT Room + MR Room) with 5-day schedules, 1 appointment.

## Walkthrough

### 1. Scheduling Dashboard

| Step | Action | Expected Outcome |
|------|--------|------------------|
| 1 | Login as `test.scheduler` / `Test@123456` | Scheduling dashboard loads |
| 2 | Observe the calendar view | CT Room + MR Room visible as resources |
| 3 | View the weekly schedule | 08:00–17:00 slots Mon–Fri for both rooms |

### 2. Create Appointment

| Step | Action | Expected Outcome |
|------|--------|------------------|
| 4 | Click an available time slot (e.g., CT Room, Wed 10:00) | Appointment creation dialog opens |
| 5 | Search for patient "UAT^Scheduling" | Patient auto-completes |
| 6 | Select procedure and set duration (30 min) | Form validates |
| 7 | Save appointment | Slot shows as booked; appears in appointment list |

### 3. Reschedule

| Step | Action | Expected Outcome |
|------|--------|------------------|
| 8 | Click the existing appointment | Edit dialog opens |
| 9 | Drag to a new time slot (e.g., Thu 14:00) | Appointment moves; no double-book conflict |
| 10 | Save | New time reflected in calendar |

### 4. Cancel Appointment

| Step | Action | Expected Outcome |
|------|--------|------------------|
| 11 | Click the appointment | Edit dialog opens |
| 12 | Select "Cancel" | Status → CANCELLED |
| 13 | Verify the slot is now available | Calendar shows the slot as free |

## Expected Data

- `ris_resources`: 2 UAT rows (CT Room, MR Room)
- `ris_resource_schedules`: 10 rows (5 days × 2 resources)
- `ris_appointments`: 1 SCHEDULED row

## Acceptance Criteria

- [ ] Calendar renders resources and weekly schedules
- [ ] Creating an appointment books the slot
- [ ] Rescheduling updates the time without double-booking
- [ ] Cancelling frees the slot
- [ ] Patient search auto-completes from patients table