# Physician User Guide — QuantumPACS
Version: ae42f57 | Role: physician | Applies to: clinical workspace

## 1. About this role

The **Physician** is a clinical user who reads imaging reports and manages
patient care through the EMR side of the platform. You view radiology findings,
track critical results, see your patients' orders and schedules, and manage
care plans — but you do **not** author or sign radiology reports (that is the
radiologist's domain).

You land on the **Reading Worklist** (`/reading`) when you sign in.

Key responsibility split:
- **You do:** read reports, view critical results, browse the schedule/orders/
  prior-auth/care plans/communications, view DICOM studies via the browser,
  browse files.
- **Radiologist does:** write + sign reports (REPORT_WRITE/SIGN).
- **You cannot:** run the admin console, billing, QA, front desk operations, or
  portal (patient-facing).

## 2. Signing in

1. Go to the QuantumPACS login page.
2. Enter your username (e.g. `test.physician` in dev) and password.
3. Sign in. You land on the **Reading Worklist**.

## 3. Getting around

The sidebar shows the sections you can reach:

| Section | What you can do there |
|---|---|
| **Files** | Browse/upload/view DICOM studies |
| **Reading** | Reading Worklist, Teaching Library, Critical Results |
| **Acquisition** | Modality Worklist, Tracking Board, Schedule Board, Calendar, Resources |
| **Coordination** | Orders, Prior Auth, Reminders, Care Plans, Communications |
| **Admin** | DICOMweb (Server, Store, Study Browser) — read-only |
| **Account** | Your profile and preferences |

You do **not** see the Front Desk, Billing, QA, Portal, or Metrics sections.

## 4. Surface-by-surface guide

### 4.1 Reading Worklist (`/reading`)
- **Purpose:** handed-off exams awaiting interpretation.
- **How to:** filter by report status, modality, patient/accession search,
  referring physician; toggle "Assigned to me", "Awaiting review", "Unread
  only". Auto-refreshes every 30s.
- **Status:** PASS
- **Notes:** shows CT/etc. exams in draft status with Continue buttons. You can
  view exams but not write the report.

### 4.2 Teaching Library (`/teaching`)
- **Purpose:** curated teaching cases.
- **Status:** PASS (empty until cases are submitted from the reading console)

### 4.3 Critical Results (`/critical`)
- **Purpose:** monitoring critical findings and alerts.
- **How to:** view FLAGGED / ESCALATED / ACKNOWLEDGED alerts with patient,
  finding, recipient, flagged-at, and action columns. Filter by status.
- **Status:** PASS
- **Notes:** you can view; acknowledging requires a critical-results grant (403
  if you don't hold it — the Acknowledge button will error).

### 4.4 Modality Worklist (`/worklist`)
- **Purpose:** DICOM modality worklist.
- **Status:** PASS

### 4.5 Tracking Board (`/tracking`)
- **Purpose:** live exam tracking.
- **Status:** PASS

### 4.6 Schedule Board (`/schedule-board`)
- **Purpose:** day schedule with capacity.
- **Status:** PASS

### 4.7 Calendar (`/schedule`)
- **Purpose:** resource calendar view.
- **Status:** PASS

### 4.8 Resources (`/schedule/resources`)
- **Purpose:** resource definitions (rooms/modalities/techs).
- **Status:** PASS

### 4.9 Orders (`/orders`)
- **Purpose:** order list.
- **Status:** PASS

### 4.10 Prior Auth (`/prior-auth`)
- **Purpose:** prior authorization management.
- **Status:** PASS

### 4.11 Reminders (`/reminders`)
- **Purpose:** reminder config and delivery audit log.
- **Status:** PASS

### 4.12 Care Plans (`/care-plans`)
- **Purpose:** per-patient care plan board.
- **Status:** PASS

### 4.13 Communications (`/communications`)
- **Purpose:** patient communication log (append-only).
- **Status:** PASS

### 4.14 DICOMweb Server (`/dicomweb`)
- **Purpose:** DICOMweb server info, metrics, request log.
- **Status:** PASS (read-only)

### 4.15 DICOMweb Store (`/dicomweb/store`)
- **Purpose:** STOW-RS upload.
- **Status:** PASS — upload returns 403 (you don't hold DICOMWEB_WRITE; read-only)

### 4.16 DICOMweb Study Browser (`/dicomweb/browser`)
- **Purpose:** search studies, expand series/instances, WADO-RS render, archive
  download.
- **How to:** enter a patient ID, click Search, expand results.
- **Status:** PASS

### 4.17 Files (`/`)
- **Purpose:** browse/upload/view DICOM files and studies.
- **Status:** PASS

## 5. Common workflows (walkthroughs)

### 5.1 Check today's pending reads
1. Land on **Reading Worklist** (`/reading`).
2. Review the list of draft exams; filter by modality or search a patient.
3. Open an exam to view the images (the exam console / reading view).

### 5.2 Monitor critical results
1. Open **Critical Results** (`/critical`).
2. Review FLAGGED and ESCALATED alerts.
3. If you hold the ack grant, click Acknowledge; otherwise pass the alert to the
   responsible radiologist.

### 5.3 Look up a patient's schedule
1. Open **Calendar** (`/schedule`) or **Schedule Board** (`/schedule-board`).
2. Find the patient's appointments by date/modality.

### 5.4 Review a study via DICOMweb
1. Open **DICOMweb Study Browser** (`/dicomweb/browser`).
2. Enter a patient ID and search.
3. Expand the study → series → instances to view/render.

### 5.5 View a care plan
1. Open **Care Plans** (`/care-plans`).
2. Search/browse patient plans and their task status.

## 6. Permissions summary

You can (selected):
- **Clinical read:** REPORT_READ, PATIENT_READ, STUDY_READ, VIEWER_READ,
  CHART_READ, RESULTS_READ, WORKLIST_READ, SCHEDULE_READ, ORDER_READ,
  PRIOR_AUTH_READ
- **EMR write:** ENCOUNTER_WRITE, NOTE_SIGN, MED_ORDER_READ/WRITE, MAR_READ,
  ORDER_WRITE, CARE_PLAN_WRITE
- **Legacy reach:** FILE_READ, DICOMWEB_READ (Files + DICOMweb browser)

You **cannot**:
- Write/sign reports (REPORT_WRITE/SIGN — radiologist)
- Run the admin console, billing, QA, metrics, or portal surfaces
- Manage users/roles/tenants/logs/replicas
- Upload to DICOMweb (STOW) — no DICOMWEB_WRITE

## 7. Troubleshooting & known limits

- **Acknowledge button errors with 403:** you don't hold the critical-results
  write grant — view-only.
- **DICOMweb Store upload fails with 403:** read-only — you can browse but not
  store.
- **No Front Desk in the sidebar:** by design — those surfaces are for
  front-office staff (the routes still work if deep-linked).
- **Elasticsearch offline:** search degrades gracefully; study browser still
  works.