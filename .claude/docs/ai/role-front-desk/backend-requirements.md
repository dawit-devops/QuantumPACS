# Backend Requirements: R08 Front Desk / Receptionist

## Context

The Front Desk receptionist performs patient registration, duplicate detection,
order intake, appointment scheduling, visit check-in, consent capture, and
insurance/guarantor capture. This is the **first point of patient contact** — a
search-first, forms-heavy workflow with hard PHI-minimum-necessary constraints on
waiting-area views.

**Screens (existing)**: none of the registration/scheduling screens exist today —
front-desk accounts currently have only the Files study browser + patient page in
read-only mode (see `existing-screens/` and the ground-truth
`role-presentation-layer.md`).

**Screens (new/planned — all GATED on a registration backend)**: Patient Search
(dedup), Registration Form, Scheduler, Check-In, Forms & Consent, Waiting Queue.

**Personas**: P8 (Front Desk). **Access tier**: registration + scheduling
(`PATIENT_READ`, `PATIENT_WRITE` exist; `SCHEDULE_*` proposed — not yet in
`permissions.py`).

## Screens/Components

### Patient Search & Duplicate Detection

**Purpose**: Find or confirm an existing patient before registering.

**Data I need to display**: matching patients by name, MRN, or DOB with a
deduplication warning banner; minimal identifiers (initials + MRN last 4) on
waiting-area views.

**Actions**: search (debounced, ≤500ms p95), select an existing patient, or
proceed to create a new one.

**States to handle**: loading, empty ("No matches — register new"), error with
retry, results with dedup warning.

**Business rules affecting UI**: dedup check must run **before** any new
registration is saved; search-first flow is mandatory.

### Registration Form

**Purpose**: Capture demographics, insurance, and order context.

**Data I need to display**: form fields (name, DOB, sex, MRN, contact, insurance,
guarantor); inline validation; outbound HL7 ADT sync status (async, non-blocking).

**Actions**: save new patient → trigger demographics sync (R16 EMR via HL7 ADT),
continue to scheduling.

**States to handle**: idle, saving (optimistic), success banner + label print,
inline field errors, offline queue + sync ≤2min after reconnect.

### Scheduler

**Purpose**: Book a modality time slot.

**Data I need**: modality time slots, scheduling conflicts (patient, modality,
technologist), room/station.

**Actions**: pick a slot, see conflicts before confirming, book.

**Business rules affecting UI**: shares the schedule-board data model with R04
(single source of truth); feeds R06/R07 modality worklist.

### Check-In / Consent / Queue

**Purpose**: Mark arrival, attach consent forms, show waiting-room status.

**Data I need**: visit status (registered → checked-in → in-progress →
complete), attached consent forms + missing-consent flags, queue rows with
destination.

**Actions**: check in, upload signed forms, print armbands/requisition labels.

**Business rules affecting UI**: waiting-area views show initials + MRN last 4
only (HIPAA §164.514(d)); consent forms retained and audited (R01/R02).

## Uncertainties

- [ ] **Entire registration/scheduling module is GATED** — no endpoints exist
  (no patient-create API, no visit/order model, no schedule board). Must be
  raised with backend before sprint commitment.
- [ ] Does a dedicated patient-create endpoint exist, or is patient upsert
  currently only driven by HL7 ADT (R16)?
- [ ] Is scheduling a new module, or does it reuse the worklist
  (`/worklist*`) with additional scheduling fields?
- [ ] Consent storage: where are uploaded forms kept (file storage vs.
  attachments to a visit record)?
- [ ] Outbound HL7 ADT for registration — confirmed to be async and
  non-blocking?

## Questions for Backend

- What is the roadmap for registration/scheduling endpoints? Everything for R08
  depends on it.
- Is the queue/check-in status derived from worklist entries (shared with R04)
  or a separate visit-state model?
- Does label/armband printing need a dedicated endpoint, or is it a pure client
  print of already-fetched data?

## Discussion Log

_(pending backend review)_
