# QuantumPACS Frontend UI — Browser Test Plan

## 1. Environment State

### Running Services
| Service | URL | Status |
|---|---|---|
| Frontend (Vite) | http://localhost:5173 | Running |
| Backend (Uvicorn) | http://localhost:8080 | Running |
| PostgreSQL | localhost:5432 | Running |
| Elasticsearch | Not running | Graceful degradation |

### Database Migration State
| Scope | Current | Needed |
|---|---|---|
| Alembic version | `087` | `111` (migrations 088-111 not applied) |
| Existing data | 718 patients, 548 exams, 590 orders, 237 appointments, 239 charges, 160 claims, 752 reports, 214 templates, 82 prior-auths, 243 resources | -- |
| Missing tables | `ris_waitlist`, `ris_staff_time_off`, `ris_protocols`, `ris_corrective_actions`, `ris_payer_contracts`, `ris_fee_schedule_history`, `care_plans`, `ris_referrals`, `ris_handoff_notes`, `ris_discharge_checklists`, `bookmark_collections`, `teaching_files`, `ris_fee_schedule_history` | Tables from migrations 088-111 |

### Test Users (seeded in DB)
Username: `test.<role>` / Password: `Test@123456`

| Username | Role Type | Scope |
|---|---|---|
| `test.super_admin` | Super Admin | Platform |
| `test.tenant_admin` | Tenant Admin | `default` tenant |
| `test.radiologist` | Radiologist | clinical |
| `test.technologist` | Technologist | clinical |
| `test.receptionist` | Receptionist | clinical |
| `test.cashier` | Cashier | clinical |
| `test.care_coordinator` | Care Coordinator | clinical |
| `test.physician` | Physician | clinical |
| `test.resident` | Resident | clinical |
| `test.pacs_admin` | PACS Admin | admin |
| `test.emr_admin` | EMR Admin | admin |
| `test.patient` | Patient | portal |
| `test.referring_physician` | Referring Physician | clinical |
| `test.teleradiologist` | Teleradiologist | clinical |

---

## 2. Pre-Test Setup Steps

### Step 1: Apply missing migrations
```bash
cd backend
.venv/bin/python -m alembic upgrade head
```
This creates all tables for migrations 088-111 (`ris_waitlist`, `ris_staff_time_off`, `ris_protocols`, `ris_corrective_actions`, `ris_payer_contracts`, `ris_fee_schedule_history`, `care_plans`, `ris_referrals`, `ris_handoff_notes`, `ris_discharge_checklists`, `bookmark_collections`, `teaching_files`, etc.)

### Step 2: Restart backend
```bash
systemctl --user restart quantumpacs-backend.service
```

### Step 3: Apply seed data script
Create and run a seed script that fills the new tables with realistic test data for the "Acme Medical Center" tenant (below).

---

## 3. Seed Data Design — "Acme Medical Center"

### 3.1 Tenant & Users
```
Tenant: "Acme Medical Center" (slug: acme)
  ├── Radiologists: Dr. Sarah Chen, Dr. James Wilson, Dr. Maria Rodriguez, Dr. Alex Kim, Dr. Lisa Park
  ├── Technologists: John Smith (CT), Mary Johnson (MR), David Brown (US), 
  │                   Jennifer Lee (CT), Robert Taylor (MR), Patricia Garcia (DX),
  │                   Michael Davis (NM), Susan Miller (CT), Thomas Anderson (MR), Linda Thomas (US)
  ├── Coordinators: Karen White, Daniel Martinez, Emily Clark
  ├── Front Desk: Rachel Green, Chris Adams
  ├── Billing: Kevin Wright, Angela Scott
  └── Dept Manager: Patricia Moore
```

### 3.2 Payer Contracts (B-08) — 6 payers × 10 procedures
| Payer | Payer ID | Procedures | Contracted Rates |
|---|---|---|---|
| Aetna | AETNA | 71250, 72125, 70551, 74176, 76700, 73721, 77067, 78811, 93005, 93880 | 10-20% below list |
| UnitedHealth | UNITED | Same 10 procedures | 12-18% below list |
| Cigna | CIGNA | Same 10 procedures | 8-15% below list |
| BlueCross | BCBS | Same 10 procedures | 5-10% below list |
| Medicare | MEDICARE | Same 10 procedures | 25-30% below list (lowest) |
| Medicaid | MEDICAID | Same 10 procedures | 35-40% below list (lowest) |

### 3.3 Fee Schedule (B-09) — 20 procedures
| Code | Description | List Price |
|---|---|---|
| 71250 | CT Chest without contrast | $350.00 |
| 71260 | CT Chest with contrast | $450.00 |
| 72125 | CT Head without contrast | $320.00 |
| 72141 | MRI Head without contrast | $600.00 |
| 72148 | MRI Lumbar Spine without contrast | $550.00 |
| 70551 | MRI Brain without contrast | $580.00 |
| 74176 | CT Abdomen/Pelvis without contrast | $380.00 |
| 76700 | US Abdomen complete | $250.00 |
| 76705 | US Abdomen limited | $180.00 |
| 73721 | MRI Ankle without contrast | $520.00 |
| 77067 | Mammography screening | $200.00 |
| 78811 | PET limited area | $950.00 |
| 78812 | PET skull to thigh | $1,200.00 |
| 78813 | PET whole body | $1,400.00 |
| 93005 | ECG routine | $80.00 |
| 93880 | Carotid duplex scan | $300.00 |
| 74150 | CT Abdomen without contrast | $360.00 |
| 74160 | CT Abdomen with contrast | $460.00 |
| 72192 | CT Pelvis without contrast | $340.00 |
| 72156 | MRI Cervical Spine without contrast | $540.00 |

### 3.4 Staff Time-Off (DM-07) — 8 requests across 3 months
| Staff | Dates | Modality | Status | Reason |
|---|---|---|---|---|
| John Smith | Sep 5-7 | CT | APPROVED | Vacation |
| Mary Johnson | Sep 10-12 | MR | APPROVED | Conference |
| David Brown | Sep 15 | US | APPROVED | Personal day |
| Jennifer Lee | Sep 20-22 | CT | REQUESTED | Vacation |
| Robert Taylor | Oct 1-3 | MR | APPROVED | Medical |
| Patricia Garcia | Oct 5-6 | DX | REJECTED | Staffing conflict |
| Michael Davis | Oct 10-12 | NM | APPROVED | Vacation |
| Susan Miller | Oct 15 | CT | REQUESTED | Personal day |

### 3.5 Coverage Gaps (DM-07) — 3 gaps created by overlapping schedules
Technologists on approved time-off who have exams scheduled on the same dates:
- John Smith (Sep 5-7) assigned to CT exams on Sep 5, 6
- Mary Johnson (Sep 10-12) assigned to MR exams on Sep 10, 11
- Robert Taylor (Oct 1-3) assigned to MR exams on Oct 2

### 3.6 Waitlist (S-08) — 5 entries
| Patient | Modality | Priority | Status | Notes |
|---|---|---|---|---|
| Alice Wonderland | CT | STAT | WAITING | Cancel slot 9/3 am |
| Bob Builder | MR | URGENT | WAITING | Waited 5 days |
| Carol Kingsley | US | ROUTINE | NOTIFIED | Called 9/1 |
| Dan Marino | CT | URGENT | BOOKED | Converted 9/2 |
| Eve Adams | DX | ROUTINE | EXPIRED | No response |

### 3.7 Protocols (QA-09) — 8 protocols
| Protocol | Modality | Version | Default |
|---|---|---|---|
| CT Chest Standard | CT | 1 | Yes |
| CT Chest High Res | CT | 1 | No |
| CT Abdomen Standard | CT | 2 | Yes |
| MRI Brain Standard | MR | 1 | Yes |
| MRI Lumbar Spine | MR | 1 | Yes |
| MRI Knee | MR | 2 | No |
| US Abdomen Complete | US | 1 | Yes |
| Mammography Screening | MG | 1 | Yes |

### 3.8 Corrective Actions (QA-11) — 5 actions
| Title | Status | Priority | Due | Assignee |
|---|---|---|---|---|
| Calibrate CT scanner #2 | open | critical | Sep 10 | John Smith |
| Update contrast protocol | in_progress | high | Sep 15 | David Brown |
| Retrain staff on dose logging | open | medium | Sep 30 | Jennifer Lee |
| Replace MR coil | open | high | Oct 1 | Robert Taylor |
| QA review backlog reduction | completed | medium | Aug 30 | Patricia Moore |

### 3.9 Care Plans (CC-02) — 5 plans
| Patient | Title | Status | Tasks |
|---|---|---|---|
| Alice Wonderland | Post-op follow-up | active | Call patient, Schedule imaging, Review results |
| Bob Builder | Diabetes management | active | HbA1c check, Nutrition consult, Endocrinologist referral |
| Carol Kingsley | Mammogram follow-up | completed | Biopsy scheduled, Results reviewed, Patient notified |
| Dan Marino | Cardiac workup | on_hold | Stress test pending, Cardiologist consult |
| Eve Adams | Pre-surgery clearance | active | Blood work, Chest X-ray, EKG, Anesthesiology consult |

### 3.10 Referrals (CC-05) — 5 referrals
| From | To | Specialty | Status |
|---|---|---|---|
| Dr. Smith | Dr. Wilson | Orthopedics | pending |
| Dr. Chen | Dr. Rodriguez | Cardiology | accepted |
| Dr. Patel | Dr. Kim | Neurology | completed |
| Dr. Garcia | Dr. Lee | Oncology | pending |
| Dr. Johnson | Dr. Brown | Pulmonology | cancelled |

### 3.11 Handoff Notes (CC-08) — 5 notes
| Patient | Note | Priority | Read |
|---|---|---|---|
| Alice Wonderland | Patient has latex allergy | urgent | No |
| Bob Builder | Diabetic, needs scheduling | normal | No |
| Carol Kingsley | Follow-up mammogram due | low | Yes |
| Dan Marino | Cardiac history, monitor | high | No |
| Eve Adams | Pre-op clearances pending | normal | No |

### 3.12 Discharge Checklists (CC-06) — 3 checklists
| Patient | Title | Status | Items |
|---|---|---|---|
| Alice Wonderland | Post-contrast monitoring | open | Check vitals, Monitor for reaction, Document findings |
| Bob Builder | Diabetes discharge | completed | Medication review, Follow-up scheduled, Diet plan provided |
| Carol Kingsley | Post-biopsy care | open | Wound check, Activity restrictions, Emergency contact |

### 3.13 Bookmark Collections (R-08) — 2 collections
| Name | Description | Shared | Bookmarks |
|---|---|---|---|
| Interesting Chest Cases | Teaching cases for residents | Yes | 5 study UIDs |
| My Research | Research study references | No | 3 study UIDs |

### 3.14 Study Bookmarks (R-08) — 8 bookmarks
Across the 2 collections, referencing existing study UIDs from the database.

### 3.15 Prior Auth requests — 8 requests
| Patient | Procedure | Payer | Status | Auth # |
|---|---|---|---|---|
| Alice | MRI Brain | AETNA | APPROVED | AUTH-001 |
| Bob | CT Chest | UNITED | PENDING | -- |
| Carol | PET whole body | CIGNA | DENIED | -- |
| Dan | MRI Lumbar | BCBS | APPROVED | AUTH-004 |
| Eve | CT Abdomen | MEDICARE | REQUIRED | -- |
| Frank | MRI Knee | AETNA | PENDING | -- |
| Grace | US Abdomen | MEDICAID | EXPIRED | AUTH-007 |
| Henry | CT Head | UNITED | NOT_REQUIRED | -- |

---

## 4. Test Assessment Checklist

### 4.1 Workspace Features

| # | Feature | Route | Test User | Expected Behavior | Actual | Notes |
|---|---|---|---|---|---|---|
| **READING** | | | | | | |
| 1 | Reading Worklist loads | `/reading` | test.radiologist | List of exams for dictation shown, filters work | | |
| 2 | Reading Console loads | `/reading/:examId` | test.radiologist | Viewer + report sidebar; tools, measurements work | | |
| 3 | Peer Review Inbox | `/peer-review` | test.radiologist | List of exams needing peer review | | |
| 4 | Resident Home | `/reading/home` | test.resident | Resident dashboard with stats | | |
| 5 | My Progress | `/reading/progress` | test.resident | Reading stats + case mix | | |
| 6 | Teaching Library | `/teaching` | test.radiologist | Teaching files list | | |
| 7 | Critical Results | `/critical` | test.radiologist | Critical result flagging/acknowledgment | | |
| 8 | Study Bookmarks | `/study-bookmarks` | test.radiologist | Bookmark collections + studies | | |
| **ACQUISITION** | | | | | | |
| 9 | My Exams | `/exams` | test.technologist | Exam list with filters, no console errors | | |
| 10 | Exam Console | `/exams/:id` | test.technologist | Exam workflow, vitals, checklists, consent | | |
| 11 | Modality Worklist | `/worklist` | test.technologist | MWL entries, search, create/edit | | |
| 12 | Tracking Board | `/tracking` | test.technologist | Exam status tracking, KPI, timeline | | |
| 13 | Schedule Board | `/schedule-board` | test.technologist | Calendar view of appointments | | |
| 14 | Calendar | `/schedule` | test.technologist | Day/Week/Month/Gantt views, resource filters | | |
| 15 | Resources | `/schedule/resources` | test.technologist | Resource management, schedule templates | | |
| **COORDINATION** | | | | | | |
| 16 | Orders | `/orders` | test.care_coordinator | Order list, search, history, create | | |
| 17 | Prior Auth | `/prior-auth` | test.care_coordinator | PA requests list, submit, approve/deny, expiry | | |
| 18 | Reminders | `/reminders` | test.care_coordinator | Reminder log, config, opt-outs | | |
| 19 | Care Plans | `/care-plans` | test.care_coordinator | Care plan list, create, edit, status transitions | | |
| 20 | Communications | `/communications` | test.care_coordinator | Communication log | | |
| 21 | Nursing Prep | `/nursing` | test.technologist | Prep list, vitals, checklists, consent | | |
| 22 | Handoff Notes | `/handoff-notes` | test.care_coordinator | Handoff notes list, create, mark read | | |
| 23 | Referrals | `/referrals` | test.care_coordinator | Referral list, create, status update | | |
| 24 | Discharge Checklists | `/discharge-checklists` | test.care_coordinator | Checklist list, create, update | | |
| **BILLING** | | | | | | |
| 25 | Billing Queue | `/billing/queue` | test.cashier | Queue with CPT suggestions, drop charges, submit claims | | |
| 26 | Claims | `/billing/claims` | test.cashier | Claim list, batch submit, claim history | | |
| 27 | Revenue | `/billing/revenue` | test.cashier | Revenue dashboard (by payer, modality, aging) | | |
| 28 | Unbilled Aging | `/billing/unbilled` | test.cashier | Unbilled aging groups, group by date/site/payer | | |
| 29 | Denial Rework | `/billing/denials` | test.cashier | Denial list, rework, resubmit, history | | |
| 30 | Fee Schedule | `/billing/fee-schedule` | test.cashier | Fee schedule list, edit, import, history, payer contracts, comparison | | |
| **QA** | | | | | | |
| 31 | QA Queue | `/qa/queue` | test.technologist | QA queue list, submit scores | | |
| 32 | QA Review | `/qa/review/:examId` | test.technologist | QA review form for an exam | | |
| 33 | Protocols | `/qa/protocols` | test.technologist | Protocol registry list, edit, set default | | |
| 34 | Incidents | `/qa/incidents` | test.technologist | Incident list, log, resolve | | |
| 35 | Corrective Actions | `/qa/actions` | test.technologist | Corrective action list, create, edit, status | | |
| 36 | QA Analytics | `/qa/analytics` | test.technologist | Reject analysis, dose tracking, tech metrics, trends | | |

### 4.2 Admin Features

| # | Feature | Route | Test User | Expected Behavior | Actual | Notes |
|---|---|---|---|---|---|---|
| **ADMIN** | | | | | | |
| 37 | Admin Dashboard | `/admin` | test.super_admin | System overview with health/metrics | | |
| 38 | RIS Dashboard | `/admin/ris-dashboard` | test.super_admin | KPI cards, TAT drill-down, workload, equipment util | | |
| 39 | Staff Schedule | `/admin/staff-schedule` | test.super_admin | Schedule table + Time Off tab with coverage gaps | | |
| 40 | Users | `/users` | test.super_admin | User list, create, edit, activate/deactivate | | |
| 41 | Roles | `/roles` | test.super_admin | Role list, create, edit, permissions | | |
| 42 | Tenants | `/tenants` | test.super_admin | Tenant list, create, health/usage | | |
| 43 | Logs | `/logs` | test.super_admin | Log viewer, filters, CSV export | | |
| 44 | Metrics | `/metrics` | test.super_admin | Dashboard metrics, health status | | |
| 45 | Backups | `/admin/backups` | test.super_admin | Backup list, create, restore, download | | |
| 46 | Settings | `/admin/settings` | test.super_admin | Admin config settings | | |
| 47 | Maintenance | `/admin/maintenance` | test.super_admin | Maintenance mode toggle | | |
| 48 | Integrations | `/integrations` | test.super_admin | OAuth providers (list, test OIDC), webhooks | | |
| 49 | FHIR Config | `/fhir/config` | test.super_admin | FHIR client config/monitoring/docs | | |
| 50 | FHIR Monitoring | `/fhir/monitoring` | test.super_admin | FHIR metrics/recent requests | | |
| 51 | HL7 Dashboard | `/hl7` | test.super_admin | HL7 messages, metrics, config | | |
| 52 | Interface Health | `/admin/interfaces` | test.super_admin | Interface health, exceptions, retry | | |
| 53 | Replicas | `/replicas` | test.super_admin | Replica list, CRUD | | |
| 54 | Routing | `/routing` | test.super_admin | Routing rules, CRUD | | |
| 55 | Service Keys | `/service-keys` | test.super_admin | API key list, create, revoke | | |
| 56 | Report Templates | `/admin/report-templates` | test.super_admin | Template list, versions, publish, rollback | | |
| 57 | DICOMweb Server | `/dicomweb` | test.super_admin | DICOMweb admin info, metrics | | |
| 58 | DICOMweb Store | `/dicomweb/store` | test.super_admin | STOW-RS upload UI | | |
| 59 | DICOMweb Browser | `/dicomweb/browser` | test.super_admin | Study browser with QIDO-RS | | |

### 4.3 Front Desk & Portal

| # | Feature | Route | Test User | Expected Behavior | Actual | Notes |
|---|---|---|---|---|---|---|
| **FRONT DESK** | | | | | | |
| 60 | Registration | `/frontdesk/registration` | test.receptionist | Patient search, create, registration form | | |
| 61 | Today's Schedule | `/frontdesk/schedule` | test.receptionist | Schedule view, check-in, no-show | | |
| 62 | Waiting Queue | `/frontdesk/queue` | test.receptionist | Queue management | | |
| **PORTAL** | | | | | | |
| 63 | My Records | `/portal` | test.patient | Portal home, scope, demographics | | |
| 64 | Appointments | `/portal/appointments` | test.patient | Appointment list, consent toggle | | |
| 65 | Results | `/portal/results` | test.patient | Report list (body part, signed by columns), detail | | |
| 66 | Follow-ups | `/portal/follow-ups` | test.patient | Follow-up list, create, update | | |

### 4.4 Viewer & Files

| # | Feature | Route | Test User | Expected Behavior | Actual | Notes |
|---|---|---|---|---|---|---|
| 67 | Files (home) | `/` | test.radiologist | Study search, QIDO results, pagination | | |
| 68 | Study Detail (viewer) | `/files/:id` | test.radiologist | Cornerstone3D viewer, tools, measurements, W/L, series | | |
| 69 | Multi-study compare | `/files/:id?compare=1` | test.radiologist | Side-by-side viewports, prior study selection | | |
| 70 | Patient page | `/patients/:id` | test.radiologist | Patient summary, studies, orders | | |

### 4.5 System Integration

| # | Feature | Test | Expected Behavior | Actual | Notes |
|---|---|---|---|---|---|
| 71 | Login | Login as each role | Successful login, redirect to role-appropriate landing | | |
| 72 | Logout | Click logout | Session cleared, redirect to login | | |
| 73 | 404 page | Navigate to `/nonexistent` | Custom 404 page shown | | |
| 74 | Permission gate | test.technologist visits `/admin` | 403 Forbidden/redirect | | |
| 75 | Notification bell | Login as test.radiologist | Unread badge count, dropdown, mark read | | |
| 76 | Theme toggle | Click theme toggle | Light/dark mode switch, persistent | | |
| 77 | API error handling | Stop backend, navigate | Graceful error states, retry buttons | | |

### 4.6 DM-07 Specific (Time-Off & Coverage Gaps)

| # | Step | Expected | Actual | Notes |
|---|---|---|---|---|
| 78 | Login as test.super_admin, navigate to Staff Schedule | Schedules tab shown with exam table | | |
| 79 | Click "Time Off & Coverage" tab | Time-off table loaded with 8 requests | | |
| 80 | Coverage gaps alert shown | Warning alert with 3 gap entries | | |
| 81 | Click "Request Time Off" | Modal opens with staff/date/reason form | | |
| 82 | Fill + submit new request | POST to API, table refreshes | | |
| 83 | Click "Approve" on a REQUESTED row | PATCH called, status changes to APPROVED | | |
| 84 | Click "Reject" on a REQUESTED row | PATCH called, status changes to REJECTED | | |
| 85 | Click "Cancel" on an APPROVED row | PATCH called, status changes to CANCELLED | | |
| 86 | Click "Refresh" on time-off tab | Data reloaded from API | | |

### 4.7 B-08/B-09 Specific (Fee Schedule & Contracts)

| # | Step | Expected | Actual | Notes |
|---|---|---|---|---|
| 87 | Login as test.cashier, navigate to /billing/fee-schedule | Fee Schedule tab with 20 procedures | | |
| 88 | Search by code "71250" | Filtered to 1 result | | |
| 89 | Click "Edit" on a row | Modal opens with price/description fields | | |
| 90 | Save price change | PUT called, table updates, history recorded | | |
| 91 | Click "History" on a row | Drawer opens with version history | | |
| 92 | Click "Import (CMS)" | Modal opens with CSV textarea | | |
| 93 | Paste CSV rows + Import | POST called, table refreshes | | |
| 94 | Click "Payer Contracts" tab | Contracts table with 6 payers × 10 procedures | | |
| 95 | Charge vs Contract comparison loads | Comparison table with over_charge/under_charge flags | | |
| 96 | Click "Add Contract" | Modal opens with payer/procedure/rate fields | | |
| 97 | Fill + save new contract | POST called, table refreshes | | |
| 98 | Click "Edit" on a contract | Modal opens with pre-filled values | | |
| 99 | Save rate change | PUT called, table updates | | |
| 100 | Click "Deactivate" on a contract | Popconfirm, then DELETE called, row deactivated | | |

### 4.8 Billing Queue Workflow

| # | Step | Expected | Actual | Notes |
|---|---|---|---|---|
| 101 | Login as test.cashier, navigate to /billing/queue | Billing queue with unbilled charges | | |
| 102 | CPT suggestions loaded | Alert shown with suggestion info | | |
| 103 | Select charge rows | Batch action buttons appear | | |
| 104 | Click "Confirm & Drop" | Charge dropped, queue refreshes | | |
| 105 | Click "Submit claims" | Batch submit, claims created | | |
| 106 | Navigate to /billing/claims | Claims list with submitted claims | | |
| 107 | Click claim history | History drawer/timeline shown | | |
| 108 | Navigate to /billing/revenue | Revenue dashboard with by-payer/modality/aging | | |
| 109 | Navigate to /billing/unbilled | Unbilled aging groups | | |
| 110 | Navigate to /billing/denials | Denial list, rework actions | | |

### 4.9 QA Workflow

| # | Step | Expected | Actual | Notes |
|---|---|---|---|---|
| 111 | Login as test.technologist, navigate to /qa/queue | QA queue with exams to review | | |
| 112 | Click on exam to review | QA review form with scoring | | |
| 113 | Navigate to /qa/protocols | Protocol registry with 8 protocols | | |
| 114 | Navigate to /qa/incidents | Incident list, can log new | | |
| 115 | Navigate to /qa/actions | Corrective action list with 5 actions | | |
| 116 | Navigate to /qa/analytics | Analytics dashboard with graphs | | |

### 4.10 Scheduling Workflow

| # | Step | Expected | Actual | Notes |
|---|---|---|---|---|
| 117 | Login as test.receptionist, navigate to /schedule | Calendar with Day/Week/Month/Gantt views | | |
| 118 | Toggle resource filters | Resources filtered by type/modality | | |
| 119 | Click on a time slot | Booking modal opens | | |
| 120 | Book appointment | Appointment created, calendar refreshes | | |
| 121 | Navigate to /schedule/resources | Resource list, schedules, templates | | |
| 122 | Apply schedule template | Template applied to resource | | |
| 123 | Navigate to /schedule-board | Schedule board view | | |

### 4.11 Prior Auth + Reminders Workflow

| # | Step | Expected | Actual | Notes |
|---|---|---|---|---|
| 124 | Login as test.care_coordinator, navigate to /prior-auth | 8 PA requests in various states | | |
| 125 | Submit for review on PENDING request | Status updated, notification sent | | |
| 126 | Approve/Deny on reviewable request | Decision recorded | | |
| 127 | Navigate to /reminders | Reminder log, config, opt-outs | | |
| 128 | Toggle reminder config | Active/inactive toggle | | |

### 4.12 Console Errors & Network

| # | Check | Expected | Actual | Notes |
|---|---|---|---|---|
| 129 | Chrome DevTools Console | 0 errors, 0 warnings (graceful degradation for ES) | | |
| 130 | Chrome DevTools Network | All API calls return 200/201/4xx expected | | |
| 131 | Axe a11y scan | 0 critical violations on each page | | |

---

## 5. Test Execution Protocol

### 5.1 Per-Feature Walkthrough
For each checklist item:
1. Open Chrome DevTools (F12) → Console + Network tabs
2. Navigate to the route URL
3. Wait for the page to fully load (network idle)
4. Verify the page renders correctly (no blank screens, no loading spinners that never resolve)
5. Interact with key controls (filters, buttons, forms)
6. Check Console for errors (red = critical, yellow = warning)
7. Check Network tab for expected API calls (correct endpoint, method, status code)
8. Record Pass/Fail/Notes in the checklist

### 5.2 Login Sequence
Start with `test.super_admin` (most permissions, can see all areas), then test role-restricted pages with the appropriate role:

1. `test.super_admin` — Admin, Users, Tenants, Roles, Logs, Metrics, Backups, Settings, Maintenance, Integrations, FHIR, HL7, DICOMweb, Routing, Replicas, Service Keys, Report Templates
2. `test.radiologist` — Reading, Peer Review, Teaching Library, Critical Results, Study Bookmarks, Files, Viewer, Patient
3. `test.technologist` — Exams, Worklist, Tracking, Schedule, QA, Nursing, Protocols
4. `test.care_coordinator` — Orders, Prior Auth, Reminders, Care Plans, Communications, Handoff Notes, Referrals, Discharge Checklists
5. `test.cashier` — Billing Queue, Claims, Revenue, Unbilled, Denials, Fee Schedule, Contracts
6. `test.receptionist` — Front Desk Registration, Schedule, Queue
7. `test.patient` — Portal Home, Appointments, Results, Follow-ups

### 5.3 Error Severity Classification
- **CRITICAL**: Page fails to load, 500 error, data loss, auth bypass
- **HIGH**: Feature doesn't work, wrong data displayed, API call fails
- **MEDIUM**: UI glitch, missing styles, minor functionality issue
- **LOW**: Cosmetic, alignment, missing tooltip, slow response
- **INFO**: Console warning, deprecated API, known ES degradation

---

## 6. Risks & Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| Migrations 088-111 not applied | Several features fail (waitlist, time-off, protocols, contracts) | Run `alembic upgrade head` before testing |
| Elasticsearch not running | Search pages degrade gracefully (known behavior) | Document as expected, not a test failure |
| Missing seed data for new tables | Empty states on new features | Create seed script before testing |
| 402 budget limit mid-testing | Session interrupted | Commit after each test area, use compact context |
| Systemd backend restart needed after migrations | Backend unavailable during test | Schedule restart, verify health before each test batch |