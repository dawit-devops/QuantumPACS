# RIS — End-to-End Workflow Maps

**Document:** 02 of 06 · **Version:** 1.0 · **Date:** 2026-08-04

Swimlane workflow maps for the RIS product surface. Priorities: M/D/O. Cross-references PACS workflows where the journey continues.

---

## RIS-WF1 · Order → Schedule → Exam (order intake & scheduling)

> **Actors:** Referring MD (EMR) · Front Desk · Scheduler · RIS engine · Modality · PACS
> **Priority:** M

```
Referring MD / EMR     Front Desk          Scheduler            RIS Engine          Modality / PACS
  ORM order ──────────▶│                    │                     │                      │
                       │ pre-register (opt) │                     │ assign accession     │
                       │                    │ book slot ─────────▶│ conflict checks      │
                       │                    │                     │ (room/tech/contrast) │
                       │                    │                     │ set status=SCHEDULED │
                       │                    │                     │ reminders (M05)      │
                       │                    │                     │ serve MWL ──────────▶│ C-FIND
                       │                    │                     │                      │ MPPS IN_PROGRESS
                       │                    │                     │◀── status ──────────│
                       │                    │                     │ MPPS COMPLETED ────▶│ PACS
                       │◀── status updates ─│                     │ tracking board live  │
```

**Requirements**
- **Order intake:** HL7 ORM / FHIR ServiceRequest → order with accession, priority (Routine/Urgent/STAT), clinical indication, prior-auth flag. *(RIS-US-P08-01)*
- **Accession uniqueness:** enforced per tenant (unique index). *(RIS-US-P06-01)*
- **Scheduling:** multi-modality/site booking with resource conflict & contraindication checks (double-book prevention, contrast conflicts). *(RIS-US-P03-01/02)*
- **MWL serving:** scheduled orders appear on the modality worklist before patient arrival. *(RIS-US-P02-01)*
- **Status lifecycle:** Ordered → Scheduled → Arrived → In Progress → Completed → Read → Signed, updated by MPPS + manual events, live on the tracking board.

**Exit criteria:** exam booked without conflicts; worklist populated; status visible end-to-end.

---

## RIS-WF2 · Registration & Intake (front desk)

> **Actors:** Patient · Front Desk · MPI · HIS · RIS
> **Priority:** M

```
Patient            Front Desk           MPI / HIS             RIS
 check-in ────────▶ verify ID/insurance ─▶ MPI lookup ────────▶ match or create patient
                   capture demographics   (dedup check)        assign encounter
                   collect consents                            insurance verification
                   arrive status ────────────────────────────▶ tracking board = Arrived
```

**Requirements:** demographics/insurance capture with insurance eligibility verification; MPI duplicate detection & merge flows (ADT updates honored); digital pre-registration (patient portal) support; check-in one-click from schedule. *(RIS-US-P04-01/02)*

---

## RIS-WF3 · Prior Authorization & Scheduling Rules

> **Actors:** Scheduler · Prior-auth system · Payer (I06) · RIS
> **Priority:** D

```
Scheduler           RIS Rule Engine         Prior-Auth / Payer
 order flagged ────▶ requires prior-auth? ──▶ submit auth request
                     check auth status ◀──── status: approved/denied/pending
                     block/reschedule/       notify scheduler
                     prompt CPT evidence
```

**Requirements:** prior-auth tracking per order (status, expiry, CPT linkage); scheduling rules block booking of denied exams with override workflow; reminders for expiring authorizations. *(RIS-US-P03-03)*

---

## RIS-WF4 · Reading, Reporting & Critical Results

> **Actors:** Radiologist · RIS worklist · PACS viewer · Dictation/SR · Referring MD · EMR
> **Priority:** M

```
Radiologist         RIS Worklist        PACS Viewer         Dictation/SR        Referring MD / EMR
 open worklist ────▶ prioritized reads ─▶ launch study
 dictate/type ─────▶ template + SR ────────────────────────▶ transcript
 flag critical ────▶ critical alert (documented, tracked) ─────────────────────▶ notify + ack
 sign report ──────▶ finalize ──▶ ORU / FHIR DiagnosticReport ─────────────────▶ EMR
                    └── status = Signed
```

**Requirements**
- **Reading worklist:** priority-sorted, filters, unread backlog; AI-flag support. *(RIS-US-P01-01)*
- **Structured templates:** per exam type; speech recognition integration with verification. *(RIS-US-P01-02)*
- **Critical results:** one-action flag → tracked notification (call/message/page) with acknowledgment & escalation — HIPAA-critical. *(RIS-US-P01-03)*
- **Sign & distribute:** signed report routed to EMR via ORU/FHIR and to billing. *(RIS-US-P01-04)*

---

## RIS-WF5 · Results Distribution & Patient Notifications

> **Actors:** RIS · EMR · Patient portal · SMS/email · Referring MD
> **Priority:** D

```
Signed report ──▶ EMR (ORU/FHIR) ──▶ portal availability notification ──▶ patient
                  └── referring MD inbox ──▶ viewed/acknowledged tracking
```

**Requirements:** automatic result delivery to EMR; portal/SMS/email notifications with opt-out; read-receipt tracking for urgent results. *(RIS-US-P05-01, RIS-US-P08-02)*

---

## RIS-WF6 · Billing & Revenue Cycle

> **Actors:** Radiologist (sign) · Billing Coder · RIS billing engine · PM/Clearinghouse · Payer
> **Priority:** M

```
Signed report ──▶ billing workspace (CPT/ICD-10 from procedure + report)
                  charge drop ──▶ 837 claim ──▶ clearinghouse ──▶ payer
                  ◀── 835/denial ── rework queue ──▶ resubmit
                  unbilled log reconciled daily
```

**Requirements:** CPT/ICD-10 capture at order/procedure level; automatic charge drop on report sign-off; unbilled backlog visibility; denial rework workflow with reason codes; prior-auth linkage on claim. *(RIS-US-P05-01/02)*

---

## RIS-WF7 · Multi-Site Enterprise Scheduling (IDN)

> **Actors:** Scheduler · Enterprise resource pool · Sites · RIS
> **Priority:** D

```
Scheduler            Enterprise RIS          Site A / Site B
 search slots ──────▶ availability across sites (rooms/tech/contrast)
 book at best site ─▶ shared resource pool update ──▶ both sites see conflict-free calendar
```

**Requirements:** centralized scheduling across facilities with shared resource visibility; patient can choose preferred site; site-level SLAs preserved; chargeback data captured per site. *(RIS-US-P03-04)*

---

## RIS-WF8 · Interface Monitoring & Exception Handling

> **Actors:** RIS Admin · Interface engine · Exception queue · Ops
> **Priority:** M

```
HL7/DICOM/MPPS events ──▶ interface engine ──▶ success → processed
                                  └─ failure ──▶ exception queue + alert (≤5 min)
                                  ──▶ retry / manual reconcile / audit
```

**Requirements:** > 99.9% message delivery; every failure alerted within 5 min; exception queue with retry/reconcile; orphan-order handling (no accession); audit of all interface events. *(RIS-US-P06-02)*

---

## RIS-WF9 · Tenant Provisioning & Configuration (RIS onboarding)

> **Actors:** Super Admin · Tenant Admin · RIS
> **Priority:** M

```
Super Admin            Provisioning (atomic)          Tenant Admin
 create tenant ──────▶ insert facility + TRIAL subscription
                       seed sites, rooms, modalities, retention, report templates
                       stage PROVISIONING→SEEDING→READY ──▶ configure schedules, codes, users, interfaces
```

Atomic per `pacs-ris-schema.sql` §16 (`provision_tenant()`); rollback on failure. *(RIS-US-P20-01)*

---

## Workflow Traceability

| Workflow | Personas | Primary stories | Acceptance |
| :--- | :--- | :--- | :--- |
| RIS-WF1 | P02, P03, P08, M01, M02 | RIS-US-P02-01, P03-01/02, P08-01 | RIS-AC-P02-01, P03-*, P08-01 |
| RIS-WF2 | P04 | RIS-US-P04-01/02 | RIS-AC-P04-* |
| RIS-WF3 | P03, I06 | RIS-US-P03-03 | RIS-AC-P03-03 |
| RIS-WF4 | P01 | RIS-US-P01-01…04 | RIS-AC-P01-* |
| RIS-WF5 | P08, M05 | RIS-US-P08-02 | RIS-AC-P08-02 |
| RIS-WF6 | P05 | RIS-US-P05-01/02 | RIS-AC-P05-* |
| RIS-WF7 | P03, I04 | RIS-US-P03-04 | RIS-AC-P03-04 |
| RIS-WF8 | P06 | RIS-US-P06-02 | RIS-AC-P06-02 |
| RIS-WF9 | P19, P20 | RIS-US-P20-01 | RIS-AC-P20-01 |
