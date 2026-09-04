# Sprint MVP-02 Detail — HL7 Interface Engine (E-RIS-02) & Registration Foundation (E-RIS-03 partial)

**Version:** 1.0 · **Date:** 2026-08-18 · **Source:** `ris-integration-spec.md` §9.1; `RELEASE_PLAN.md` E-RIS-02, E-RIS-03; `02_end_to_end_workflows.md` RIS-WF1/WF2/WF8
**Cadence:** one 2-week sprint (S3) · **Squads:** RIS-MVP — two backend, one frontend, part-time integration engineer, QA

---

## 1. Sprint Goal

> **"A real HL7 ORM message is received, parsed, routed to create an order, and ACK'd — with every failure in an exception queue and every event logged — while patient registration and MPI dedup work end-to-end."**

**Scope in:** HL7 v2 listener (ADT/ORM/ORU) with ACK handling, message parser → normalized segments, exception queue + retry/reconcile, interface health dashboard, patient CRUD + MPI, ADT sync.

**Scope out:** Scheduling (S5), MWL/MPPS (S6), FHIR endpoints (deferred to v1.1).

---

## 2. Team Capacity (one 10-day sprint)

| Role | FTE | Available dev-days | Notes |
| :--- | :-: | :-: | :--- |
| Backend engineer ×2 | 2.0 | 20 | Interface engine, HL7 parser, patient CRUD, MPI |
| Frontend engineer ×1 | 1.0 | 10 | Interface health dashboard, registration UI |
| Integration engineer | 0.5 | 5 | HL7 conformance, ACK handling, ADT/ORM message testing |
| QA | 1.0 | 10 | HL7 message E2E, MPI merge, RLS regression |
| **Total** | **4.5** | **~45** | Total task estimate below: **~34 dev-days** (BE 14.0 · FE 5.5 · INT 5.0 · QA 5.5) — ~11 days slack |

---

## 3. Task Board

### 3.1 HL7 Interface Engine — E-RIS-02 #1/2/3
**Source:** `RELEASE_PLAN.md` E-RIS-02 #1–3; `ris-integration-spec.md` §5.5; `ris-integration-spec.md` §3.2 Migration 5.

| ID | Task | Owner | Est. | Dep | Acceptance check |
| :-: | :--- | :-: | :-: | :-: | :--- |
| S2-01 | HL7 v2 listener: TCP socket accept ADT/ORM/ORU messages; parse to segments (JSONB); persist to `ris_hl7_messages` table; send ACK (AA/AE) | BE | 3.0 | S1-05 | Messages persisted; ACK returned; port configurable |
| S2-02 | HL7 message parser: validate segments (MSH, PID, PV1, OBR, ORC, DG1); normalize to internal model (order, patient, diagnosis) | BE | 2.5 | S2-01 | ORM^O01 → order model; ADT^A04 → patient model; parse errors → FAILED status |
| S2-03 | Exception queue: failed messages land in `ris_hl7_messages` with FAILED status; retry mechanism (configurable max_retries=3); manual reconcile endpoint | BE | 2.0 | S2-02 | 0 silent drops; exception queue shows failed messages with reason |
| S2-04 | Interface health metrics: `ris_hl7_messages_total` counter (by type/trigger/status), `ris_hl7_message_latency_seconds` histogram; Prometheus scrape endpoint | BE | 1.0 | S2-01 | Metrics queryable; dashboard data available |
| S2-05 | HL7 conformance test set: ORM^O01 sample messages (new order, update, cancel); ADT^A04/A08/A40 samples; verify parse + ACK | INT | 2.5 | S2-01 | Repeatable test scripts; ≥ 95% parse success |

**Epic exit contribution:** E-RIS-02 #1–3 (interface engine + exception queue).

### 3.2 Order Intake from ORM — E-RIS-04 #1/2
**Source:** `RELEASE_PLAN.md` E-RIS-04 #1/2; `ris-integration-spec.md` §3.2 Migration 1; `06_acceptance_criteria.md` RIS-AC-P06-01.

| ID | Task | Owner | Est. | Dep | Acceptance check |
| :-: | :--- | :-: | :-: | :-: | :--- |
| S2-06 | `ris_orders` table + Alembic migration (Migration 1 from spec §3.2); accession number generation (unique per facility, partial unique index) | BE | 2.0 | — | Migration applies; accession unique per facility; RIS-AC-P06-01 |
| S2-07 | `ris_order_procedures` table + migration; order→procedure linkage | BE | 1.0 | S2-06 | Procedures link to orders; multi-procedure per order |
| S2-08 | ORM → order service: parse ORM^O01 → create `ris_orders` row + `ris_order_procedures`; set status=ORDERED; accession assigned | BE | 2.0 | S2-02, S2-06 | ORM received → order accessible < 1 min (RIS-SL-20) |
| S2-09 | Order status lifecycle engine: `VALID_TRANSITIONS` dict; `transition()` method with guard + audit; side effects per transition | BE | 1.5 | S2-08 | Invalid transitions blocked; every transition audited |

**Epic exit contribution:** E-RIS-04 #1/2 (order intake + accession).

### 3.3 Registration & MPI — E-RIS-03 #1/2/3
**Source:** `RELEASE_PLAN.md` E-RIS-03 #1–3; `ris-integration-spec.md` §4.1; existing `db/frontdesk.py`.

| ID | Task | Owner | Est. | Dep | Acceptance check |
| :-: | :--- | :-: | :-: | :-: | :--- |
| S2-10 | Patient CRUD API: extend existing `api/frontdesk.py` patients endpoints to match RIS spec (`POST /api/ris/patients`, `GET /api/ris/patients/search`, etc.) | BE | 1.5 | — | RIS patient endpoints work; existing frontdesk endpoints unchanged |
| S2-11 | MPI probable-match detection: trigram similarity on name+DOB; review/merge flow; merge audited | BE | 2.0 | S2-10 | Dup rate < 1% (RIS-SL-37); merge undoable |
| S2-12 | ADT A04/A08/A40 sync: HL7 ADT → patient create/update/merge; propagation to existing patient records | BE | 1.5 | S2-02, S2-11 | Merges propagate; RIS-AC-P06-04 |
| S2-13 | Registration UI: extend existing `frontend/src/frontdesk/` registration form with RIS fields (demographics, insurance capture, MPI duplicate warnings inline) | FE | 4.0 | S2-10 | RIS-UI-20 parity; inline duplicate warnings |
| S2-14 | Insurance eligibility check stub: placeholder API that returns "active" for now; real provider API in v1.1 | BE | 0.5 | S2-10 | Stub returns status; RIS-AC-P04-02 (v1 local) |

**Epic exit contribution:** E-RIS-03 #1–3 (registration + MPI).

### 3.4 Interface Health Dashboard — E-RIS-02 #4
**Source:** `RELEASE_PLAN.md` E-RIS-02 #4; `ris-integration-spec.md` §4.1; `06_acceptance_criteria.md` RIS-AC-P06-02.

| ID | Task | Owner | Est. | Dep | Acceptance check |
| :-: | :--- | :-: | :-: | :-: | :--- |
| S2-15 | Interface health dashboard API: `GET /api/ris/interfaces` (list endpoints), `GET /api/ris/interfaces/{id}/messages` (message history), `GET /api/ris/interfaces/{id}/metrics` (counts, errors, latency), `GET /api/ris/interfaces/exceptions` (failed queue) | BE | 2.0 | S2-01 | RIS-AC-P06-02: dashboard data available |
| S2-16 | Interface health dashboard UI: new `frontend/src/admin/InterfaceDashboard.tsx` + `ExceptionQueue.tsx` — per-interface message counts, errors, latency, last-message times; alert rules config; exception queue with retry | FE | 2.5 | S2-15 | RIS-UI-37 parity; WCAG 2.1 AA; retry action works |
| S2-17 | ≤ 5-min alerting: interface failure event → notification to admin; test with simulated failure | BE | 1.0 | S2-04 | G5: failures alerted ≤ 5 min |

**Epic exit contribution:** E-RIS-02 #4 (interface health).

### 3.5 Cross-cutting: E2E & RLS

| ID | Task | Owner | Est. | Dep | Acceptance check |
| :-: | :--- | :-: | :-: | :-: | :--- |
| S2-18 | HL7 E2E: send ORM^O01 → parse → order created → ACK returned → exception queue test (bad message → FAILED → retry) | QA | 2.0 | S2-01…09 | RIS-SL-20; G5 partial |
| S2-19 | Registration E2E: ADT^A04 → patient created → MPI match → duplicate detected → merge → ADT^A40 → merged | QA | 1.5 | S2-10…14 | RIS-AC-P04-01; RIS-SL-37 |
| S2-20 | RLS on new tables: `ris_orders`, `ris_order_procedures`, patient records — cross-facility denied; home-facility reads work | QA | 1.0 | S2-06 | PAC-SL-61 on new tables |

---

## 4. Sprint Milestones

| Milestone | Target | Evidence |
| :--- | :--- | :--- |
| **Day 3** | HL7 listener scaffold; `ris_orders` migration; patient CRUD API started | S2-01, S2-06, S2-10 started |
| **Day 5** | HL7 parser + ACK + exception queue; ORM → order service; registration UI started | S2-01…03, S2-08, S2-13 started |
| **Day 8** | MPI + ADT sync; order lifecycle engine; interface dashboard; insurance stub | S2-11/12, S2-09, S2-15/16, S2-14 closed |
| **Day 10 (demo)** | HL7 + registration E2E green; demo: ORM → order → registration; exception queue retry; dashboard | S2-18…20; sprint review |

---

## 5. Sprint Definition of Done

| # | Check | Verifies | Method |
| :-: | :--- | :--- | :--- |
| D1 | HL7 listener receives, parses, ACKs ORM; exception queue catches failures; 0 silent drops | E-RIS-02 #1–3, G5 | S2-18 |
| D2 | ORM → order with accession created < 1 min; accession unique per facility | E-RIS-04 #1/2, RIS-SL-20 | S2-18 |
| D3 | Registration with MPI dedup; ADT sync; merge audited | E-RIS-03 #1–3, RIS-SL-37 | S2-19 |
| D4 | Interface dashboard + ≤ 5-min alerting | RIS-AC-P06-02 | S2-16/17 |
| D5 | RLS on new tables; cross-facility denied | PAC-SL-61 | S2-20 |
| D6 | Engineering DoD: `tsc --noEmit` + `vite build` clean; unit tests green; migrations reviewed | release-plan §6 | CI gate |
| D7 | No P0/P1 open defects | release-plan §6 | Defect triage |

---

## 6. Risks & Watch Items

| Risk | Watch indicator | Mitigation |
| :--- | :--- | :--- |
| HL7 message format variance (real-world vendor differences) | S2-05 conformance test set | Parser accepts common variants; exception queue for unknown formats; manual reconcile |
| MPI trigram false positives | RIS-SL-37 dup rate | Conservative threshold; review/merge flow; undo capability |
| Registration UI complexity (demographics + insurance + MPI) | S2-13 estimate 4.0 FE | Scope to demographics + MPI warnings; insurance details deferred to v1.1 |
| Existing HL7 receiver (`api/hl7.py`) conflicts with new engine | Regression risk | New engine runs on separate port; old receiver kept for backward compat during transition |

---

## Traceability

| Source work item | Tasks |
| :--- | :--- |
| E-RIS-02 #1 (HL7 listener) | S2-01 |
| E-RIS-02 #2 (parser) | S2-02 |
| E-RIS-02 #3 (exception queue) | S2-03 |
| E-RIS-02 #4 (interface health) | S2-04, S2-15…17 |
| E-RIS-04 #1 (order model + accession) | S2-06/07 |
| E-RIS-04 #2 (ORM intake) | S2-08/09 |
| E-RIS-03 #1 (patient CRUD) | S2-10 |
| E-RIS-03 #2 (MPI) | S2-11 |
| E-RIS-03 #3 (ADT sync) | S2-12 |
| Cross-cutting (HL7 E2E, registration E2E, RLS) | S2-18…20 |
