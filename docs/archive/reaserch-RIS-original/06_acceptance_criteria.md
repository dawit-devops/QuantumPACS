# RIS — Acceptance Criteria

**Document:** 06 of 06 · **Version:** 1.0 · **Date:** 2026-08-04

Testable acceptance criteria per user story (`03_user_stories.md`). Format: Given / When / Then. Used for UAT scripts and automated assertions.

---

## RIS-P01 · Radiologist

### RIS-AC-P01-01 — Priority-sorted reading worklist (→ RIS-US-P01-01)
- **GIVEN** a worklist with mixed priorities **WHEN** opened **THEN** STAT > inpatient > outpatient order by study date desc, and filters (modality/site/status/date) work with server-side pagination.
- **GIVEN** a worklist filter set **WHEN** the user navigates away and back **THEN** filters persist.

### RIS-AC-P01-02 — Structured templates + speech recognition (→ RIS-US-P01-02)
- **GIVEN** an exam type **WHEN** a new report starts **THEN** the correct template loads with required sections marked.
- **GIVEN** dictation **WHEN** transcribed **THEN** text fills the active field and uncertain words are highlighted for verification; no text is lost.

### RIS-AC-P01-03 — Critical-results flagging (→ RIS-US-P01-03)
- **GIVEN** an urgent finding **WHEN** the radiologist flags it **THEN** a documented notification is created with recipient, timestamp, and acknowledgment tracking; unacknowledged escalates per policy; all events audited.
- **GIVEN** a critical flag **WHEN** the report is signed **THEN** the flag is carried into the ORU/FHIR payload.

### RIS-AC-P01-04 — Sign & auto-distribute (→ RIS-US-P01-04)
- **GIVEN** a completed report **WHEN** signed **THEN** it is delivered to the EMR (ORU/FHIR) within 5 min and a billing record is created; distribution status visible; no manual forwarding needed.

### RIS-AC-P01-05 — Viewer launch in context (→ RIS-US-P01-05)
- **GIVEN** a worklist row **WHEN** the user clicks it **THEN** the PACS viewer opens on that study (deep link) and returning to RIS preserves worklist state.

### RIS-AC-P01-06 — Draft preservation (→ RIS-US-P01-06)
- **GIVEN** an unfinished report **WHEN** the session ends or the device changes **THEN** the draft is restored; no duplicate report is created.

## RIS-P02 · Technologist

### RIS-AC-P02-01 — MWL auto-population (→ RIS-US-P02-01)
- **GIVEN** a scheduled order **WHEN** the modality queries MWL **THEN** patient/accession/requested procedure return and auto-fill (≥ 98% of exams, RIS-SL-33); empty queries return a clear empty result.

### RIS-AC-P02-02 — Live tracking from MPPS (→ RIS-US-P02-02)
- **GIVEN** MPPS IN PROGRESS/COMPLETED/DISCONTINUED **WHEN** received **THEN** the tracking board updates within 5 s (RIS-SL-22) and status echoes to PACS; mismatched MPPS goes to the exception queue.

### RIS-AC-P02-03 — Add-ons & re-schedules (→ RIS-US-P02-03)
- **GIVEN** an add-on exam **WHEN** added **THEN** it inherits order context (patient/accession/procedure) and appears on MWL without re-entry; re-schedules preserve the order and audit the change.

## RIS-P03 · Scheduler

### RIS-AC-P03-01 — Conflict-free booking (→ RIS-US-P03-01)
- **GIVEN** a booking attempt **WHEN** a room/technologist/contrast conflict exists **THEN** the system blocks it with an explanatory message; valid bookings save and are visible to the modality worklist.
- **GIVEN** a contraindication (e.g., contrast allergy, renal impairment) **WHEN** detected **THEN** an inline warning appears; proceeding requires an audited override.

### RIS-AC-P03-02 — Reminders (→ RIS-US-P03-02)
- **GIVEN** a scheduled appointment **WHEN** reminder config is active **THEN** reminders send on the chosen channels/times; opt-out is honored; send success/failure logged.

### RIS-AC-P03-03 — Prior-auth tracking (→ RIS-US-P03-03)
- **GIVEN** an order requiring prior authorization **WHEN** authorization is missing/expired/denied **THEN** the order is flagged and booking is blocked (with audited override); approved auth links to the order and claim.
- **GIVEN** an expiring authorization **WHEN** ≤ 7 days remain **THEN** the scheduler is alerted.

### RIS-AC-P03-04 — Enterprise multi-site scheduling (→ RIS-US-P03-04)
- **GIVEN** an IDN tenant **WHEN** the scheduler searches availability **THEN** results span all sites with shared resource visibility; booking records the site; site chargeback data is captured.

### RIS-AC-P03-05 — Day view (→ RIS-US-P03-05)
- **GIVEN** the calendar/list day view **WHEN** opened **THEN** status colors, room/technologist assignments, and priority badges render; actions respect status guards.

## RIS-P04 · Front Desk

### RIS-AC-P04-01 — Registration with MPI dedup (→ RIS-US-P04-01)
- **GIVEN** a new registration **WHEN** demographics are entered **THEN** MPI probable-match warnings appear with review/merge links; saving creates a clean record with insurance captured.
- **GIVEN** an existing patient **WHEN** re-registered **THEN** the existing record is reused (no duplicate MRN), per RIS-SL-37.

### RIS-AC-P04-02 — Insurance eligibility (→ RIS-US-P04-02)
- **GIVEN** an eligibility check **WHEN** run **THEN** the status (active/inactive/needs verification) displays inline before check-in completes.

### RIS-AC-P04-03 — One-click check-in (→ RIS-US-P04-03)
- **GIVEN** the day's schedule **WHEN** the clerk checks a patient in **THEN** status becomes Arrived, labels/consents are produced, and the tracking board updates.

## RIS-P05 · Billing Coder

### RIS-AC-P05-01 — CPT/ICD-10 suggestion (→ RIS-US-P05-01)
- **GIVEN** a signed exam **WHEN** the coder opens the billing queue **THEN** CPT/ICD-10 suggestions from procedure + report render with coder confirmation/adjustment; coding accuracy ≥ 95% first pass (RIS-SL-43).

### RIS-AC-P05-02 — Denial rework queue (→ RIS-US-P05-02)
- **GIVEN** a denied claim **WHEN** received **THEN** it appears in the rework queue with reason code, correction workflow, and resubmission; history is preserved.

### RIS-AC-P05-03 — Auto charge drop (→ RIS-US-P05-03)
- **GIVEN** a signed report **WHEN** finalized **THEN** a billable record is created automatically (charge capture ≥ 98%, RIS-SL-40) and appears in the billing queue; nothing billable is missed (reconciled daily).

## RIS-P06 · RIS Administrator

### RIS-AC-P06-01 — Accession uniqueness (→ RIS-US-P06-01)
- **GIVEN** an order entry **WHEN** an accession already exists for the tenant **THEN** insertion is rejected with a clear error; duplicates never occur (unique index per `worklist_design.md`).

### RIS-AC-P06-02 — Interface health & exception queue (→ RIS-US-P06-02)
- **GIVEN** an interface failure **WHEN** it occurs **THEN** an alert fires within 5 min; the dashboard shows the fault; failed messages land in the exception queue with retry/reconcile; > 99.9% delivery baseline (RIS-SL-23).

### RIS-AC-P06-03 — Configurable templates & maps (→ RIS-US-P06-03)
- **GIVEN** template/map changes **WHEN** published **THEN** they are versioned and apply to target sites; rollback is one click; validation prevents duplicates.

### RIS-AC-P06-04 — MPI maintenance (→ RIS-US-P06-04)
- **GIVEN** duplicate candidates **WHEN** the admin merges **THEN** a merge wizard runs with undo and a full audit trail; downstream records update consistently.

## RIS-P07 · Manager · RIS-P08/09 · Referring/ED

### RIS-AC-P07-01 — Dashboards (→ RIS-US-P07-01)
- **GIVEN** the manager dashboard **WHEN** a period is selected **THEN** patient flow, utilization, TAT by priority, and unbilled metrics aggregate correctly and export matches on-screen data.

### RIS-AC-P08-01 — Order from EMR with status (→ RIS-US-P08-01)
- **GIVEN** an EMR order (ORM/FHIR) **WHEN** received **THEN** the order appears in RIS with accession and status, and the referring physician sees real-time status; accessible for scheduling < 1 min (RIS-SL-20).

### RIS-AC-P08-02 — Report delivery to EMR (→ RIS-US-P08-02)
- **GIVEN** a signed report **WHEN** finalized **THEN** it is delivered to the EMR inbox within 5 min (RIS-SL-24) and visible to the ordering physician.

### RIS-AC-P09-01 — STAT end-to-end prioritization (→ RIS-US-P09-01)
- **GIVEN** a STAT order **WHEN** it enters the pipeline **THEN** it is prioritized in scheduling, MWL, acquisition, and reading queues; the ED sees priority status throughout.

### RIS-AC-P09-02 — Immediate critical alerts (→ RIS-US-P09-02)
- **GIVEN** a critical result **WHEN** flagged **THEN** the ED physician is notified immediately and acknowledgment is tracked; notification events audited.

## RIS-P19 · Tenant Admin · RIS-P20 · Super Admin

### RIS-AC-P19-01 — Tenant configuration (→ RIS-US-P19-01)
- **GIVEN** a tenant admin **WHEN** configuring sites, rooms, schedules, and roles **THEN** changes are versioned, audited, and immediately effective for that tenant only.

### RIS-AC-P19-02 — Usage & billing visibility (→ RIS-US-P19-02)
- **GIVEN** the tenant admin console **WHEN** opened **THEN** metered usage (MWL queries, API calls, notifications) and invoices render with drill-down; export matches metering data (RIS-SL-50).

### RIS-AC-P20-01 — Atomic provisioning (→ RIS-US-P20-01)
- **GIVEN** a new tenant signup **WHEN** provisioning runs **THEN** it completes atomically (facility + TRIAL + seed + RLS scope) to READY < 15 min; failure rolls back with no partial tenant.

### RIS-AC-P20-02 — Audited cross-tenant workflows (→ RIS-US-P20-02)
- **GIVEN** an IDN/teleradiology cross-tenant operation **WHEN** performed **THEN** it requires an explicit policy grant and is audit-logged with source/target facility; unauthorized attempts are denied and logged.

---

## Traceability matrix

| Story group | Acceptance |
| :--- | :--- |
| RIS-US-P01-01…06 | RIS-AC-P01-01…06 |
| RIS-US-P02-01…03 | RIS-AC-P02-01…03 |
| RIS-US-P03-01…05 | RIS-AC-P03-01…05 |
| RIS-US-P04-01…03 | RIS-AC-P04-01…03 |
| RIS-US-P05-01…03 | RIS-AC-P05-01…03 |
| RIS-US-P06-01…04 | RIS-AC-P06-01…04 |
| RIS-US-P07/08/09/19/20 | RIS-AC-P07…P20 |
