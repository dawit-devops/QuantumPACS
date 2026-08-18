# RIS — Persona Catalog: Real-World Users, Institutions & Machines

**Document:** 01 of 06 · **Version:** 1.0 · **Date:** 2026-08-04

Proposed real-world users and personas for the RIS product surface, grouped into **human users** (RIS-P##), **institutions** (RIS-I##), and **machines/systems** (RIS-M##).

---

## 1. Human Users (RIS-P##)

### RIS-P01 · Radiologist (reporting & worklist)

| Attribute | Description |
| :--- | :--- |
| **Real-world identity** | Staff/subspecialty radiologist using RIS to manage reads, report, and communicate results |
| **Primary goals** | Efficient prioritized reading; fast accurate reporting; critical-results communication; low TAT |
| **Key tasks** | Review prioritized reading worklist; open studies (via PACS link); dictate/type structured report; flag critical findings; sign; route results |
| **Pain points** | Unprioritized worklists, template friction, speech-recognition errors, no critical-alert tracking, report distribution delays |
| **Success metrics** | TAT by priority; reads/day; critical-alert acknowledgment time |
| **Permissions** | Worklist read/prioritize · report author/sign · critical flag · results distribution |

### RIS-P02 · Radiology Technologist

| Attribute | Description |
| :--- | :--- |
| **Real-world identity** | CT/MR/XR/US/NM/mammo technologist working at the scanner and tracking board |
| **Primary goals** | Smooth exam flow: MWL auto-fill, MPPS updates, minimal rework |
| **Key tasks** | Query MWL; verify patient; perform exam; update status via MPPS; document contrast/dose; handle add-ons |
| **Pain points** | MWL not populated, wrong accession, MPPS mismatch, status board not live |
| **Success metrics** | % MWL auto-fill; exam-to-complete time; rework rate |
| **Permissions** | Worklist read · perform exam (MPPS) · view tracking board |

### RIS-P03 · Scheduler / Referral Coordinator

| Attribute | Description |
| :--- | :--- |
| **Real-world identity** | Imaging scheduler booking exams across modalities, sites, and staff |
| **Primary goals** | Book the right slot with the right prep/contrast, no conflicts, high utilization |
| **Key tasks** | Multi-modality/site booking; resource matching (room, technologist, contrast room); conflict/rule checks; prior-auth tracking; reminders; rescheduling/cancellations |
| **Pain points** | Double-booking, missing pre-certs, complex prep rules, last-minute cancellations, no reminder automation |
| **Success metrics** | Booking accuracy; scheduling conflicts = 0; utilization; no-show reduction |
| **Permissions** | Scheduling CRUD · prior-auth view · reminder management |

### RIS-P04 · Front-Desk / Registration Clerk

| Attribute | Description |
| :--- | :--- |
| **Real-world identity** | Receptionist/registrar checking patients in at imaging departments |
| **Primary goals** | Accurate demographics/insurance; fast check-in; clean downstream records & claims |
| **Key tasks** | Register/pre-register patients; verify ID/insurance; MPI dedup checks; collect consents; check-in arrivals |
| **Pain points** | Duplicate MRNs, unverified insurance, long queues, paper consent |
| **Success metrics** | Registration accuracy; duplicate-record rate; check-in time |
| **Permissions** | Patient registration · insurance capture · check-in |

### RIS-P05 · Radiology Billing Coder

| Attribute | Description |
| :--- | :--- |
| **Real-world identity** | Radiology biller/coder translating completed exams into clean claims |
| **Primary goals** | Capture every billable exam accurately; minimize denials; speed charge drop |
| **Key tasks** | Review signed reports; match CPT/ICD-10; reconcile unbilled log; fix rejections; prior-auth linkage |
| **Pain points** | Incomplete docs, mismatched codes, unbilled backlog, denial rework |
| **Success metrics** | Charge capture rate; denial rate; unbilled aging |
| **Permissions** | Billing workspace · claim view · unbilled reconciliation |

### RIS-P06 · RIS Administrator

| Attribute | Description |
| :--- | :--- |
| **Real-world identity** | RIS admin managing schedules, code maps, interfaces, and user access |
| **Primary goals** | Keep the RIS configured & flowing; keep interfaces healthy; support users |
| **Key tasks** | Maintain scheduling templates; procedure/CPT/ICD maps; interface monitoring (HL7); MPI maintenance; user roles; report templates |
| **Pain points** | Interface message failures, HIS/RIS demographic mismatches, template sprawl |
| **Success metrics** | Interface health; config change lead time; % template reuse |
| **Permissions** | Admin: codes, templates, interfaces, users, audit |

### RIS-P07 · Department Manager / Radiology Director

| Attribute | Description |
| :--- | :--- |
| **Real-world identity** | Manager tracking department performance |
| **Primary goals** | Monitor patient flow, modality utilization, TAT, staff productivity; meet SLAs |
| **Key tasks** | Review dashboards; drill into outliers; export reports; drive improvements |
| **Pain points** | No live data, no drill-down, manual reporting |
| **Success metrics** | KPI accuracy; SLA attainment; dashboard adoption |
| **Permissions** | Department analytics (read) · exports |

### RIS-P08 · Referring / Ordering Physician · RIS-P09 · ED Physician

| Attribute | Description |
| :--- | :--- |
| **Real-world identity** | Ordering provider wanting order status & results |
| **Primary goals** | Place orders (via EMR), track status, receive results promptly |
| **Key tasks** | View order status; receive critical alerts; get final reports in EMR |
| **Pain points** | Unknown order status, delayed results, missed critical alerts |
| **Success metrics** | Result delivery time; critical acknowledgment time |
| **Permissions** | Order status view (EMR-scoped) · result receipt |

### RIS-P19 · Tenant Admin · RIS-P20 · Super Admin

| Attribute | Description |
| :--- | :--- |
| **Real-world identity** | Facility IT lead / platform operator |
| **Primary goals** | Configure tenant (sites, rooms, schedules, users, quotas); run the SaaS (provision, meter, bill, support) |
| **Key tasks** | User/role management; site & resource setup; usage/billing visibility; platform provisioning & lifecycle |
| **Success metrics** | Time-to-provision; billing accuracy; uptime |
| **Permissions** | Tenant-scoped admin / platform-scoped (audited `BYPASSRLS`) |

---

## 2. Institutions (RIS-I##)

| ID | Institution | RIS-relevant needs |
| :-: | :--- | :--- |
| RIS-I01 | **Acute-care hospital** | 24/7 scheduling, ED STAT, inpatient transport coordination, high-volume tracking |
| RIS-I02 | **Freestanding imaging center** | High-throughput scheduling, minimal staff, strong patient experience, reminders |
| RIS-I03 | **Teleradiology group** | Cross-facility reading workload, report routing to multiple tenants |
| RIS-I04 | **Integrated Delivery Network** | Enterprise scheduling across sites, shared resources, consolidated analytics & chargeback |
| RIS-I05 | **Outpatient clinic** | Ordering site: place imaging orders, track status, receive results |
| RIS-I06 | **Payer / insurer** | Prior authorization (external), claims adjudication inputs |

---

## 3. Machines & Systems (RIS-M##) — Integration Actors

| ID | Machine actor | Role in RIS | Protocols | Key requirements |
| :-: | :--- | :--- | :--- | :--- |
| RIS-M01 | **Imaging modalities** | Consume MWL; report status | DICOM C-FIND (MWL), N-CREATE/N-SET (MPPS) | MWL entries served when scheduled; MPPS accepted & echoed to PACS; no manual re-entry |
| RIS-M02 | **HIS/EMR** | Orders, demographics, results consumption | HL7 v2 ADT/ORM/ORU; FHIR R4 ServiceRequest/DiagnosticReport | Order intake (ORM→order), demographic sync (ADT), result delivery (ORU); patient merges honored |
| RIS-M03 | **PACS** | Study status & retrieval context | HL7 ORU, DICOM, DICOMweb | Receives MPPS echo; provides viewer launch context for reporting |
| RIS-M04 | **Billing / PM & clearinghouses** | Charge & claim exchange | HL7, X12 837/835 | Charge drop after sign-off; claim rejections returned for rework; prior-auth status |
| RIS-M05 | **Patient portal / SMS/email** | Reminders & results delivery | HTTPS, FHIR, SMS/email providers | Appointment reminders; result availability notifications; opt-out honored |
| RIS-M06 | **Speech-recognition / dictation engine** | Report authoring | WebSocket/API | Dictation into structured templates; transcription verification loop; FHIR DocumentReference |

---

## 4. Permission Mapping (RBAC skeleton for RIS)

| Capability | Radiologist | Technologist | Scheduler | Front Desk | Billing | RIS Admin | Tenant Admin | Super Admin |
| :--- | :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: |
| Patient registration | — | — | — | ✓ | — | ✓ | — | ✓ |
| Scheduling CRUD | — | — | ✓ | — | — | ✓ | ✓ | ✓ |
| Worklist read/prioritize | ✓ | ✓ | — | — | — | ✓ | — | — |
| Perform exam (MPPS) | — | ✓ | — | — | — | — | — | — |
| Report author/sign | ✓ | — | — | — | — | — | — | — |
| Critical-results alert | ✓ | ✓ | — | — | — | — | — | — |
| Billing workspace | — | — | — | — | ✓ | ✓ | — | — |
| Procedure/CPT maps | — | — | — | — | ✓ | ✓ | — | ✓ |
| Interface/admin config | — | — | — | — | — | ✓ | ✓ | ✓ |
| Audit log view | — | — | — | — | — | ✓ (tenant) | ✓ (tenant) | ✓ (all) |

> All rows scoped by `facility_id` (RLS). Cross-facility scheduling/reading in an IDN is a deliberate audited policy.
>
> **Read-only personas** (referring MD RIS-P08, ED MD RIS-P09) are view-only: order status, results, and critical alerts — no write, scheduling, or billing capabilities.
