# User Requirements — Front Desk / Receptionist (R08)

**Version**: 1.0.0 (v3.0 scope)
**Status**: Draft
**Date**: 2026-08-02

## Functional Requirements

| ID | Requirement | Priority | Notes |
|----|-------------|----------|-------|
| FR-R08-01 | **Patient Search & Duplicate Detection**: Search for an existing patient by name, MRN, or date of birth before registration. When matches are found, show them with a dedup warning so the receptionist avoids creating a duplicate record. | Must | Reuses patient lookup; dedup is a hard safety requirement |
| FR-R08-02 | **Patient Registration**: Capture demographics (name, DOB, sex, MRN, contact details, insurance). Validate required fields inline. New patients create a patient record and trigger demographics sync to connected systems. | Must | Registration screen; sync via HL7 ADT (R16) |
| FR-R08-03 | **Order Intake**: Capture a referring physician order: requested procedure, indication, urgency (STAT/urgent/routine), referring physician. Support manual entry and scanning of a paper order. | Must | Links order to patient + visit |
| FR-R08-04 | **Appointment Scheduling**: Schedule the patient into a modality time slot with date, time, and room/station. Show scheduling conflicts (patient, modality, technologist) before confirming. | Must | Feeds R04 schedule board + R06/R07 worklist |
| FR-R08-05 | **Visit Check-In**: Mark a patient as arrived/checked-in on the day of service. Verify demographics at check-in and capture corrections. | Must | Updates visit status visible to R11/R06/R07 |
| FR-R08-06 | **Consent & Forms Capture**: Attach signed consent forms and screening questionnaires to the visit (uploaded scan or digital signature). List attached forms and flag missing required consents. | Must | HIPAA consent handling |
| FR-R08-07 | **Insurance & Guarantor Capture**: Record insurance policy and guarantor information, authorization status, and notes. Flag missing authorization for scheduled services. | Should | Needed by R09 cashier |
| FR-R08-08 | **Label & Document Printing**: Print patient armbands and requisition/label documents with patient identifiers (name, MRN, DOB, accession). | Should | Print via browser/PWA |
| FR-R08-09 | **Patient Queue & Status Board**: Display the current waiting room / in-progress queue with status (registered, checked-in, in-progress, complete) and destination (modality room). | Should | Privacy-limited view (initials) |
| FR-R08-10 | **PHI Minimum Necessary**: All waiting-area/queue views must show only minimal identifiers (initials + MRN last 4); full PHI only in an authenticated detail view. | Must | HIPAA §164.514(d) |

## Non-Functional Requirements

| ID | Requirement | Target | Measurement |
|----|-------------|--------|-------------|
| NFR-R08-01 | Registration/search screens load time | LCP ≤ 2.5s, INP ≤ 200ms | Lighthouse CI, RUM |
| NFR-R08-02 | Patient search latency (server round-trip) | ≤ 500ms p95 | Synthetic probe |
| NFR-R08-03 | Registration form save latency | ≤ 500ms optimistic update | Backend timing |
| NFR-R08-04 | Offline tolerance for registration forms | Queue submissions, sync ≤ 2min after reconnect | Synthetic offline test |
| NFR-R08-05 | Form submit success/error feedback | Every submit shows explicit success or inline error | Automated E2E |
| NFR-R08-06 | WCAG 2.2 AA compliance | 100% (keyboard + screen-reader usable) | axe-core CI + manual |

## Codebase Status (verified 2026-08-03)

**GATED**: All FR-R08-NN registration/scheduling requirements are aspirational v3.0
— no registration, scheduling, check-in, consent, or queue routes/endpoints exist.
Front-desk accounts today have only Files/patient read-only views. Requires new
backend registration module + permissions flagged to backend. See artifacts 04/07/08.

## Assumptions & Constraints

- A1: Registration triggers an outbound HL7 ADT message (R16 EMR) — async, non-blocking.
- A2: Scheduling shares the schedule board data model with R04 (single source of truth).
- A3: The front desk does not perform billing (R09), clinical reading (R12), or acquisition (R06/R07).
- A4: Waiting-area displays must not expose full PHI (initials only).
- A5: Patient search and dedup must run before any new registration is saved.
