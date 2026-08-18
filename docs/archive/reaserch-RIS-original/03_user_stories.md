# RIS — User Stories

**Document:** 03 of 06 · **Version:** 1.0 · **Date:** 2026-08-04

Syntax (EARS): `As a <persona>, I want <capability>, so that <benefit>.` Priorities: M/D/O. Each story maps to ≥1 acceptance criterion and ≥1 workflow.

---

## RIS-P01 · Radiologist

| ID | Story | Pri | WF | AC |
| :--- | :--- | :-: | :-: | :-: |
| RIS-US-P01-01 | As a radiologist, I want a priority-sorted reading worklist (STAT > inpatient > outpatient) with filters for modality, site, and status, so that I read the most urgent studies first. | M | WF4 | RIS-AC-P01-01 |
| RIS-US-P01-02 | As a radiologist, I want structured report templates with speech-recognition integration, so that reports are complete, consistent, and fast to produce. | M | WF4 | RIS-AC-P01-02 |
| RIS-US-P01-03 | As a radiologist, I want one-action critical-results flagging with tracked notification and escalation, so that urgent findings are acted on and documented for HIPAA. | M | WF4 | RIS-AC-P01-03 |
| RIS-US-P01-04 | As a radiologist, I want to sign a report and have it distributed automatically to the EMR and billing, so that results and charges flow without manual steps. | M | WF4, WF6 | RIS-AC-P01-04 |
| RIS-US-P01-05 | As a radiologist, I want to launch the PACS viewer from the worklist with study context, so that I read without re-searching for the study. | M | WF4 | RIS-AC-P01-05 |
| RIS-US-P01-06 | As a radiologist, I want my draft reports preserved across sessions/devices, so that interrupted work is never lost. | D | WF4 | RIS-AC-P01-06 |

## RIS-P02 · Technologist

| ID | Story | Pri | WF | AC |
| :--- | :--- | :-: | :-: | :-: |
| RIS-US-P02-01 | As a technologist, I want the modality worklist populated automatically from scheduled orders, so that I never re-type patient data at the console. | M | WF1 | RIS-AC-P02-01 |
| RIS-US-P02-02 | As a technologist, I want my MPPS updates (in-progress/completed/discontinued) to drive the tracking board live, so that statuses are accurate without manual entry. | M | WF1 | RIS-AC-P02-02 |
| RIS-US-P02-03 | As a technologist, I want to handle add-on exams and re-schedules without losing the order context, so that the flow continues smoothly. | D | WF1 | RIS-AC-P02-03 |

## RIS-P03 · Scheduler / Referral Coordinator

| ID | Story | Pri | WF | AC |
| :--- | :--- | :-: | :-: | :-: |
| RIS-US-P03-01 | As a scheduler, I want conflict-free multi-modality/multi-site booking with room, technologist, and contrast checks, so that double-bookings never happen. | M | WF1 | RIS-AC-P03-01 |
| RIS-US-P03-02 | As a scheduler, I want automated appointment reminders (SMS/email/phone) with opt-out, so that no-shows decrease. | D | WF1 | RIS-AC-P03-02 |
| RIS-US-P03-03 | As a scheduler, I want prior-authorization tracking with expiry alerts and blocked booking when denied, so that exams are authorized before they happen. | D | WF3 | RIS-AC-P03-03 |
| RIS-US-P03-04 | As a scheduler in a health system, I want enterprise scheduling across sites with a shared resource pool, so that patients get the earliest available slot at the best site. | D | WF7 | RIS-AC-P03-04 |
| RIS-US-P03-05 | As a scheduler, I want a calendar and list view of the day's schedule with status colors, so that I can manage the day at a glance. | M | WF1 | RIS-AC-P03-05 |

## RIS-P04 · Front-Desk / Registration Clerk

| ID | Story | Pri | WF | AC |
| :--- | :--- | :-: | :-: | :-: |
| RIS-US-P04-01 | As a front-desk clerk, I want to register/check-in a patient with demographics and insurance capture plus MPI duplicate checks, so that records and claims are clean from the start. | M | WF2 | RIS-AC-P04-01 |
| RIS-US-P04-02 | As a front-desk clerk, I want insurance eligibility verification at check-in, so that coverage surprises surface before the exam. | D | WF2 | RIS-AC-P04-02 |
| RIS-US-P04-03 | As a front-desk clerk, I want one-click check-in from the day's schedule with arrival status, so that the tracking board stays accurate. | M | WF2 | RIS-AC-P04-03 |

## RIS-P05 · Radiology Billing Coder

| ID | Story | Pri | WF | AC |
| :--- | :--- | :-: | :-: | :-: |
| RIS-US-P05-01 | As a billing coder, I want CPT/ICD-10 automatically suggested from the ordered procedure and signed report, so that coding is fast and accurate. | M | WF6 | RIS-AC-P05-01 |
| RIS-US-P05-02 | As a billing coder, I want an unbilled/denial rework queue with reason codes and resubmission, so that revenue leakage is minimized. | M | WF6 | RIS-AC-P05-02 |
| RIS-US-P05-03 | As a billing coder, I want charge drop to occur automatically when the radiologist signs the report, so that nothing billable is missed. | M | WF6 | RIS-AC-P05-03 |

## RIS-P06 · RIS Administrator

| ID | Story | Pri | WF | AC |
| :--- | :--- | :-: | :-: | :-: |
| RIS-US-P06-01 | As a RIS administrator, I want accession numbers enforced as unique per tenant, so that orders never collide. | M | WF1 | RIS-AC-P06-01 |
| RIS-US-P06-02 | As a RIS administrator, I want interface health dashboards (HL7/MPPS/MWL) with ≤5-min alerting and an exception queue, so that message failures never go unnoticed. | M | WF8 | RIS-AC-P06-02 |
| RIS-US-P06-03 | As a RIS administrator, I want configurable scheduling templates, procedure/CPT maps, and report templates, so that new sites go live consistently. | D | WF9 | RIS-AC-P06-03 |
| RIS-US-P06-04 | As a RIS administrator, I want MPI maintenance tools (duplicate review/merge), so that patient records stay unified. | D | WF2 | RIS-AC-P06-04 |

## RIS-P07 · Department Manager

| ID | Story | Pri | WF | AC |
| :--- | :--- | :-: | :-: | :-: |
| RIS-US-P07-01 | As a department manager, I want patient-flow, utilization, and TAT dashboards with drill-down and export, so that I can manage SLAs and staffing. | M | WF4 | RIS-AC-P07-01 |

## RIS-P08 · Referring Physician

| ID | Story | Pri | WF | AC |
| :--- | :--- | :-: | :-: | :-: |
| RIS-US-P08-01 | As a referring physician, I want to place imaging orders from my EMR and see order status in real time, so that I know where my patients' exams stand. | M | WF1 | RIS-AC-P08-01 |
| RIS-US-P08-02 | As a referring physician, I want finalized reports delivered to my EMR inbox automatically, so that I act on results without logging into another system. | M | WF5 | RIS-AC-P08-02 |

## RIS-P09 · ED Physician

| ID | Story | Pri | WF | AC |
| :--- | :--- | :-: | :-: | :-: |
| RIS-US-P09-01 | As an ED physician, I want STAT orders flagged and prioritized end-to-end (schedule → acquisition → read), so that acute patients get answers fast. | M | WF1, WF4 | RIS-AC-P09-01 |
| RIS-US-P09-02 | As an ED physician, I want critical-result alerts delivered immediately with acknowledgment, so that urgent findings reach me without delay. | M | WF4 | RIS-AC-P09-02 |

## RIS-P19 · Tenant Admin · RIS-P20 · Super Admin

| ID | Story | Pri | WF | AC |
| :--- | :--- | :-: | :-: | :-: |
| RIS-US-P19-01 | As a tenant admin, I want to configure sites, rooms, schedules, and user roles, so that my facility reflects its operational structure. | M | WF9 | RIS-AC-P19-01 |
| RIS-US-P19-02 | As a tenant admin, I want usage and billing visibility, so that I can manage costs. | M | — | RIS-AC-P19-02 |
| RIS-US-P20-01 | As a super admin, I want atomic tenant provisioning with rollback, so that no tenant is left half-configured. | M | WF9 | RIS-AC-P20-01 |
| RIS-US-P20-02 | As a super admin, I want cross-tenant workflows (IDN scheduling, teleradiology reading) policy-gated and audited, so that no data crosses tenant boundaries accidentally. | M | WF7 | RIS-AC-P20-02 |

---

## Story counts by priority

| System | M | D | O | Total |
| :--- | :-: | :-: | :-: | :-: |
| RIS | 25 | 8 | 0 | 33 |
