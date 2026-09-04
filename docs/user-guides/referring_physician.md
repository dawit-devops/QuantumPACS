# Referring Physician User Guide — QuantumPACS
Version: 793b087 | Role: referring_physician | Applies to: clinical workspace

## 1. About this role

The **Referring Physician** is a read-only clinical user. You refer patients
for imaging, then check back on the results: view reports, track critical
findings, and see your patients' orders, schedules, prior authorizations, care
plans, and communications. You do **not** write or sign reports, do not operate
the acquisition/modality workflow, and cannot run the admin console or billing.

You land on the **Reading Worklist** (`/reading`) when you sign in.

Key responsibility split:
- **You do (read-only):** view reports, critical results, orders, schedules,
  prior auth, care plans, communications, teaching library.
- **You cannot:** write reports (radiologist), operate the modality worklist /
  scheduling (technologist/scheduler), manage users/tenants/logs (admins),
  access billing/QA/portal/DICOMweb.

## 2. Signing in

1. Go to the QuantumPACS login page.
2. Enter your username (e.g. `test.referring_physician` in dev) and password.
3. Sign in. You land on the **Reading Worklist**.

## 3. Getting around

Your sidebar is intentionally minimal — only what a referring physician needs:

| Section | What you can do there |
|---|---|
| **Reading** | Reading Worklist, Teaching Library, Critical Results |
| **Coordination** | Orders, Prior Auth, Reminders, Care Plans, Communications |
| **Account** | Your profile and preferences |

You do **not** see Files, Acquisition, Admin, Billing, QA, Metrics, Front Desk,
or Portal — those are for other roles.

## 4. Surface-by-surface guide

### 4.1 Reading Worklist (`/reading`)
- **Purpose:** exams awaiting interpretation.
- **How to:** filter by report status, modality, patient/accession search,
  referring physician; toggle "Assigned to me", "Awaiting review", "Unread
  only". Auto-refreshes every 30s.
- **Status:** PASS

### 4.2 Teaching Library (`/teaching`)
- **Purpose:** curated teaching cases.
- **Status:** PASS (empty until cases are submitted)

### 4.3 Critical Results (`/critical`)
- **Purpose:** monitoring critical findings and alerts.
- **How to:** view FLAGGED / ESCALATED / ACKNOWLEDGED alerts. Filter by status.
- **Status:** PASS (view-only)

### 4.4 Orders (`/orders`)
- **Purpose:** order list for your patients.
- **Status:** PASS (read-only)

### 4.5 Prior Auth (`/prior-auth`)
- **Purpose:** prior authorization management.
- **Status:** PASS (read-only)

### 4.6 Reminders (`/reminders`)
- **Purpose:** reminder config and delivery audit log.
- **Status:** PASS (read-only)

### 4.7 Care Plans (`/care-plans`)
- **Purpose:** per-patient care plan board.
- **Status:** PASS (read-only)

### 4.8 Communications (`/communications`)
- **Purpose:** patient communication log.
- **Status:** PASS (read-only)

## 5. Common workflows (walkthroughs)

### 5.1 Check a patient's imaging results
1. Open **Reading Worklist** (`/reading`).
2. Search by patient or accession.
3. Open the exam/report to view the finding.

### 5.2 Monitor critical results for your patients
1. Open **Critical Results** (`/critical`).
2. Review FLAGGED and ESCALATED alerts for your patients.

### 5.3 Check prior auth status before a referral
1. Open **Prior Auth** (`/prior-auth`).
2. Look up the patient's authorization status.

### 5.4 View a patient's care plan
1. Open **Care Plans** (`/care-plans`).
2. Browse the plan board and task status.

## 6. Permissions summary

You have (all read-only):
- **Clinical read:** PATIENT_READ, ORDER_READ, SCHEDULE_READ, WORKLIST_READ,
  REPORT_READ, VIEWER_READ, STUDY_READ, CHART_READ, RESULTS_READ,
  PRIOR_AUTH_READ

You **cannot**:
- Write or sign reports
- Operate the modality worklist / acquisition / scheduling workflow
- Access Files, DICOMweb, billing, QA, metrics, portal, or admin console
- Manage users, tenants, roles, or logs

## 7. Troubleshooting & known limits

- **No Files/Acquisition in the sidebar:** by design — those surfaces are for
  other roles. The routes still work if deep-linked.
- **"No curated teaching cases yet":** expected until cases are submitted.
- **Elasticsearch offline:** search degrades gracefully.