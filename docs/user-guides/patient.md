# Patient User Guide — QuantumPACS
Version: 716b84b | Role: patient | Applies to: patient portal (own records)

## 1. About this role

The **Patient** uses the self-service portal to view their own records,
appointments, test results, and follow-up tasks. All data is **own-data
scoped** — you only ever see your own health information.

You land on **My Records** (`/portal`) when you sign in.

## 2. Signing in

1. Go to the QuantumPACS login page.
2. Choose your tenant (e.g. Acme Medical Center) and enter your username
   (e.g. `acme.patient`) + password.
3. Sign in. You land on **My Records**.

Your account must be linked to a patient record in the system. If you see
"No records are shared with you yet", contact your radiology department.

## 3. Getting around

Your sidebar is the patient portal:

| Section | What you can do there |
|---|---|
| **My Records** | My Records, Appointments, Results, Follow-ups |
| **Account** | Your profile and preferences |

You do **not** see Files, Reading, Acquisition, Admin, Billing, Front Desk,
QA, Metrics, or Portal-for-staff — those are for other roles.

## 4. Surface-by-surface guide

### 4.1 My Records (`/portal`)
- **Purpose:** your shared patient records.
- **Status:** PASS (empty state: "No records are shared with you yet" if your
  account isn't linked)

### 4.2 Appointments (`/portal/appointments`)
- **Purpose:** your upcoming appointments.
- **Status:** PASS

### 4.3 Results (`/portal/results`)
- **Purpose:** your released test/imaging results.
- **Status:** PASS

### 4.4 Follow-ups (`/portal/follow-ups`)
- **Purpose:** your follow-up tasks.
- **Status:** PASS

## 5. Common workflows (walkthroughs)

### 5.1 View your imaging results
1. Sign in, land on **My Records** (`/portal`).
2. Open **Results** (`/portal/results`) to see released reports.

### 5.2 Check your appointments
1. Open **Appointments** (`/portal/appointments`).
2. Review upcoming visit dates/times.

### 5.3 Manage follow-ups
1. Open **Follow-ups** (`/portal/follow-ups`).
2. Review tasks; mark status as applicable.

## 6. Permissions summary

You have (all own-data scoped):
- **Portal:** PORTAL_READ, FOLLOW_UP_SELF, NOTIFICATIONS_SELF
- **View own:** CHART_READ, RESULTS_READ, MED_ORDER_READ, SCHEDULE_READ,
  VIEWER_READ

You **cannot**:
- Access anyone else's data
- Run any admin, clinical, billing, or front-desk surface
- Upload files or operate the DICOMweb console

## 7. Troubleshooting & known limits

- **"No records are shared with you yet":** your account isn't linked to a
  patient record — contact the radiology department.
- **Your sidebar is portal-only:** by design — patients see only their own
  portal surfaces.
- **Elasticsearch offline:** search degrades gracefully.