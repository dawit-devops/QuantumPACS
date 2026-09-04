# Biller (Cashier) UAT Walkthrough

## Prerequisites

```bash
cd backend && .venv/bin/python ../scripts/seed_uat.py --persona biller
```

Seeds: 3 charge-claim pairs (PENDING/DRAFT, PAID/PAID, DENIED/DENIED) + prior-auth (DENIED).

## Walkthrough

### 1. Billing Queue

| Step | Action | Expected Outcome |
|------|--------|------------------|
| 1 | Login as `test.cashier` / `Test@123456` | Billing dashboard loads |
| 2 | View the billing queue | 3 charges visible: PENDING, PAID, DENIED |
| 3 | Verify status badges | Distinct colors per status |

### 2. Unbilled View

| Step | Action | Expected Outcome |
|------|--------|------------------|
| 4 | Click "Unbilled" tab | Shows PENDING charge only |
| 5 | Verify aging buckets | Charge appears in appropriate bucket (e.g., "0–5 days") |
| 6 | Group by payer | Payer-based grouping works |

### 3. Submit Claim

| Step | Action | Expected Outcome |
|------|--------|------------------|
| 7 | Select the PENDING charge | Claim detail panel opens |
| 8 | Verify CPT (74176) + ICD-10 (R10.9) | Correct codes displayed |
| 9 | Click "Submit to Payer" | Claim submits; status → SUBMITTED |
| 10 | Verify queue updates | PENDING count decrements |

### 4. Denial Management

| Step | Action | Expected Outcome |
|------|--------|------------------|
| 11 | Open the DENIED charge | Denial reason shown: "Claim/service lacks information" (CO-16) |
| 12 | View prior-auth details | Approved auth visible (UAT-AUTH-001) |
| 13 | Click "Resubmit" | Claim re-processed; status updates |

### 5. Aging Report

| Step | Action | Expected Outcome |
|------|--------|------------------|
| 14 | Navigate to Unbilled Aging | Chart shows aging buckets |
| 15 | Verify group-by options | Date, site, and payer grouping work |

## Expected Data

- `ris_charges`: 3 rows (PENDING, PAID, DENIED)
- `ris_claims`: 3 rows (DRAFT, PAID, DENIED)
- `ris_prior_auth_requests`: 1 APPROVED (for the DENIED charge)

## Acceptance Criteria

- [ ] Billing queue shows all charge statuses with correct filters
- [ ] Unbilled view shows only PENDING charges with aging
- [ ] Claim submission transitions status correctly
- [ ] Denial reasons are displayed and actionable
- [ ] Prior-auth references are visible on claims
- [ ] Aging report renders with group-by controls