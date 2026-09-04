# Release Plan — RIS (Radiology Information System)

**Version:** 1.0 · **Date:** 2026-08-04 · **Source:** `requrements/RIS/PRD.md` (§5.1 phased rollout)
**Planning assumptions:** 2-week sprints · two squads — **Platform** (shared services: auth/RBAC, tenant provisioning, audit, interface engine) and **RIS-Clinical** (RIS domain) · part-time integration engineer for HL7/DICOM conformance. **MVP estimated at 11–12 sprints (~5–6 months).**

---

## 1. Release Overview

| Phase | Scope (PRD §5.1) | Est. duration | Exit gate |
| :--- | :--- | :--- | :--- |
| **MVP v1.0** | Registration+MPI, order intake, scheduling, MWL/MPPS, tracking, reporting+dictation, critical results, ORU, charge capture, audit/RBAC/provisioning | 11–12 sprints | RIS-AC-P02-01/02, P03-01, P05-03 pass; MWL ≥ 98% auto-fill; interface > 99.9% |
| **v1.1** | Prior-auth, reminders, denial rework, template manager, multi-site (IDN grants), SR polish, FHIR | 6–8 sprints | RIS-AC-P03-02/03, P05-02; prior-auth ≥ 95% pre-scan; unbilled $0 > 5 days |
| **v2.0** | Full FHIR, portal delivery, AI-assisted coding, chargeback analytics, pre-registration | 6–8 sprints | Coding acceptance ≥ 90%; RIS-SL-40/41 sustained |

---

## 2. MVP Exit-Gate Acceptance Criteria (Definition of "releasable")

| Gate | Criterion | Verifies |
| :-: | :--- | :--- |
| G1 | MWL auto-populates from scheduled orders; ≥ 98% of exams without manual entry | RIS-AC-P02-01, RIS-SL-33 |
| G2 | Conflict-free booking: scheduling enforced with 0 conflicts (room/technologist/contrast) | RIS-AC-P03-01, RIS-SL-34 |
| G3 | MPPS IN_PROGRESS/COMPLETED/DISCONTINUED drives the tracking board < 5 s and echoes to PACS | RIS-AC-P02-02, RIS-SL-22 |
| G4 | Auto charge drop on report sign-off; charge capture ≥ 98% | RIS-AC-P05-03, RIS-SL-40 |
| G5 | Interface delivery > 99.9%; failures alerted ≤ 5 min with exception queue | RIS-SL-23 |
| G6 | Atomic tenant provisioning < 15 min; RLS isolation verified; 100% audit | RIS-AC-P20-01, RIS-SL-60 |
| G7 | No P0/P1 open defects; UAT sign-off by scheduler, technologist, radiologist, biller | PRD §2.3 |

---

## 3. MVP Epics & Sprint-Sized Work Items

> Work items are sized to ≤ 3 dev-days each (2–4 per sprint per engineer). Story/AC/UI IDs reference the RIS requirement docs. Backend = schema+API; Frontend = UI; Integration = HL7/DICOM.

### E-RIS-01 · Platform Foundation (Platform squad) — dependency for all
**Source:** RIS-US-P19-01/02, RIS-US-P20-01; `RBAC_matrix_spec.md`; `pacs-ris-schema.sql` §2/§15–17.
> **Task-level detail (Sprint 1):** `requrements/sprint1_platform_foundation_detail.md` — task IDs S1-01…S1-29 with owners, dev-day estimates, dependency graph, and acceptance checks (shared with E-PAC-01).

| # | Work item | Size | Done when |
| :-: | :--- | :-: | :--- |
| 1 | Auth + token pair + refresh rotation + rate limiting (login) | S | Login flow per `auth_design.md` |
| 2 | RBAC seed: permissions, roles, role_permissions (incl. RIS roles) + `@requires_permission` | M | Seed matches `RBAC_matrix_spec.md` §8; unit tests |
| 3 | Tenant middleware: resolve facility, set `app.facility_id`, effective permissions | M | Cross-facility isolation test passes |
| 4 | `provision_tenant()` wiring: tenant-ops console → atomic provisioning (TRIAL→READY) | M | RIS-AC-P20-01 |
| 5 | Audit pipeline: trigger-based `audit_log` + structured viewer (`AUDIT_READ`) | M | 100% events; RIS-SL-60 |
| 6 | User/role management UI (tenant admin) | M | `roles_design.md` parity |
| 7 | Metering hooks (`API_CALLS`, `MWL_QUERIES`) — emit events to collector (ADR-010) + invoice view | D | Metering matches usage |

**Epic exit:** G6 passes in a staging tenant; platform foundations reused by EMR release.

### E-RIS-02 · Interface Engine & Monitoring (Integration engineer)
**Source:** RIS-US-P06-02; RIS-WF8; schema §9 (`interface_endpoints`, `hl7_messages`, `interface_events`).
> **Task-level detail (Sprint 2):** `requrements/sprint2_ingestion_interface_detail.md` — task IDs S2-01…S2-30 with owners, dev-day estimates, dependency graph, and acceptance checks (shared with E-PAC-02).

| # | Work item | Size | Done when |
| :-: | :--- | :-: | :--- |
| 1 | HL7 v2 listener (ADT/ORM/ORU) with ACK handling + raw log | M | Messages persisted, ACKed |
| 2 | Message parser → normalized segments (parsed JSONB) | M | ORM/ORU map to orders/results |
| 3 | Exception queue + retry/reconcile | M | 0 silent drops (G5) |
| 4 | Interface health dashboard + ≤ 5-min alerting (severity events) | M | G5; `INTERFACE_MONITOR` |
| 5 | FHIR R4 endpoints (ServiceRequest/DiagnosticReport) — read-only in MVP | D | Conformance smoke tests |

**Epic exit:** G5; ORM→order and ORU→EMR flows proven in integration lab.

### E-RIS-03 · Registration & MPI (RIS-Clinical)
**Source:** RIS-US-P04-01…03; RIS-WF2; schema §4.

| # | Work item | Size | Done when |
| :-: | :--- | :-: | :--- |
| 1 | Patient CRUD + insurance capture (`PATIENT_READ/WRITE`) | M | RIS-AC-P04-01 (registration) |
| 2 | MPI probable-match detection (trigram) + review/merge flow | M | Dup rate < 1% (RIS-SL-37) |
| 3 | ADT A04/A08/A40 sync (demographics, merge) | M | Merges propagate (RIS-AC-P06-04) |
| 4 | Check-in from schedule → Arrived (one click) | M | RIS-AC-P04-03 |
| 5 | Eligibility check stub → provider API (v1 local, v2 live) | D | RIS-AC-P04-02 |

**Epic exit:** RIS-AC-P04-01/03; MPI merge audited & undoable.

### E-RIS-04 · Order Intake (RIS-Clinical + Integration)
**Source:** RIS-US-P08-01; RIS-WF1; schema §5 (`orders`, `order_procedures`).

| # | Work item | Size | Done when |
| :-: | :--- | :-: | :--- |
| 1 | Order model + accession assignment (unique per facility) | M | RIS-AC-P06-01 |
| 2 | ORM intake → order with priority/indication/prior-auth flag | M | Accessible < 1 min (RIS-SL-20) |
| 3 | Order status lifecycle engine (Ordered→…→Signed) with guards | M | Invalid transitions blocked |
| 4 | Order search/status API + referring-MD status view | D | RIS-AC-P08-01 |

**Epic exit:** RIS-SL-20; accession collisions impossible (unique index).

### E-RIS-05 · Scheduling (RIS-Clinical)
**Source:** RIS-US-P03-01/05; RIS-WF1/WF7 (single-site in MVP); schema `appointments` (EXCLUDE).

| # | Work item | Size | Done when |
| :-: | :--- | :-: | :--- |
| 1 | Room/modality/technologist resource model + availability | M | Calendar renders slots |
| 2 | Booking with conflict & contraindication checks (EXCLUDE guard) | M | RIS-AC-P03-01 (0 conflicts) |
| 3 | Calendar + list day view with status colors & guards | M | RIS-AC-P03-05, RIS-UI-13 |
| 4 | Reschedule/cancel with reason + audit + slot release | M | Audited, no leaks |
| 5 | Double-book/contrast override flow (audited) | D | Override rate < 1% |

**Epic exit:** G2; RIS-AC-P03-01/05.

### E-RIS-06 · MWL Serving & MPPS (Integration + RIS-Clinical)
**Source:** RIS-US-P02-01/02; RIS-WF1; schema `worklist_entries`, `mpps_events`.

| # | Work item | Size | Done when |
| :-: | :--- | :-: | :--- |
| 1 | MWL SCP (DICOM C-FIND) serving scheduled entries | M | Scanner query returns entries |
| 2 | MPPS N-CREATE/N-SET consumer → tracking status + PACS echo | M | RIS-AC-P02-02, RIS-SL-22 |
| 3 | Worklist search/filters/pagination + station AE endpoint | M | `worklist_design.md` parity |
| 4 | Query-count metering hook (`MWL_QUERIES`) | D | Metering accurate |

**Epic exit:** G1 + G3; RIS-AC-P02-01/02.

### E-RIS-07 · Tracking Board (RIS-Clinical)
**Source:** RIS-US-P07-01; RIS-WF1; RIS-UI-07…12.

| # | Work item | Size | Done when |
| :-: | :--- | :-: | :--- |
| 1 | Live board: exams, statuses, priority, room, technologist | M | Live updates ≤ 30 s (RIS-SL-15) |
| 2 | Status progress indicator + KPI strip (volume/in progress/overdue) | D | RIS-UI-08/12 |
| 3 | Filters (modality/site/status/priority/date) + server pagination | M | RIS-AC-P07-01 partial |
| 4 | Row actions with status guards (check-in, reassign, reschedule) | M | Guards enforced |

**Epic exit:** Tracking accuracy per G3; manager dashboard baseline.

### E-RIS-08 · Reporting (Radiologist)
**Source:** RIS-US-P01-01/02/05/06; RIS-WF4; schema `reports`, `report_versions`, `report_templates`.

| # | Work item | Size | Done when |
| :-: | :--- | :-: | :--- |
| 1 | Reading worklist (priority-sorted, filters, unread toggle) | M | RIS-AC-P01-01 |
| 2 | Report editor: structured templates + smart fields + autosave | M | RIS-AC-P01-02/06 |
| 3 | Report versioning (JSONB diffs) + draft/transcribed states | M | Every edit attributed |
| 4 | Viewer launch deep-link (StudyInstanceUID → PACS) | M | RIS-AC-P01-05 |
| 5 | Speech-recognition integration (dictation → fields, verify highlight) | D | RIS-AC-P01-02 (SR) |
| 6 | Sign & route (→ ORU + billing) | M | RIS-AC-P01-04 |

**Epic exit:** G4 (sign → charge); RIS-AC-P01-01/02/04/05/06.

### E-RIS-09 · Critical Results (Radiologist)
**Source:** RIS-US-P01-03; RIS-AC-P01-03; schema `critical_result_notifications`.

| # | Work item | Size | Done when |
| :-: | :--- | :-: | :--- |
| 1 | Flag critical finding (one action) + recipient selection | M | RIS-AC-P01-03 |
| 2 | Tracked notification (EHR_ALERT/MESSAGING/PAGE/PHONE) + acknowledgment | M | 100% ack, escalate per policy (RIS-SL-25) |
| 3 | Escalation policy config + unacknowledged alerting | D | Escalates on timeout |
| 4 | Critical flag embedded in ORU/FHIR payload | M | Payload carries flag |

**Epic exit:** RIS-SL-25; HIPAA-critical loop documented end-to-end.

### E-RIS-10 · Results Distribution (Integration + RIS-Clinical)
**Source:** RIS-US-P08-02; RIS-WF5.

| # | Work item | Size | Done when |
| :-: | :--- | :-: | :--- |
| 1 | Signed report → ORU to EMR (< 5 min) | M | RIS-AC-P08-02, RIS-SL-24 |
| 2 | Delivery status/retry on ORU failure | M | 0 silent failures |
| 3 | Portal/SMS/email result-availability notification (opt-out) | D | Derived from RIS-US-P08-02 (report delivery); see RIS-AC-P08-02 |

**Epic exit:** RIS-SL-24; delivery retry verified.

### E-RIS-11 · Billing Capture (RIS-Clinical)
**Source:** RIS-US-P05-01/03; RIS-WF6; schema `charges`, `claims`.

| # | Work item | Size | Done when |
| :-: | :--- | :-: | :--- |
| 1 | CPT/ICD-10 suggestion from procedure + signed report | M | RIS-AC-P05-01 |
| 2 | Auto charge drop on sign-off + billing queue | M | G4, RIS-AC-P05-03 |
| 3 | Unbilled aging view (daily reconcile) | M | Unbilled visibility (RIS-SL-41) |
| 4 | 837/835 export/import (clearinghouse) | D | Claim file smoke test |

**Epic exit:** G4; RIS-AC-P05-01/03.

---

## 4. Sprint Roadmap (MVP, 2-week sprints)

| Sprint | Focus (epics) | Key milestone |
| :-: | :--- | :--- |
| S1–S2 | E-RIS-01 (platform foundation) | Login + RBAC + tenant isolation green |
| S3 | E-RIS-02 (interface engine) + E-RIS-03 (registration) | ORM listener accepts real message |
| S4 | E-RIS-03 (MPI) + E-RIS-04 (order intake) | Order with accession created from ORM |
| S5 | E-RIS-05 (scheduling) | Conflict-free booking live |
| S6 | E-RIS-06 (MWL/MPPS) | Scanner pulls MWL; MPPS updates board |
| S7 | E-RIS-07 (tracking board) | Live board in UAT |
| S8–S9 | E-RIS-08 (reporting) | Template report + dictation + sign |
| S10 | E-RIS-09 (critical results) + E-RIS-10 (distribution) | Critical loop + ORU to EMR |
| S11 | E-RIS-11 (billing) | Auto charge drop + aging view |
| S12 | Hardening: UAT, performance (sub-second), DR drill, security test | MVP exit gates G1–G7 |

> v1.1/v2.0 epic-level backlog (post-MVP): **Prior-auth engine** (RIS-US-P03-03), **Reminders** (RIS-US-P03-02), **Denial rework** (RIS-US-P05-02), **Template manager** (RIS-US-P06-03), **Multi-site scheduling + IDN grants** (RIS-US-P03-04, `cross_tenant_grants_design.md`), **FHIR write APIs**, **AI-assisted coding** (gate: ≥ 90% coder acceptance), **chargeback analytics**.

---

## 5. Critical Path & Dependencies

```
Platform Foundation (E-RIS-01) ──► Interface Engine (E-RIS-02) ──► Order Intake (E-RIS-04)
                                                                    │
Registration/MPI (E-RIS-03) ──► Scheduling (E-RIS-05) ──► MWL/MPPS (E-RIS-06) ──► Tracking (E-RIS-07)
                                                                    │
                                                        Reporting (E-RIS-08) ──► Critical (E-RIS-09) ──► Distribution (E-RIS-10)
                                                                    │
                                                        Billing (E-RIS-11) ◀── (sign-off hook)
```

- **Blocking:** E-RIS-02 before E-RIS-04/10; E-RIS-01 before everything (shared auth/RBAC/audit/provisioning).
- **Parallelizable:** E-RIS-03 ∥ E-RIS-05 ∥ E-RIS-08 once platform + interface foundations exist.
- **External:** modality conformance statements (MWL/MPPS test set), EMR ORU endpoint (or test harness), clearinghouse credentials (D).
- **Shared with EMR release:** E-RIS-01 platform foundation, interface engine patterns, audit viewer, notifications — coordinate to avoid duplication.

---

## 6. Definition of Done (per work item)

- Backend: schema migration reviewed; API behind `@requires_permission`; Pydantic validation; unit tests green; audit event emitted where applicable.
- Frontend: Ant Design conventions, design tokens, WCAG 2.1 AA, `tsc --noEmit` + `vite build` clean.
- Integration: message conformance verified in lab; exception queue covered.
- Acceptance: the item's RIS-AC-* criteria pass in staging; traceability link updated.
- No P0/P1 defects open at sprint close.

---

## 7. Risks & Watch Items

| Risk | Watch indicator | Mitigation |
| :--- | :--- | :--- |
| HL7 interface latency (order→schedule > 1 min) | RIS-SL-20 metric | Interface lab daily; exception queue alerts |
| MWL auto-fill < 98% | RIS-SL-33 | Conformance test set; worklist quality dashboard |
| Double-booking regression | RIS-SL-34 | EXCLUDE constraint + E2E test on every schema change |
| Charge capture leakage | RIS-SL-40/41 | Daily unbilled reconcile; sign→charge test |
| Radiologist dictation adoption | SR acceptance in UAT | Superuser program; dictation polish in v1.1 |
| IDN scope creep in MVP | Cross-facility writes attempted | Read-only grants only (`cross_tenant_grants_design.md` §6.3) |
