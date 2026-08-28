# Receptionist User Guide — QuantumPACS
Version: d92268c | Role: receptionist | Applies to: front-desk workspace

## 1. About this role

The **Receptionist** is the front-office user who registers patients, books
visits, checks patients in, and manages the waiting queue. You also look up
patients and their orders during registration.

You land on **Patient Registration** (`/frontdesk/registration`) when you sign
in.

Key responsibility split:
- **You do:** register patients, book walk-ins, check in, manage the waiting
  queue, view today's schedule, search patients, view orders/care plans/
  communications.
- **You cannot:** run the admin console, billing, QA, reading/imaging, portal,
  or the modality worklist.

## 2. Signing in

1. Go to the QuantumPACS login page.
2. Choose your tenant (e.g. Acme Medical Center) and enter your username
   (e.g. `acme.receptionist`) + password.
3. Sign in. You land on **Patient Registration**.

## 3. Getting around

Your sidebar shows:

| Section | What you can do there |
|---|---|
| **Front Desk** | Registration, Today's Schedule, Waiting Queue, Patient Search |
| **Coordination** | Orders, Care Plans, Communications |
| **Account** | Your profile and preferences |

You do **not** see the Acquisition (modality worklist/scheduling), Admin,
Billing, Reading, QA, Portal, or Files sections.

## 4. Surface-by-surface guide

### 4.1 Patient Registration (`/frontdesk/registration`)
- **Purpose:** search for and register patients, book visits.
- **How to:** search first to avoid duplicates; click **Register New Patient**
  and fill the form (name, optional MRN, DOB, sex, phone, email, room,
  address, emergency contact, portal consent). Click **Register & Open Visit**
  to create the patient + a visit, or use **Walk-in Book** to schedule.
- **Status:** PASS

### 4.2 Today's Schedule (`/frontdesk/schedule`)
- **Purpose:** all appointments across modalities, ordered by time.
- **How to:** pick a schedule date, filter by modality/status, refresh.
- **Status:** PASS

### 4.3 Waiting Queue (`/frontdesk/queue`)
- **Purpose:** the privacy-projected waiting queue.
- **Status:** PASS

### 4.4 Patient Search (sidebar action)
- **Purpose:** global patient search overlay.
- **Status:** PASS

### 4.5 Orders (`/orders`)
- **Purpose:** order list (for looking up patients' imaging orders during
  registration).
- **Status:** PASS (read-only)

### 4.6 Care Plans (`/care-plans`)
- **Purpose:** care plan board.
- **Status:** PASS (read-only)

### 4.7 Communications (`/communications`)
- **Purpose:** patient communication log.
- **Status:** PASS (read-only)

## 5. Common workflows (walkthroughs)

### 5.1 Register a new walk-in patient
1. Open **Patient Registration** (`/frontdesk/registration`).
2. Search the patient first to avoid duplicates.
3. Click **Register New Patient**, fill the form, click **Register & Open
   Visit**.

### 5.2 Check a patient in
1. Find the patient (search or queue).
2. Use the **Check-in** action to mark them arrived.

### 5.3 Book a walk-in appointment
1. From registration, click **Walk-in Book**.
2. Pick date/time/modality; the system detects capacity conflicts.

### 5.4 Monitor the waiting queue
1. Open **Waiting Queue** (`/frontdesk/queue`).
2. Review patient status; the queue is privacy-projected.

### 5.5 Look up a patient's orders
1. Open **Orders** (`/orders`).
2. Search by patient to see their imaging orders.

## 6. Permissions summary

You have:
- **Registration:** REGISTRATION_READ, REGISTRATION_WRITE
- **Patients:** PATIENT_READ, PATIENT_WRITE
- **Scheduling:** SCHEDULE_READ, SCHEDULE_WRITE
- **Queue:** QUEUE_READ
- **Orders/Worklist:** ORDER_READ, WORKLIST_READ

You **cannot**:
- Run the admin console, billing, QA, reading, portal, or metrics
- Access DICOMweb or Files
- Manage users, tenants, roles, or logs

## 7. Troubleshooting & known limits

- **No Acquisition section in the sidebar:** by design — the modality worklist /
  scheduling are the technologist's surfaces.
- **Portal consent checkbox:** only marks consent; the portal itself is
  patient-facing.
- **Elasticsearch offline:** patient search degrades gracefully.