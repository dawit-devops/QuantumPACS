# Sprint MVP-03 Detail — Order Search & Status API (E-RIS-04 #3/4) + Conflict-Free Scheduling (E-RIS-05)

**Version:** 1.0 · **Date:** 2026-08-18 · **Source:** `ris-integration-spec.md` §9.1; `RELEASE_PLAN.md` E-RIS-04 #3/4, E-RIS-05; `02_end_to_end_workflows.md` RIS-WF1/WF7; `04_uiux_requirements.md` RIS-UI-13…19
**Cadence:** two 2-week sprints (S4–S5) · **Squads:** RIS-MVP — two backend, two frontend, part-time integration engineer, QA

---

## 1. Sprint Goal

> **"A scheduler books a conflict-free appointment in under 1.5 seconds with room/technologist/contrast checks enforced at the database level; the order status lifecycle is queryable with filters and pagination; and the referring physician sees real-time order status."**

**Scope in:** Order search/status API, referring-MD status view, resource model (rooms/modalities/technologists), booking with EXCLUDE constraint, calendar/list day view, reschedule/cancel with audit, double-book override flow.

**Scope out:** MWL serving (S6), MPPS (S6), reporting (S8–S9).

---

## 2. Team Capacity (two 10-day sprints)

| Role | FTE | Available dev-days (×2) | Notes |
| :--- | :-: | :-: | :--- |
| Backend engineer ×2 | 2.0 | 40 | Order search API, scheduling engine, EXCLUDE constraint, resource model |
| Frontend engineer ×2 | 2.0 | 40 | Calendar grid, booking form, resource manager, order status views |
| Integration engineer | 0.5 | 10 | Scheduling conformance, conflict detection testing |
| QA | 1.0 | 20 | Scheduling E2E, conflict tests, RLS regression |
| **Total** | **5.5** | **~110** | Total task estimate below: **~48 dev-days** (BE 16.0 · FE 20.0 · INT 4.0 · QA 8.0) — ~62 days slack |

---

## 3. Task Board

### 3.1 Order Search & Status — E-RIS-04 #3/4
**Source:** `RELEASE_PLAN.md` E-RIS-04 #3/4; `ris-integration-spec.md` §4.1; `06_acceptance_criteria.md` RIS-AC-P08-01.

| ID | Task | Owner | Est. | Dep | Acceptance check |
| :-: | :--- | :-: | :-: | :-: | :--- |
| S3-01 | Order search API: `GET /api/ris/orders` with filters (status, priority, patient, accession, date range, referring physician); server-side pagination with `total` | BE | 2.0 | S2-08 | Paginated results; filters work; RIS-AC-P08-01 |
| S3-02 | Order detail API: `GET /api/ris/orders/{id}` with status history, procedures, appointments | BE | 1.0 | S3-01 | Full order detail with lifecycle |
| S3-03 | Order status transition API: `PUT /api/ris/orders/{id}/status` with guard validation + audit | BE | 1.5 | S2-09 | Invalid transitions blocked; audited |
| S3-04 | Order status history API: `GET /api/ris/orders/{id}/status-history` — chronological status changes with actor + reason | BE | 1.0 | S3-03 | Timeline of status changes |
| S3-05 | Referring physician status view: `GET /api/ris/orders` scoped to referring physician's patients only (RLS) | BE | 1.0 | S3-01 | Referring MD sees only their orders; RLS enforced |

**Epic exit contribution:** E-RIS-04 #3/4 (order search + status).

### 3.2 Resource Model & Availability — E-RIS-05 #1
**Source:** `RELEASE_PLAN.md` E-RIS-05 #1; `ris-integration-spec.md` §3.2 (ris_resources, ris_resource_schedules).

| ID | Task | Owner | Est. | Dep | Acceptance check |
| :-: | :--- | :-: | :-: | :-: | :--- |
| S3-06 | `ris_resources` + `ris_resource_schedules` tables + Alembic migration (Migration 2 partial) | BE | 1.5 | — | Tables created; seed data for test tenant |
| S3-07 | Resource API: `GET /api/ris/resources` (list rooms/modalities/technologists), `POST /api/ris/resources` (create), `GET /api/ris/appointments/availability` (slot search) | BE | 2.0 | S3-06 | Calendar renders slots; availability search works |
| S3-08 | Resource manager UI: new `frontend/src/schedule/ResourceManager.tsx` — list rooms/modality/technologist resources; create/edit; availability schedule editor | FE | 3.0 | S3-07 | RIS-UI-34 parity; WCAG 2.1 AA |

**Epic exit contribution:** E-RIS-05 #1 (resource model).

### 3.3 Conflict-Free Booking — E-RIS-05 #2/3/4/5
**Source:** `RELEASE_PLAN.md` E-RIS-05 #2–5; `ris-integration-spec.md` §5.2; `04_uiux_requirements.md` RIS-UI-13…15/19; `06_acceptance_criteria.md` RIS-AC-P03-01/05.

| ID | Task | Owner | Est. | Dep | Acceptance check |
| :-: | :--- | :-: | :-: | :-: | :--- |
| S3-09 | `ris_appointments` table + EXCLUDE constraint + GiST index (Migration 2 from spec §3.2); conflict-free at DB level | BE | 2.0 | S3-06 | EXCLUDE constraint prevents double-book; RIS-AC-P03-01 |
| S3-10 | Scheduling engine: `POST /api/ris/appointments` with conflict check (room/technologist/contrast), contraindication warnings, prior-auth check (stub) | BE | 3.0 | S3-07, S3-09 | Booking < 1.5s (RIS-SL-11); 0 conflicts (RIS-SL-34) |
| S3-11 | Reschedule/cancel API: `PUT /api/ris/appointments/{id}` with reason capture, slot release, patient notification trigger, audit logged | BE | 1.5 | S3-10 | Audited; slot released; RIS-UI-19 |
| S3-12 | Double-book/contrast override flow: override with mandatory reason, audited; override rate tracked | BE | 1.0 | S3-10 | Override rate < 1% (RIS-SL-34); audited |
| S3-13 | Appointment → worklist entry creation: book appointment → `worklist_entries` row created (MWL-ready) | BE | 1.0 | S3-10 | MWL entry exists after booking; S6-ready |
| S3-14 | Calendar grid UI: new `frontend/src/schedule/CalendarGrid.tsx` — per-room/modality calendar with slot availability, drag-to-book, click-to-book, visual conflict prevention (red/disabled when double-book) | FE | 5.0 | S3-07 | RIS-UI-13 parity; WCAG 2.1 AA |
| S3-15 | Booking form UI: new `frontend/src/schedule/BookingForm.tsx` — patient search + MPI hint, procedure (triggers prep/contrast rules), priority, site/room/technologist, time; shows prep instructions & contrast warnings inline | FE | 4.0 | S3-10 | RIS-UI-14 parity; inline warnings |
| S3-16 | Day view: calendar + list view of day's schedule with status colors, room/technologist assignments, priority badges; row actions with status guards | FE | 3.0 | S3-14 | RIS-UI-13/03-05 parity |
| S3-17 | Reschedule/cancel UI: reason capture form, slot release confirmation, audit trail visible | FE | 1.5 | S3-11 | RIS-UI-19 parity |

**Epic exit contribution:** E-RIS-05 #2–5 (conflict-free scheduling + day view).

### 3.4 Cross-cutting: E2E & Gates

| ID | Task | Owner | Est. | Dep | Acceptance check |
| :-: | :--- | :-: | :-: | :-: | :--- |
| S3-18 | Scheduling E2E: create resources → book appointment → conflict detected → override → reschedule → cancel → slot released | QA | 2.0 | S3-10…17 | RIS-AC-P03-01/05; RIS-SL-34 |
| S3-19 | Order search E2E: ORM → order → search by patient/accession/status → status history → referring MD view | QA | 1.5 | S3-01…05 | RIS-AC-P08-01 |
| S3-20 | EXCLUDE constraint stress test: 50 concurrent bookings for same room → 0 conflicts; DB-level enforcement verified | QA | 1.0 | S3-09 | RIS-SL-34 under load |
| S3-21 | RLS on appointments + resources: cross-facility bookings denied; home-facility bookings work | QA | 1.0 | S3-09 | PAC-SL-61 on scheduling tables |

---

## 4. Sprint Milestones

| Milestone | Target | Evidence |
| :--- | :--- | :--- |
| **Day 3 (S4)** | Order search API; resources table + API; calendar grid scaffold | S3-01, S3-06/07, S3-14 started |
| **Day 8 (S4)** | Order status API; EXCLUDE constraint; booking engine; resource manager UI | S3-03/04, S3-09/10, S3-08 closed |
| **Day 5 (S5)** | Booking form; calendar grid complete; day view; reschedule/cancel | S3-15/16/17 closed |
| **Day 10 (S5, demo)** | Scheduling + order E2E green; EXCLUDE stress test; demo: book → conflict → override → reschedule | S3-18…21; sprint review |

---

## 5. Sprint Definition of Done

| # | Check | Verifies | Method |
| :-: | :--- | :--- | :--- |
| D1 | Conflict-free booking: EXCLUDE constraint enforced; 0 double-books; override audited | RIS-AC-P03-01, RIS-SL-34 | S3-18/20 |
| D2 | Booking < 1.5s p95; slot search fast | RIS-SL-11 | S3-18 perf |
| D3 | Calendar + day view: status colors, room/tech assignments, priority badges; row actions with guards | RIS-UI-13/03-05 | S3-16 visual |
| D4 | Order search + status API; referring MD view; RLS enforced | RIS-AC-P08-01 | S3-19 |
| D5 | Appointment → worklist entry created (MWL-ready for S6) | S6 prerequisite | S3-13 verified |
| D6 | Engineering DoD: `tsc --noEmit` + `vite build` clean; unit tests green; migrations reviewed | release-plan §6 | CI gate |
| D7 | No P0/P1 open defects | release-plan §6 | Defect triage |

---

## 6. Risks & Watch Items

| Risk | Watch indicator | Mitigation |
| :--- | :--- | :--- |
| EXCLUDE constraint GiST index performance on large appointment volumes | S3-20 stress test | Partial index (only non-cancelled); partition by date if needed |
| Calendar grid complexity (drag-to-book, conflict visualization) | S3-14 estimate 5.0 FE | Start with click-to-book; drag-to-book in slack if time permits |
| Booking form scope creep (contrast rules, prep instructions) | S3-15 | Inline warnings from procedure data; full contrast rule engine deferred to v1.1 |
| Existing frontdesk appointments table conflicts with new `ris_appointments` | Schema drift | New table is `ris_appointments`; existing `appointments` kept for backward compat during transition |

---

## Traceability

| Source work item | Tasks |
| :--- | :--- |
| E-RIS-04 #3 (order search) | S3-01/02 |
| E-RIS-04 #4 (order status) | S3-03/04/05 |
| E-RIS-05 #1 (resource model) | S3-06/07/08 |
| E-RIS-05 #2 (conflict-free booking) | S3-09/10 |
| E-RIS-05 #3 (day view) | S3-14/16 |
| E-RIS-05 #4 (reschedule/cancel) | S3-11/17 |
| E-RIS-05 #5 (override flow) | S3-12 |
| Cross-cutting (scheduling E2E, order E2E, EXCLUDE stress, RLS) | S3-18…21 |
