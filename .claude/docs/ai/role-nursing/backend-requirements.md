# Backend Requirements: R11 Radiology Service Nursing Team

## Context

The Nursing team provides patient care during exams: patient prep, vitals
capture, contrast administration, allergy/safety verification, adverse-reaction
response, sedation monitoring, post-procedure recovery/discharge, MAR, and
handoff notes. This is a **bedside, tablet-friendly, offline-tolerant** role fed
by R08 check-in and R06/R07 exam status. No nursing module exists in the
codebase — fully GATED.

**Screens (existing)**: none — nursing accounts currently have only the Files
study browser + patient page in read-only mode.

**Screens (new/planned — all GATED on a nursing backend)**: Nursing Worklist,
Patient Prep Checklist, Vitals Capture, Contrast Administration Record, Allergy
& Safety Verification, Adverse Reaction Log, Sedation Monitoring, Recovery &
Discharge, MAR, Handoff Notes.

**Personas**: P11 (Nursing Team). **Access tier**: nursing read/write
(`PATIENT_READ`, proposed `NURSING_*`).

## Screens/Components

### Nursing Worklist

**Purpose**: See patients needing nursing care with status.

**Data I need to display**: patient status (waiting / in prep / in procedure /
recovery / discharged), destination; auto-refresh from check-in and exam status
(≤5s staleness).

**Actions**: open a patient, transition status.

**States to handle**: empty, loading, error, live-update rows.

**Business rules affecting UI**: worklist feeds from R08 check-in + R06/R07 exam
status — needs a shared status event stream (WebSocket LISTEN/NOTIFY pattern).

### Prep Checklist / Vitals / Contrast / Safety

**Purpose**: Structured bedside documentation before and during exams.

**Data I need**: per-procedure prep checklist (fasting, labs, consent), vitals
(BP, HR, SpO2, temperature, respiration) with timestamp + operator, contrast
records (agent, dose, route, rate, time), allergy/pregnancy/renal screening
(from HL7 ADT flags + nurse confirmation).

**Actions**: item-by-item checklist confirmation, repeated vital readings,
record contrast administration (requires prior safety verification), confirm
allergy screen.

**States to handle**: idle, saving (optimistic ≤500ms), offline queue + sync
≤2min, warning states (allergy flag, pregnancy).

### Adverse Reaction / Sedation / Recovery / MAR / Handoff

**Purpose**: Post-procedure care and escalation.

**Data I need**: adverse-reaction records (type, severity, onset, actions),
sedation doses + monitoring intervals, recovery observations + discharge
criteria, MAR entries (medication, dose, route, time, indication), structured
handoff notes.

**Actions**: log adverse reaction → escalation to on-call radiologist (R12/R18)
≤15min, record recovery, print discharge instructions, add MAR entries.

**Business rules affecting UI**: contrast administration requires prior
allergy/safety verification (FR-R11-05); vitals/MAR support tablet entry with
offline tolerance; all documentation audited (who, what, when).

## Uncertainties

- [ ] **Entire nursing module is GATED** — no nursing, vitals, contrast, MAR,
  or escalation endpoints exist. Must be raised with backend.
- [ ] How is the "on-call radiologist" routed for adverse-reaction escalation —
  does the notification system support a priority/on-call destination?
- [ ] Are allergy/pregnancy flags reliably available via HL7 ADT (R16), or do
  nurses need manual entry fallback?
- [ ] Vitals/offline: is there a queue-and-sync contract for bedside tablets?
- [ ] Permission slugs (`NURSING_*`) proposed but not in `permissions.py`.

## Questions for Backend

- What is the roadmap for nursing endpoints (worklist, vitals, prep, contrast,
  MAR, escalation)?
- Does the nursing worklist share the worklist event stream (`/worklist*` +
  `/ws`) or need its own?
- Is adverse-reaction escalation a notification-only flow, or does it need a
  dedicated escalation record?

## Discussion Log

_(pending backend review)_
