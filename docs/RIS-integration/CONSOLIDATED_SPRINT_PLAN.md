# Consolidated RIS Sprint Plan — QuantumPACS v3

**Version:** 1.1 · **Date:** 2026-08-18 · **Status:** Corrected (conformance fixes applied)  
**Source:** `ris-integration-spec.md`, `VALIDATION_REPORT.md`, `SPRINT_PLAN_CONFORMANCE_REPORT.md`  
**Scope:** 24 sprints (MVP S1–S12 + v1.1 R2-S1–S2-S7 + v2.0 R2-S8–R2-S12)  
**Platform:** QuantumPACS v3-dev (Starlette, React/Vite, PostgreSQL, asyncpg, Alembic)

---

## 1. Master Roadmap

| Phase | Sprint | Focus | Epics | Duration | Key Milestone | Exit Gate |
|:---|:---|:---|:---|:---|:---|:---|
| **MVP** | S1–S2 | Platform Foundation | E-RIS-01 | 4 weeks | Auth+RBAC+Isolation green | G6 |
| | S3 | Interface Engine + Registration | E-RIS-02, E-RIS-03 | 2 weeks | Real HL7 ORM → order | — |
| | S4–S5 | Scheduling Engine | E-RIS-04, E-RIS-05 | 4 weeks | Conflict-free booking | G2 |
| | S6–S7 | MWL/MPPS + Tracking | E-RIS-06, E-RIS-07 | 4 weeks | Scanner → tracking live | G1, G3 |
| | S8–S9 | Reporting + Sign-Off | E-RIS-08 | 4 weeks | Report → sign → distribute | — |
| | S10 | Critical Results + Distribution | E-RIS-09, E-RIS-10 | 2 weeks | Critical loop + ORU to EMR | — |
| | S11 | Billing Capture | E-RIS-11 | 2 weeks | Auto charge drop | G4, G5 |
| | S12 | Hardening + UAT | — | 2 weeks | G1–G7 all green | MVP |
| **v1.1** | R2-S1–S2 | Prior-Auth + Reminders | E-RIS2-01, E-RIS2-02 | 4 weeks | Prior-auth ≥ 95% | RVG-1 |
| | R2-S3–S4 | Denial + Templates + SR | E-RIS2-03, E-RIS2-04, E-RIS2-06 | 4 weeks | Unbilled $0 > 5d | RVG-2 |
| | R2-S5–S6 | IDN + Multi-Site | E-RIS2-05 | 4 weeks | Cross-site booking | RVG-3 |
| | R2-S7 | FHIR Read + Gates | E-RIS2-07 | 2 weeks | FHIR conformance green | RVG-4 |
| **v2.0** | R2-S8–S9 | Full FHIR + Portal | E-RIS2-08, E-RIS2-09 | 4 weeks | Portal results live | RVG-5 |
| | R2-S10–S12 | AI Coding + Chargeback + Hardening | E-RIS2-10, E-RIS2-11, E-RIS2-12 | 6 weeks | V2 go/no-go | RVG-6 |

### Critical Path

```
S1-2 Platform ──► S3 Interface ──► S4-5 Scheduling ──► S6-7 MWL/MPPS/Tracking
                    │                                          │
                    └──► S3 Registration ──────────────────────┘
                                                      │
                              S8-9 Reporting ──────────┤
                                                      │
                              S10 Critical+Distribute ─┤
                                                      │
                              S11 Billing ◀────────────┘
                                                      │
                                                 S12 Hardening
                                                      │
                              R2-S1-2 Prior-Auth+Reminders ──► R2-S3-4 Denial+Templates
                                        │                              │
                              R2-S5-6 IDN Grants ────────────────────┘
                                        │
                              R2-S7 FHIR Read ──► R2-S8-9 Full FHIR+Portal
                                                      │
                              R2-S10-12 AI+Chargeback+Hardening
```

---

## 2. Codebase Integration Map

### Existing Files to Modify

| Existing File | Sprint | What Changes |
|:---|:---|:---|
| `backend/api/auth.py` | S1 | Add RIS permission claims to JWT |
| `backend/api/tokens.py` | S1 | Extend token creation with RIS perms |
| `backend/api/rbac.py` | S1 | Verify `@requires_permission` with RIS perms |
| `backend/api/permissions.py` | S1 | Add RIS Permission enum values |
| `backend/api/tenant_middleware.py` | S1 | Verify `app.facility_id` for RIS tables |
| `backend/db/worklist.py` | S2, S6 | Add MWL fields, station_ae, priority, MPPS status |
| `backend/db/frontdesk.py` | S2, S3 | Extend patient CRUD, MPI, check-in |
| `backend/db/reports.py` | S8–S9 | Add versioning, sign-off hooks, template linkage |
| `backend/db/billing.py` | S11 | Add CPT suggestion, charge drop, unbilled aging |
| `backend/db/exams.py` | S6–S7 | Add MPPS status linkage, protocol assignment |
| `backend/api/worklist.py` | S2, S4, S6–S7 | MWL filters, tracking API, station AE |
| `backend/api/exams.py` | S6–S7 | MPPS-driven status updates, protocol assignment |
| `backend/api/reports.py` | S8–S9 | Templates, versioning, sign-off |
| `backend/api/billing.py` | S11 | CPT suggestion, charge drop, unbilled |
| `backend/api/frontdesk.py` | S2, S3 | Registration, MPI, check-in |
| `backend/api/hl7.py` | S3 | Route to new interface engine (replace inline processing) |
| `backend/api/notifications.py` | S6, S10 | Critical results, reminders |
| `backend/app.py` | S1, S6 | Register new services, MWL/MPPS DICOM |
| `frontend/src/navigator.ts` | S1, S3 | Add RIS workspaces and landing routes |
| `frontend/src/worklist/Worklist.tsx` | S6–S7 | Upgrade to tracking board |
| `frontend/src/radiologist/ReadingWorklist.tsx` | S8–S9 | Priority sorting, filters, viewer launch |
| `frontend/src/radiologist/ReportPanel.tsx` | S8–S9 | Structured templates, versioning |
| `frontend/src/schedule/CalendarView.tsx` | S4 | Conflict-free calendar grid |

### New Files to Create

| New File | Sprint | Purpose |
|:---|:---|:---|
| `backend/services/hl7_engine/__init__.py` | S3 | HL7 interface engine module |
| `backend/services/hl7_engine/engine.py` | S3 | Message queue, parse, route, retry |
| `backend/services/hl7_engine/parser.py` | S3 | HL7 v2 segment parser |
| `backend/services/mwl_scp/__init__.py` | S6 | MWL DICOM SCP service |
| `backend/services/mwl_scp/service.py` | S6 | C-FIND handler |
| `backend/services/mpps_consumer/__init__.py` | S6 | MPPS DICOM consumer |
| `backend/services/mpps_consumer/service.py` | S6 | N-CREATE/N-SET handler |
| `backend/services/scheduling/__init__.py` | S4 | Scheduling engine module |
| `backend/services/scheduling/engine.py` | S4 | Conflict-free booking |
| `backend/services/order_lifecycle/__init__.py` | S3 | Order state machine |
| `backend/services/order_lifecycle/service.py` | S3 | Status transitions + side effects |
| `backend/services/results_distribution/__init__.py` | S10 | ORU/FHIR distribution |
| `backend/services/results_distribution/service.py` | S10 | Sign → EMR delivery |
| `backend/services/prior_auth/__init__.py` | R2-S1–S2 | Prior-auth engine module |
| `backend/services/prior_auth/engine.py` | R2-S1–S2 | Payer integration, booking rules |
| `backend/db/ris_orders.py` | S3 | Order persistence |
| `backend/db/ris_appointments.py` | S4 | Appointment persistence |
| `backend/db/ris_resources.py` | S4 | Resource persistence |
| `backend/db/ris_critical_results.py` | S10 | Critical results persistence |
| `backend/db/ris_charges.py` | S11 | Billing persistence |
| `backend/db/ris_hl7.py` | S3 | HL7 message persistence |
| `backend/api/schemas/ris_orders.py` | S3 | Pydantic schemas for orders |
| `backend/api/schemas/ris_scheduling.py` | S4 | Pydantic schemas for appointments |
| `backend/api/schemas/ris_reports.py` | S8–S9 | Pydantic schemas for reports |
| `backend/api/schemas/ris_billing.py` | S11 | Pydantic schemas for billing |
| `backend/api/schemas/ris_critical.py` | S10 | Pydantic schemas for critical results |
| `backend/api/schemas/ris_prior_auth.py` | R2-S1–S2 | Pydantic schemas for prior-auth |
| `frontend/src/worklist/TrackingBoard.tsx` | S6 | Live tracking board |
| `frontend/src/worklist/TrackingBoard.css` | S6 | Tracking board styles |
| `frontend/src/worklist/KpiStrip.tsx` | S6 | KPI strip component |
| `frontend/src/schedule/CalendarGrid.tsx` | S4 | Calendar grid for scheduling |
| `frontend/src/schedule/BookingForm.tsx` | S4 | Appointment booking form |
| `frontend/src/schedule/ResourceManager.tsx` | S4 | Room/tech management |
| `frontend/src/radiologist/CriticalResults.tsx` | S10 | Critical results workflow |
| `frontend/src/billing/BillingQueue.tsx` | S7 | Billing queue with CPT suggestions |
| `frontend/src/billing/UnbilledAging.tsx` | S7 | Unbilled aging dashboard |
| `frontend/src/admin/InterfaceDashboard.tsx` | S3 | HL7/DICOM interface health |
| `frontend/src/admin/ExceptionQueue.tsx` | S3 | Failed message queue |

---

## 3. MVP Phase — Detailed Sprint Plans

### Sprint S1–S2 · Platform Foundation (4 weeks)

**Goal:** Every RIS endpoint behind permission-gated JWT with facility-scoped RLS; every write audit-logged; tenant provisioning atomic.

| ID | Task | Owner | Est. | Dep | Files Modified/Created | Acceptance |
|:---|:---|:---|:---|:---|:---|:---|
| S1-01 | Audit existing auth: JWT create/verify, refresh, login flow | BE | 1.0 | — | `api/auth.py`, `api/tokens.py` | Audit report; gaps identified |
| S1-02 | Add RIS permission claims to JWT payload | BE | 1.5 | S1-01 | `api/tokens.py` | Token contains RIS perms |
| S1-03 | RBAC seed: RIS permissions, roles, role_permissions | BE | 2.0 | S1-02 | `api/permissions.py`, seed script | Matches `01_persona_catalog.md` §4 |
| S1-04 | Rate limiting: RIS-specific limits per permission/tenant | BE | 1.5 | S1-01 | `api/ratelimit.py` | 429 on excess; existing limits unchanged |
| S1-05 | `@requires_permission` decorator: verify with RIS perms | BE | 1.0 | S1-03 | `api/rbac.py` | All RIS endpoints gated |
| S1-06 | Auth E2E: login → token → access → 403 without perm → refresh | QA | 1.5 | S1-05 | — | Auth flow green; no regression |
| S1-07 | Audit tenant middleware: `app.facility_id` resolution, RLS | BE | 1.0 | — | `api/tenant_middleware.py` | Audit report |
| S1-08 | Extend RLS: add `facility_id` RLS to new RIS tables | BE | 2.0 | S1-07 | Alembic migrations | Cross-facility returns 0 |
| S1-09 | `app_cross_accessible_facilities()` reuse for IDN | BE | 1.5 | S1-08 | `db/user_tenant_grants.py` | CTG-AC-01/02 smoke |
| S1-10 | Middleware caching: per-request facility-array cache | BE | 1.0 | S1-09 | `api/tenant_middleware.py` | Cross-facility auth < 1s |
| S1-11 | Tenant isolation E2E: two tenants, cross-facility denied | QA | 1.5 | S1-10 | — | PAC-SL-61 |
| S1-12 | Audit `provision_tenant()`: verify atomic create | BE | 1.0 | — | `db/tenant_provisioner.py` | Audit report |
| S1-13 | Extend `provision_tenant()` to seed RIS defaults | BE | 2.0 | S1-12 | `db/tenant_provisioner.py` | New tenant has RIS defaults |
| S1-14 | Rollback on failure: verify partial tenant rolled back | BE | 1.5 | S1-13 | `db/tenant_provisioner.py` | Rollback test green |
| S1-15 | Provisioning performance: measure time to READY | BE | 1.0 | S1-14 | — | READY < 15 min |
| S1-16 | Provisioning E2E: create → seed → RLS → verify → READY | QA | 1.5 | S1-15 | — | RIS-AC-P20-01 |
| S1-17 | Audit existing `audit_log` table: structure, triggers | BE | 1.0 | — | `db/audit_log.py` | Audit report |
| S1-18 | Add RIS audit events: order, appointment, report, charge, critical | BE | 2.0 | S1-17 | `db/audit_log.py` | 100% events logged |
| S1-19 | Structured audit viewer API: filter by event/actor/facility/date | BE | 1.5 | S1-18 | `api/logs.py` | `AUDIT_READ` enforced |
| S1-20 | Audit viewer UI: tenant admin page with filters | FE | 3.0 | S1-19 | `frontend/src/admin/` | WCAG 2.1 AA |
| S1-21 | Audit completeness: verify triggers on all RIS tables | QA | 1.5 | S1-18 | — | RIS-SL-60 |
| S1-22 | Audit existing roles/users UI | FE | 1.0 | — | `frontend/src/roles/`, `frontend/src/users/` | Audit report |
| S1-23 | Extend roles UI with RIS permissions | FE | 2.5 | S1-22 | `frontend/src/roles/` | RIS perms visible |
| S1-24 | Extend users UI with RIS roles | FE | 1.5 | S1-23 | `frontend/src/users/` | RIS roles assignable |
| S1-25 | User/role E2E: create user → assign role → login → verify | QA | 1.0 | S1-24 | — | Permissions enforced |
| S2-01 | Audit existing metering: `usage.events`, event emission | BE | 1.0 | — | `db/metering.py`, `api/metering.py` | Audit report |
| S2-02 | Add RIS metering events: MWL_QUERIES, API_CALLS, NOTIFICATIONS | BE | 2.0 | S2-01 | `db/metering.py` | Events emitted |
| S2-03 | Extend tenant usage view: RIS usage breakdown | BE | 1.5 | S2-02 | `api/metering.py` | Invoice drill-down |
| S2-04 | Metering E2E: generate traffic → verify counts → invoice | QA | 1.0 | S2-03 | — | RIS-SL-50 |
| S2-05 | Full RLS regression: all PACS tables | QA | 2.0 | S1-08 | — | PAC-SL-61 |
| S2-06 | Auth regression: existing PACS login, refresh, OAuth | QA | 1.5 | S1-05 | — | No regressions |
| S2-07 | Platform foundation E2E: full smoke | QA | 1.5 | S2-05/06 | — | G6 |
| S2-08 | UAT prep: platform admin script | QA | 1.0 | S2-07 | — | RIS-AC-P20-01 |

**Sprint Total:** ~42 dev-days · **Team:** 2 BE + 1 FE + 0.5 INT + 1 QA

---

### Sprint S3 · Interface Engine + Registration (2 weeks)

**Goal:** Real HL7 ORM → parsed → order created → ACK'd; patient registration with MPI dedup.

| ID | Task | Owner | Est. | Dep | Files Modified/Created | Acceptance |
|:---|:---|:---|:---|:---|:---|:---|
| S3-01 | HL7 v2 listener: TCP accept ADT/ORM/ORU; parse to JSONB; persist; ACK | BE | 3.0 | S1-05 | **NEW** `services/hl7_engine/engine.py` | Messages persisted; ACK returned |
| S3-01b | Route `api/hl7.py` to engine: replace inline processing with delegation to `services/hl7_engine/engine.py` | BE | 1.5 | S3-01 | `api/hl7.py` | Existing HL7 endpoint routes to new engine; no behavior change for callers |
| S3-02 | HL7 parser: validate MSH/PID/PV1/OBR/ORC/DG1; normalize | BE | 2.5 | S3-01 | **NEW** `services/hl7_engine/parser.py` | ORM→order; ADT→patient |
| S3-03 | Exception queue: FAILED status; retry (max 3); manual reconcile | BE | 2.0 | S3-02 | **NEW** `db/ris_hl7.py` | 0 silent drops |
| S3-04 | Interface health metrics: Prometheus counters + histogram | BE | 1.0 | S3-01 | `api/telemetry.py` | Metrics queryable |
| S3-05 | HL7 conformance test set: ORM/ADT samples | INT | 2.5 | S3-01 | Test scripts | ≥ 95% parse |
| S3-06 | `ris_orders` table + Alembic migration | BE | 2.0 | — | **NEW** `db/ris_orders.py`, migration | Accession unique per facility |
| S3-07 | `ris_order_procedures` table + migration | BE | 1.0 | S3-06 | Migration | Multi-procedure per order |
| S3-08 | ORM → order service: parse → create order + procedures | BE | 2.0 | S3-02, S3-06 | `services/hl7_engine/engine.py` | RIS-SL-20 |
| S3-09 | Order lifecycle: `VALID_TRANSITIONS`, `transition()` with audit | BE | 1.5 | S3-08 | **NEW** `services/order_lifecycle/service.py` | Invalid blocked; audited |
| S3-10 | Patient CRUD API: RIS endpoints | BE | 1.5 | — | `api/frontdesk.py` | Existing endpoints unchanged |
| S3-11 | MPI: trigram match, merge flow, undo, audit | BE | 2.0 | S3-10 | `db/frontdesk.py` | Dup rate < 1% |
| S3-12 | ADT A04/A08/A40 sync: patient create/update/merge | BE | 1.5 | S3-02, S3-11 | `services/hl7_engine/engine.py` | Merges propagate |
| S3-13 | Registration UI: demographics, insurance, MPI warnings | FE | 4.0 | S3-10 | `frontend/src/frontdesk/` | RIS-UI-20 |
| S3-14 | Insurance eligibility stub: returns "active" | BE | 0.5 | S3-10 | `api/frontdesk.py` | RIS-AC-P04-02 (v1 local) |
| S3-15 | Interface dashboard API: endpoints, messages, metrics, exceptions | BE | 2.0 | S3-01 | `api/hl7_admin.py` | RIS-AC-P06-02 |
| S3-16 | Interface dashboard UI: per-interface counts, errors, latency, retry | FE | 2.5 | S3-15 | **NEW** `frontend/src/admin/InterfaceDashboard.tsx` | RIS-UI-37 |
| S3-17 | ≤ 5-min alerting: failure event → admin notification | BE | 1.0 | S3-04 | `api/notifications.py` | G5 |
| S3-18 | HL7 E2E: ORM → order → ACK → exception → retry | QA | 2.0 | S3-01…09 | — | RIS-SL-20 |
| S3-19 | Registration E2E: ADT → patient → MPI → merge | QA | 1.5 | S3-10…14 | — | RIS-AC-P04-01 |
| S3-20 | RLS on new tables: cross-facility denied | QA | 1.0 | S3-06 | — | PAC-SL-61 |

**Sprint Total:** ~35.5 dev-days · **Team:** 2 BE + 1 FE + 0.5 INT + 1 QA

---

### Sprint S4–S5 · Scheduling Engine (4 weeks)

**Goal:** Scheduler books conflict-free appointment in < 1.5s; order status queryable; referring MD sees real-time status.

| ID | Task | Owner | Est. | Dep | Files Modified/Created | Acceptance |
|:---|:---|:---|:---|:---|:---|:---|
| S4-01 | Order search API: filters, pagination, referring-MD view | BE | 2.0 | S3-08 | `api/orders.py` | RIS-AC-P08-01 |
| S4-02 | Order detail API: status history, procedures, appointments | BE | 1.0 | S4-01 | `api/orders.py` | Full lifecycle |
| S4-03 | Order status transition API: guard + audit | BE | 1.5 | S3-09 | `api/orders.py` | Invalid blocked |
| S4-04 | Order status history API: chronological changes | BE | 1.0 | S4-03 | `api/orders.py` | Timeline visible |
| S4-05 | Referring MD status view: scoped to their patients | BE | 1.0 | S4-01 | `api/orders.py` | RLS enforced |
| S4-06 | `ris_resources` + `ris_resource_schedules` tables | BE | 1.5 | — | **NEW** `db/ris_resources.py`, migration | Seed data |
| S4-07 | Resource API: list, create, availability search | BE | 2.0 | S4-06 | `api/scheduling.py` | Calendar renders slots |
| S4-08 | Resource manager UI: list rooms/modality/tech, create, schedules | FE | 3.0 | S4-07 | **NEW** `frontend/src/schedule/ResourceManager.tsx` | RIS-UI-34 |
| S4-09 | `ris_appointments` table + EXCLUDE constraint + GiST index | BE | 2.0 | S4-06 | **NEW** `db/ris_appointments.py`, migration | 0 double-books |
| S4-10 | Scheduling engine: conflict check, contraindication, prior-auth stub | BE | 3.0 | S4-07, S4-09 | **NEW** `services/scheduling/engine.py` | RIS-SL-11, RIS-SL-34 |
| S4-11 | Reschedule/cancel API: reason, slot release, audit | BE | 1.5 | S4-10 | `api/scheduling.py` | RIS-UI-19 |
| S4-12 | Override flow: mandatory reason, audited | BE | 1.0 | S4-10 | `api/scheduling.py` | Override rate < 1% |
| S4-13 | Appointment → worklist entry creation | BE | 1.0 | S4-10 | `db/worklist.py` | MWL-ready for S6 |
| S4-14 | Calendar grid UI: per-room/modality, drag/click-to-book, conflict viz | FE | 5.0 | S4-07 | **NEW** `frontend/src/schedule/CalendarGrid.tsx` | RIS-UI-13 |
| S4-15 | Booking form UI: patient search, procedure, priority, room/tech, warnings | FE | 4.0 | S4-10 | **NEW** `frontend/src/schedule/BookingForm.tsx` | RIS-UI-14/15 |
| S4-16 | Day view: status colors, room/tech, priority badges, row actions | FE | 3.0 | S4-14 | `frontend/src/schedule/CalendarView.tsx` | RIS-UI-13/03-05 |
| S4-17 | Reschedule/cancel UI: reason, confirmation, audit | FE | 1.5 | S4-11 | `frontend/src/schedule/` | RIS-UI-19 |
| S4-18 | Scheduling E2E: book → conflict → override → reschedule → cancel | QA | 2.0 | S4-10…17 | — | RIS-AC-P03-01/05 |
| S4-19 | Order search E2E: ORM → order → search → status → referring MD | QA | 1.5 | S4-01…05 | — | RIS-AC-P08-01 |
| S4-20 | EXCLUDE stress test: 50 concurrent same-room bookings | QA | 1.0 | S4-09 | — | RIS-SL-34 |
| S4-21 | RLS on appointments + resources | QA | 1.0 | S4-09 | — | PAC-SL-61 |

**Sprint Total:** ~48 dev-days · **Team:** 2 BE + 2 FE + 0.5 INT + 1 QA

---

### Sprint S6–S7 · MWL/MPPS + Tracking Board (4 weeks)

**Goal:** Modality pulls MWL, performs exam, tracking board updates live < 5s; technologist never re-types patient data.

| ID | Task | Owner | Est. | Dep | Files Modified/Created | Acceptance |
|:---|:---|:---|:---|:---|:---|:---|
| S6-01 | MWL SCP: pynetdicom AE port 11113, C-FIND handler | BE | 3.0 | S4-13 | **NEW** `services/mwl_scp/service.py` | Scanner returns entries |
| S6-02 | MWL query filters: station_ae, name, id, accession, modality; priority sort (STAT first) | BE | 1.5 | S6-01 | `services/mwl_scp/service.py` | ≥ 98% auto-fill; STAT prioritized |
| S6-03 | Station AE endpoint: list active AEs | BE | 0.5 | S6-01 | `api/worklist.py` | Station AEs listed |
| S6-04 | MWL conformance test set: C-FIND requests | INT | 2.0 | S6-01 | Test scripts | ≥ 95% conformance |
| S6-05 | MWL REST API: extend `api/worklist.py` with RIS filters + pagination | BE | 1.5 | S6-01 | `api/worklist.py` | Paginated results |
| S6-06 | ALTER TABLE `worklist_entries`: add `ris_order_id`, `station_ae`, `priority`, `mpps_status`, `body_part`, `contrast`, `requesting_physician` | BE | 1.5 | S3-06 | Alembic migration (v2) | MWL fields added |
| S6-07 | MPPS consumer: pynetdicom AE port 11114, N-CREATE → IN_PROGRESS, N-SET → COMPLETED | BE | 3.0 | S6-01 | **NEW** `services/mpps_consumer/service.py` | RIS-AC-P02-02 |
| S6-08 | `ris_mpps_events` table + migration | BE | 1.0 | — | **NEW** `db/ris_mpps.py`, migration | Events logged |
| S6-09 | PACS echo: MPPS → echo study status to PACS | INT | 2.0 | S6-07 | `dcm_server.py` | PACS receives echo |
| S6-10 | MPPS conformance test set | INT | 1.5 | S6-07 | Test scripts | ≥ 95% conformance |
| S6-11 | MPPS latency instrumented: histogram | BE | 0.5 | S6-07 | `api/telemetry.py` | RIS-SL-22 |
| S6-12 | `api/exams.py`: add MPPS status linkage, protocol assignment | BE | 1.5 | S6-07 | `api/exams.py` | MPPS drives exam status |
| S6-13 | Tracking board API: live exam list, filters, pagination | BE | 2.5 | S4-01 | `api/worklist.py` | RIS-UI-07 |
| S6-14 | KPI strip API: volume, in-progress, awaiting, overdue, STAT | BE | 1.0 | S6-13 | `api/worklist.py` | RIS-UI-12 |
| S6-15 | Status update API: manual update with guard + audit | BE | 1.5 | S4-03 | `api/worklist.py` | RIS-UI-10 |
| S6-16 | Status timeline API: lifecycle changes | BE | 0.5 | S6-13 | `api/worklist.py` | Timeline visible |
| S6-17 | Tracking board UI: live board, status lifecycle, priority badges | FE | 5.0 | S6-13 | **NEW** `frontend/src/worklist/TrackingBoard.tsx` | RIS-UI-07/08 |
| S6-18 | KPI strip UI | FE | 2.0 | S6-14 | **NEW** `frontend/src/worklist/KpiStrip.tsx` | RIS-UI-12 |
| S6-19 | Filters + search: modality, site, room, status, priority, date | FE | 3.0 | S6-17 | `frontend/src/worklist/TrackingBoard.tsx` | RIS-UI-09 |
| S6-20 | Row actions: check-in, arrived, reassign, reschedule, cancel | FE | 2.5 | S6-15 | `frontend/src/worklist/TrackingBoard.tsx` | RIS-UI-10 |
| S6-21 | Critical-result badges: persistent until ack | FE | 1.0 | S6-17 | `frontend/src/worklist/TrackingBoard.tsx` | RIS-UI-11 |
| S6-22 | MWL E2E: book → MWL → modality → MPPS → tracking live | QA | 2.0 | S6-01…21 | — | RIS-AC-P02-01/02 |
| S6-23 | STAT E2E: STAT order → scheduling → MWL priority → reading queue | QA | 1.0 | S6-02 | — | RIS-AC-P09-01 |
| S6-24 | Tracking E2E: filter → actions → KPI → 50 concurrent updates | QA | 1.5 | S6-17 | — | RIS-UI-07…12 |
| S6-25 | MPPS → tracking latency: < 5s p95 | QA | 1.0 | S6-07 | — | RIS-SL-22 |
| S6-26 | RLS on tracking | QA | 0.5 | S6-13 | — | PAC-SL-61 |

**Sprint Total:** ~50 dev-days · **Team:** 2 BE + 2 FE + 0.5 INT + 1 QA

---

### Sprint S8–S9 · Reporting + Sign-Off (4 weeks)

**Goal:** Radiologist opens priority-sorted reading list, dictates structured report, signs → auto-distributed to EMR + billing.

| ID | Task | Owner | Est. | Dep | Files Modified/Created | Acceptance |
|:---|:---|:---|:---|:---|:---|:---|
| S8-01 | ALTER TABLE `reports`: add `ris_order_id`, `template_id`, `signed_at`, `signed_by`, `distributed_at`, `is_critical` | BE | 1.0 | — | Alembic migration (v3) | Report fields added |
| S8-02 | Reading list API: priority-sorted, filters, unread, pagination | BE | 2.0 | S6-13 | `api/reports.py` | RIS-AC-P01-01 |
| S8-03 | Reading list UI: priority badges, filters, viewer launch | FE | 4.0 | S8-02 | `frontend/src/radiologist/ReadingWorklist.tsx` | RIS-UI-24 |
| S8-04 | Viewer launch deep-link: StudyInstanceUID → PACS, return preserves state | FE | 2.0 | S8-03 | `frontend/src/radiologist/ReadingWorklist.tsx` | RIS-AC-P01-05 |
| S8-05 | Reading list assignment API | BE | 1.0 | S8-02 | `api/reports.py` | Assignment works |
| S8-06 | `ris_report_templates` table + migration | BE | 1.0 | — | **NEW** `db/ris_templates.py`, migration | Seed 10 templates |
| S8-07 | Report templates API: list by modality, create | BE | 1.5 | S8-06 | `api/reports.py` | RIS-AC-P01-02 |
| S8-08 | Report versioning: versions table, diff, history API | BE | 2.0 | S8-06 | **NEW** `db/ris_report_versions.py` | Every edit attributed |
| S8-09 | Auto-save: debounced async save, no duplicates | BE | 1.5 | S8-08 | `api/reports.py` | RIS-AC-P01-06 |
| S8-10 | Report editor UI: templates, sections, autosave indicator | FE | 5.0 | S8-07 | `frontend/src/radiologist/ReportPanel.tsx` | RIS-UI-25 |
| S8-11 | WIP draft list: restore drafts, no duplicates | FE | 2.0 | S8-09 | `frontend/src/radiologist/ReportPanel.tsx` | RIS-UI-29 |
| S8-12 | Sign & route API: transition SIGNED, audit, ORU stub, charge stub | BE | 2.5 | S8-08 | `api/reports.py` | RIS-AC-P01-04 |
| S8-13 | ORU distribution stub: mock ORU^R01, log, set distributed_at | BE | 1.0 | S8-12 | `api/reports.py` | ORU generated |
| S8-14 | Charge drop stub: placeholder `ris_charges` row | BE | 1.0 | S8-12 | `api/billing.py` | S11-ready |
| S8-15 | Sign dialog UI: completeness warnings, status, routing indicator | FE | 3.0 | S8-12 | `frontend/src/radiologist/ReportPanel.tsx` | RIS-UI-28 |
| S8-16 | Report status indicator: signed status on reading list | FE | 1.5 | S8-15 | `frontend/src/radiologist/ReadingWorklist.tsx` | Status visible |
| S8-17 | Reporting E2E: reading list → template → report → autosave → sign → stubs | QA | 2.5 | S8-01…16 | — | RIS-AC-P01-01/02/04/05/06 |
| S8-18 | Draft preservation E2E: start → close → reopen → restored | QA | 1.0 | S8-09 | — | RIS-AC-P01-06 |
| S8-19 | Report versioning E2E: 3 edits → version history | QA | 1.0 | S8-08 | — | RIS-AC-P01-06 |
| S8-20 | RLS on reports | QA | 0.5 | S8-12 | — | PAC-SL-61 |

**Sprint Total:** ~52 dev-days · **Team:** 2 BE + 2 FE + 0.5 INT + 1 QA

---

### Sprint S10 · Critical Results + Distribution (2 weeks)

**Goal:** Radiologist flags critical finding → ED physician notified immediately → ack tracked → signed report delivered to EMR < 5 min.

| ID | Task | Owner | Est. | Dep | Files Modified/Created | Acceptance |
|:---|:---|:---|:---|:---|:---|:---|
| S10-01 | `ris_critical_results` table + migration | BE | 1.0 | — | **NEW** `db/ris_critical_results.py`, migration | Table created |
| S10-02 | Critical flag API: one-action flag, recipient selection (incl. ED physician) | BE | 2.0 | S8-12 | `api/notifications.py` | RIS-AC-P01-03; ED physician recipient option |
| S10-03 | Acknowledgment API: ack with timestamp | BE | 1.5 | S10-02 | `api/notifications.py` | 100% ack tracked |
| S10-04 | Escalation policy: configurable rules, background check | BE | 2.0 | S10-03 | `services/notification/` | RIS-SL-25 |
| S10-05 | Critical flag in ORU payload: OBX segment carries flag | BE | 1.0 | S10-02, S8-13 | `services/results_distribution/` | ORU carries flag |
| S10-06 | Critical results UI: one-click flag, recipient dialog (incl. ED physician), ack, escalation | FE | 3.0 | S10-02 | **NEW** `frontend/src/radiologist/CriticalResults.tsx` | RIS-UI-27 |
| S10-07 | Critical results list API: all for facility with status | BE | 1.0 | S10-02 | `api/notifications.py` | List works |
| S10-08 | Critical results list UI: persistent badges until ack | FE | 2.0 | S10-07 | `frontend/src/radiologist/CriticalResults.tsx` | RIS-UI-11 |
| S10-09 | ORU distribution engine: signed report → HL7 ORU^R01 → EMR endpoint | BE | 2.5 | S8-13 | **NEW** `services/results_distribution/service.py` | RIS-SL-24 |
| S10-10 | Delivery retry: failed ORU → retry queue, exception handling | BE | 1.5 | S10-09 | `services/results_distribution/service.py` | 0 silent failures |
| S10-11 | Portal/SMS/email notifications: result availability, opt-out honored | INT | 2.0 | S10-09 | `api/notifications.py` | RIS-AC-P08-02 |
| S10-12 | Delivery status API: per-recipient status | BE | 1.0 | S10-09 | `api/reports.py` | Status visible |
| S10-13 | Critical results E2E: flag → notify (incl. ED) → ack → escalate → ack clears | QA | 2.0 | S10-01…08 | — | RIS-AC-P01-03 |
| S10-14 | Distribution E2E: sign → ORU → deliver → retry → notification → opt-out | QA | 2.0 | S10-09…12 | — | RIS-AC-P08-02 |
| S10-15 | RLS on critical results | QA | 0.5 | S10-02 | — | PAC-SL-61 |

**Sprint Total:** ~32 dev-days · **Team:** 2 BE + 1 FE + 0.5 INT + 1 QA

---

### Sprint S11 · Billing Capture (2 weeks)

**Goal:** Signed report auto-generates charge with CPT/ICD-10 suggestion; coder confirms; unbilled aging $0 > 5 days; charge capture ≥ 98%.

| ID | Task | Owner | Est. | Dep | Files Modified/Created | Acceptance |
|:---|:---|:---|:---|:---|:---|:---|
| S11-01 | `ris_charges` table + migration | BE | 1.0 | — | **NEW** `db/ris_charges.py`, migration | Table created |
| S11-02 | CPT/ICD-10 suggestion: procedure → CPT, indication → ICD-10 | BE | 2.0 | S11-01 | `api/billing.py` | RIS-SL-43 |
| S11-03 | Auto charge drop: on sign-off (replacing S8-14 stub) | BE | 2.0 | S8-12, S11-02 | `api/billing.py` | RIS-SL-40 |
| S11-04 | Billing queue API: signed-but-unbilled with suggestions | BE | 1.5 | S11-03 | `api/billing.py` | RIS-UI-30 |
| S11-05 | Charge drop API: coder confirms, status → BILLED | BE | 1.0 | S11-04 | `api/billing.py` | Audited |
| S11-06 | CPT suggestions API | BE | 0.5 | S11-02 | `api/billing.py` | Override works |
| S11-07 | Unbilled aging API: grouped by date/site/payer, $0 > 5d | BE | 2.0 | S11-03 | `api/billing.py` | RIS-SL-41 |
| S11-08 | Unbilled aging dashboard UI | FE | 3.0 | S11-07 | **NEW** `frontend/src/billing/UnbilledAging.tsx` | RIS-UI-31 |
| S11-09 | 837 export stub: charges → JSON claim | INT | 1.5 | S11-05 | `api/billing.py` | Format validated |
| S11-10 | 835 import stub: mock denial → `ris_claims` | INT | 1.0 | S11-09 | `api/billing.py` | Denial record created |
| S11-11 | Billing queue UI: CPT suggestions, confirm, charge drop | FE | 3.0 | S11-04 | **NEW** `frontend/src/billing/BillingQueue.tsx` | RIS-UI-30 |
| S11-12 | Billing E2E: sign → charge → queue → confirm → unbilled = 0 | QA | 2.0 | S11-01…11 | — | RIS-AC-P05-01/03 |
| S11-13 | Reconciliation: 20 signed exams → all have charges | QA | 1.5 | S11-07 | — | RIS-SL-41 |
| S11-14 | Charge capture rate: ≥ 98% | QA | 1.0 | S11-03 | — | RIS-SL-40 |
| S11-15 | RLS on charges | QA | 0.5 | S11-01 | — | PAC-SL-61 |

**Sprint Total:** ~28 dev-days · **Team:** 2 BE + 1 FE + 0.5 INT + 1 QA

---

### Sprint S12 · Hardening + UAT (2 weeks)

**Goal:** G1–G7 all green; full regression; performance under load; security audit; per-persona UAT; MVP releasable.

| ID | Task | Owner | Est. | Dep | Acceptance |
|:---|:---|:---|:---|:---|:---|
| S12-01 | MWL perf: 50 concurrent C-FIND → p95 < 1s | QA | 1.5 | All MWL | RIS-SL-10 |
| S12-02 | Booking perf: 50 concurrent → p95 < 1.5s | QA | 1.0 | All scheduling | RIS-SL-11 |
| S12-03 | Registration perf: screen transitions → p95 < 1s | QA | 0.5 | All registration | RIS-SL-12 |
| S12-04 | Tracking perf: 500 exams, 50 updates → < 30s | QA | 1.0 | All tracking | RIS-SL-15 |
| S12-05 | Worklist perf: 1000 entries filtered → p95 < 1s | QA | 1.0 | All reporting | RIS-SL-13 |
| S12-06 | Report autosave perf: async save → p95 < 1s perceived | QA | 0.5 | All reporting | RIS-SL-14 |
| S12-07 | HL7 throughput: 100 msg/min, 0 failures | QA | 1.0 | All interface | RIS-SL-23 |
| S12-08 | Full RLS regression: all clinical tables | QA | 2.0 | All tables | PAC-SL-61 |
| S12-09 | RBAC regression: every perm vs endpoint | QA | 1.5 | All permissions | RBAC matrix |
| S12-10 | IDOR test: cross-facility ID manipulation | QA | 1.0 | All APIs | 0 IDOR |
| S12-11 | Audit completeness: every write event logged | QA | 1.0 | All triggers | RIS-SL-60 |
| S12-12 | Bug fix sprint: all P0/P1 | BE+FE | 4.0 | — | 0 P0/P1 |
| S12-13 | Full regression: PACS + RIS tests | QA | 2.0 | S12-12 | All green |
| S12-14 | UAT: Radiologist (reading → template → report → sign → critical) | QA | 1.0 | S12-13 | RIS-AC-P01-* |
| S12-15 | UAT: Technologist (MWL → exam → MPPS → tracking) | QA | 1.0 | S12-13 | RIS-AC-P02-* |
| S12-16 | UAT: Scheduler (book → conflict → override → reschedule → cancel) | QA | 1.0 | S12-13 | RIS-AC-P03-* |
| S12-17 | UAT: Front Desk (register → MPI → insurance → check-in) | QA | 1.0 | S12-13 | RIS-AC-P04-* |
| S12-18 | UAT: Billing Coder (queue → CPT → confirm → aging) | QA | 1.0 | S12-13 | RIS-AC-P05-* |
| S12-19 | UAT: RIS Admin (dashboard → exception → retry → roles → audit) | QA | 1.0 | S12-13 | RIS-AC-P06-* |
| S12-20 | UAT: Department Manager (dashboard → TAT → utilization → unbilled) | QA | 1.0 | S12-13 | RIS-AC-P07-01 |
| S12-21 | G1 verify: MWL ≥ 98% | QA | 0.5 | S12-01 | G1 green |
| S12-22 | G2 verify: 0 conflicts | QA | 0.5 | S12-02 | G2 green |
| S12-23 | G3 verify: MPPS < 5s | QA | 0.5 | S12-04 | G3 green |
| S12-24 | G4 verify: charge capture ≥ 98% | QA | 0.5 | S12-18 | G4 green |
| S12-25 | G5 verify: delivery > 99.9% | QA | 0.5 | S12-07 | G5 green |
| S12-26 | G6 verify: provisioning < 15 min | QA | 0.5 | S1-16 | G6 green |
| S12-27 | G7 verify: 0 P0/P1 | QA | 0.5 | S12-12 | G7 green |
| S12-28 | MVP evidence package: G1–G7 report | QA | 1.5 | S12-21…27 | Package complete |
| S12-29 | Cutover runbook + rollback rehearsal | OPS | 1.0 | S12-28 | Rehearsed |
| S12-30 | MVP go/no-go review | QA | 0.5 | S12-28/29 | GO recorded |
| S12-31 | DR drill: backup → restore → verify | OPS | 1.5 | — | RTO ≤ 4h |
| S12-32 | WCAG 2.1 AA audit: all new RIS pages | QA | 1.5 | All UI | WCAG pass |
| S12-33 | TAT metrics: instrument `ris_report_tat_seconds` histogram (by priority: STAT/inpatient/outpatient); wire to Prometheus | BE | 1.5 | S8-12 | `api/telemetry.py` | RIS-SL-30/31/32 trackable |
| S12-34 | Manager Dashboard API: `GET /api/ris/dashboard/kpi` — TAT by priority, utilization, unbilled aging, volume, drill-down support | BE | 2.0 | S12-33 | `api/ris_dashboard.py` | RIS-AC-P07-01 |
| S12-35 | Manager Dashboard UI: `frontend/src/admin/RISDashboard.tsx` — TAT histogram, utilization chart, unbilled aging, export | FE | 3.0 | S12-34 | **NEW** `frontend/src/admin/RISDashboard.tsx` | RIS-UI-42; RIS-AC-P07-01 |

**Sprint Total:** ~36.5 dev-days · **Team:** 2 BE + 2 FE + 0.5 INT + 1 QA

---

## 4. v1.1 Phase — Detailed Sprint Plans

### Sprint R2-S1–S2 · Prior-Auth + Reminders (4 weeks)

**Goal:** Orders needing prior auth tracked and enforced at booking; ≥ 95% authorized pre-scan; reminders reduce no-shows.

| ID | Task | Owner | Est. | Dep | Files Modified/Created | Acceptance |
|:---|:---|:---|:---|:---|:---|:---|
| R2-01-01 | `ris_prior_auth_requests` table + migration | BE | 2.0 | S3-08 | **NEW** `db/ris_prior_auth.py`, migration | Table created |
| R2-01-02 | Prior-auth APIs: create/query/update + expiry | BE | 1.5 | R2-01-01 | `api/prior_auth.py` | `PRIOR_AUTH_*` enforced |
| R2-01-03 | Prior-auth panel UI: status, expiry, CPT, warning badge | FE | 2.5 | R2-01-02 | **NEW** `frontend/src/worklist/PriorAuthPanel.tsx` | RIS-UI-16 |
| R2-01-04 | Live payer/eligibility integration (extend S3-14 stub) | INT | 3.0 | S3-14 | `api/frontdesk.py` | RIS-AC-P04-02 (v2) |
| R2-01-05 | Booking rule: missing/denied/expired blocks; audited override | BE | 2.0 | R2-01-01, S4-10 | `services/scheduling/engine.py` | RIS-AC-P03-03 |
| R2-01-06 | Override UX: reason + confirm | FE | 1.5 | R2-01-05 | `frontend/src/schedule/BookingForm.tsx` | RIS-SL-60 |
| R2-01-07 | Expiry alerts: ≤ 7 days → scheduler alert | BE | 1.0 | R2-01-01 | `api/notifications.py` | RIS-AC-P03-03 |
| R2-01-08 | Prior-auth on claim line | BE | 1.0 | R2-01-01 | `api/billing.py` | RIS-UI-33 |
| R2-01-09 | Prior-auth dashboard: status mix, aging, denial reasons | FE | 2.0 | R2-01-02 | `frontend/src/dashboard/` | Manager view |
| R2-01-10 | Reminder config UI: channel, time, template, opt-out | FE | 2.5 | S4-10 | `frontend/src/schedule/` | RIS-UI-17 |
| R2-01-11 | Provider integrations (SMS/email/phone) + retry | INT | 1.5 | S7-11 | `api/notifications.py` | 0 silent failures |
| R2-01-12 | Opt-out registry honored | BE | 1.5 | R2-01-10 | `api/notifications.py` | RIS-AC-P03-02 |
| R2-01-13 | Send/receipt logging + ≤ 5-min failure alerting | BE | 1.0 | R2-01-11 | `api/notifications.py` | RIS-SL-60 |
| R2-01-14 | E2E: order → auth → book → expiry → override → reminder → opt-out | QA | 2.0 | R2-01-01…13 | — | RIS-AC-P03-02/03 |
| R2-01-15 | Prior-auth ≥ 95% instrumentation | QA | 2.0 | R2-01-09 | — | RIS-SL-36 |

**Sprint Total:** ~27 dev-days · **Team:** 2 BE + 1 FE + 0.5 INT + 0.5 QA

---

### Sprint R2-S3–S4 · Denial + Templates + SR Polish (4 weeks)

**Goal:** Denied claims reworked with reason codes; templates versioned/rollback; dictation accuracy improved.

| ID | Task | Owner | Est. | Dep | Files Modified/Created | Acceptance |
|:---|:---|:---|:---|:---|:---|:---|
| R2-02-01 | 835 denial intake: parse → rework queue | INT | 2.5 | S8-10 | `api/billing.py` | RIS-AC-P05-02 |
| R2-02-02 | Rework queue UI: filters, reason grouping, correction | FE | 2.5 | R2-02-01 | **NEW** `frontend/src/billing/DenialRework.tsx` | RIS-UI-32 |
| R2-02-03 | Correction + resubmission: full history | BE | 2.0 | R2-02-01 | `api/billing.py` | RIS-AC-P05-02 |
| R2-02-04 | Prior-auth linkage on rework rows | BE | 0.5 | R2-01-08 | `api/billing.py` | Claim line parity |
| R2-02-05 | Unbilled aging dashboard (extend S8-08) | FE | 2.0 | S8-07 | `frontend/src/billing/UnbilledAging.tsx` | RIS-SL-41 |
| R2-02-06 | Aging escalation alerts: > 10 days → biller/manager | BE | 1.0 | R2-02-05 | `api/notifications.py` | Alerts wired |
| R2-02-07 | Template versioning model: scheduling + procedure/CPT maps | BE | 2.0 | S4-06 | `db/ris_templates.py` | RIS-AC-P06-03 |
| R2-02-08 | Report template manager UI: tree, history, publish, rollback | FE | 2.5 | R2-02-07 | `frontend/src/admin/` | RIS-UI-36 |
| R2-02-09 | Site-apply + one-click rollback | BE | 1.5 | R2-02-07/08 | `api/reports.py` | RIS-AC-P06-03 |
| R2-02-10 | SR polish: specialty lexicons (MSK, neuro, cardiac) | INT | 1.5 | S6-09 | Integration | Dictation acceptance |
| R2-02-11 | Verification highlight loop polish | FE | 1.0 | S6-09 | `frontend/src/radiologist/ReportPanel.tsx` | RIS-AC-P01-02 |
| R2-02-12 | FHIR DocumentReference export | BE | 1.0 | R2-02-10 | `api/fhir.py` | Smoke test |
| R2-02-13 | E2E: denial → rework → resubmit; template publish → rollback | QA | 2.0 | R2-02-01…09 | — | RIS-AC-P05-02/P06-03 |
| R2-02-14 | Unbilled $0 > 5d instrumentation | QA | 1.0 | R2-02-05 | — | RIS-SL-41 |

**Sprint Total:** ~23 dev-days · **Team:** 2 BE + 1 FE + 0.5 INT + 0.5 QA

---

### Sprint R2-S5–S6 · IDN Grants + Multi-Site Scheduling (4 weeks)

**Goal:** IDN schedulers search across sites; reads authorized via `IDN_SCHEDULE_READ` grants; bookings write home facility only.

| ID | Task | Owner | Est. | Dep | Files Modified/Created | Acceptance |
|:---|:---|:---|:---|:---|:---|:---|
| R2-03-01 | Grants smoke: PACS V2-02 tables live in RIS | INT | 2.0 | PACS V2-02 | `db/user_tenant_grants.py` | CTG-API-01…07 |
| R2-03-02 | `app_cross_accessible_facilities()` reuse in schedule read | BE | 2.0 | R2-03-01 | `api/scheduling.py` | CTG-AC-01/02 |
| R2-03-03 | Per-request facility cache + audit events | BE | 1.5 | R2-03-02 | `api/tenant_middleware.py` | PAC-SL-25 |
| R2-03-04 | Denial path: 0 grants → denied + logged | FE | 1.0 | R2-03-02 | `frontend/src/schedule/` | RIS-SL-61 |
| R2-03-05 | Multi-site availability search + booking (home facility only) | BE+FE | 4.0 | R2-03-02 | `api/scheduling.py`, `frontend/src/schedule/CalendarGrid.tsx` | RIS-AC-P03-04 |
| R2-03-06 | Home-facility write enforcement: `WITH CHECK` | BE | 2.0 | R2-03-05 | `api/scheduling.py` | 0 cross-tenant writes |
| R2-03-07 | Revoked/expired grant → denied + audited | BE+FE | 1.5 | R2-03-04 | `api/scheduling.py` | CTG-AC-03 |
| R2-03-08 | Site chargeback data capture per booking | BE | 1.5 | R2-03-06 | `api/scheduling.py` | RIS-AC-P03-04 |
| R2-03-09 | Per-site SLA preservation | BE | 1.0 | R2-03-05 | `api/telemetry.py` | Site SLAs measured |
| R2-03-10 | RLS regression: home unchanged, cross-tenant writes impossible | QA | 2.0 | R2-03-01…07 | — | PAC-SL-61 |
| R2-03-11 | E2E: grant → search → book → revoke → denied | QA | 2.5 | R2-03-10 | — | CTG-AC-01…07 |

**Sprint Total:** ~21 dev-days · **Team:** 2 BE + 1 FE + 0.5 INT + 0.5 QA

---

### Sprint R2-S7 · FHIR Read + v1.1 Gates (2 weeks)

**Goal:** FHIR read APIs serve Patient/ServiceRequest/DiagnosticReport/ImagingStudy with RLS; RVG-1…RVG-4 all green.

| ID | Task | Owner | Est. | Dep | Files Modified/Created | Acceptance |
|:---|:---|:---|:---|:---|:---|:---|
| R2-04-01 | FHIR read: Patient/ServiceRequest/DiagnosticReport/ImagingStudy + search + pagination | BE | 3.0 | S3-05 | `api/fhir.py` | Conformance smoke |
| R2-04-02 | RLS on all FHIR routes; cross-facility → denied + logged | BE | 2.0 | R2-04-01 | `api/fhir.py` | RIS-SL-61 |
| R2-04-03 | FHIR conformance harness + version pinning | INT | 3.0 | R2-04-01 | Test suite | Suite green |
| R2-04-04 | RVG-1 re-verify: prior-auth ≥ 95% | QA | 2.0 | R2-S1–S2 | — | Gate green |
| R2-04-05 | RVG-2 re-verify: denial + unbilled $0 > 5d | QA | 1.5 | R2-S3–S4 | — | Gate green |
| R2-04-06 | RVG-3 re-verify: IDN + 0 cross-tenant writes | QA | 1.5 | R2-S5–S6 | — | Gate green |
| R2-04-07 | Per-persona UAT: scheduler, biller, admin, radiologist | QA | 2.0 | R2-04-04…06 | — | RVG-4 |
| R2-04-08 | Phase-1 evidence package | QA | 1.0 | R2-04-07 | — | Package complete |

**Sprint Total:** ~16 dev-days · **Team:** 2 BE + 1 FE + 0.5 INT + 1 QA

---

## 5. v2.0 Phase — Detailed Sprint Plans

### Sprint R2-S8–S9 · Full FHIR + Portal (4 weeks)

**Goal:** Full FHIR R4 read/write; patients receive results via portal with consent and audit.

| ID | Task | Owner | Est. | Dep | Files Modified/Created | Acceptance |
|:---|:---|:---|:---|:---|:---|:---|
| R2-05-01 | FHIR writes: ServiceRequest create/update, DiagnosticReport create | BE | 3.0 | R2-04-01 | `api/fhir.py` | Write conformance |
| R2-05-02 | FHIR search coverage + RLS on all routes | BE | 2.0 | R2-05-01 | `api/fhir.py` | Search parity |
| R2-05-03 | Shared conformance tooling with PACS E-V2-10 | INT | 3.0 | R2-05-01 | Test suite | One harness |
| R2-05-04 | Result-availability notifications on sign-off | INT | 2.0 | S7-09 | `api/notifications.py` | RIS-AC-P08-02 |
| R2-05-05 | Release policy (HIM review) | BE | 1.5 | R2-05-04 | `api/reports.py` | Policy enforced |
| R2-05-06 | Secure share links: expiry + revocation | BE | 2.0 | PACS V2-04-02 | `api/files.py` | RIS-SL-60 |
| R2-05-07 | Portal results view: read-only, consent-gated | FE | 3.0 | R2-05-05/06 | `frontend/src/portal/` | Patient-facing live |
| R2-05-08 | Audit: every patient-visible access logged | BE | 0.5 | R2-05-07 | `db/audit_log.py` | RIS-SL-60 |
| R2-05-09 | E2E: sign → notification → release → portal → share → expire | QA | 2.0 | R2-05-01…08 | — | RVG-5 pre-checks |
| R2-05-10 | FHIR write + portal perf under load | QA | 2.0 | R2-05-03/07 | — | p95 green |

**Sprint Total:** ~21 dev-days · **Team:** 2 BE + 1 FE + 0.5 INT + 0.5 QA

---

### Sprint R2-S10–S12 · AI Coding + Chargeback + Hardening (6 weeks)

**Goal:** AI coding pilot ≥ 90% acceptance; chargeback analytics live; V2 go/no-go.

| ID | Task | Owner | Est. | Dep | Files Modified/Created | Acceptance |
|:---|:---|:---|:---|:---|:---|:---|
| R2-06-01 | Coding suggestion service: CPT/ICD-10 from procedure + report | BE+INT | 4.0 | R2-05-01 | `services/coding_suggestion/` | Suggestions confirmable |
| R2-06-02 | Accept/override workflow; every suggestion audited | FE+BE | 2.5 | R2-06-01 | `frontend/src/billing/BillingQueue.tsx` | RIS-SL-60 |
| R2-06-03 | Pilot instrumentation: acceptance/rejection + utility dashboard | QA | 2.0 | R2-06-01 | — | ≥ 90% measurable |
| R2-06-04 | Per-site chargeback aggregation from bookings | BE | 2.0 | R2-03-08 | `api/scheduling.py` | Chargeback reconciles |
| R2-06-05 | Manager dashboard: chargeback, denial rate, unbilled by site | FE | 2.5 | R2-06-04 | `frontend/src/dashboard/` | RIS-P07 parity |
| R2-06-06 | Pre-registration: portal data visible before arrival | FE+BE | 2.0 | R2-05-07 | `frontend/src/frontdesk/` | RIS-UI-23 |
| R2-06-07 | One-click completion at check-in | FE | 1.0 | R2-06-06 | `frontend/src/frontdesk/` | Check-in pre-fill |
| R2-06-08 | Full perf suite: FHIR, scheduling, portal | QA | 1.5 | All v2 code | — | p95 green |
| R2-06-09 | Security test: RLS, RBAC, IDOR, SMART token | QA | 1.5 | R2-06-02 | — | 0 critical/high |
| R2-06-10 | RVG-5 re-verify: full FHIR + portal + pre-reg | QA | 1.0 | R2-S8–S9 | — | Gate green |
| R2-06-11 | AI 30-day pilot gate: ≥ 90% acceptance | QA | 1.5 | R2-06-03 | — | Gate decision |
| R2-06-12 | RVG-6 re-verify: charge ≥ 98%, unbilled $0 > 5d | QA | 1.0 | R2-06-04/05 | — | Gate green |
| R2-06-13 | Per-persona UAT: biller, manager, scheduler, front desk | QA | 2.0 | R2-06-10…12 | — | UAT sign-off |
| R2-06-14 | V2 evidence package: RVG-5…6 report | QA | 1.0 | R2-06-13 | — | Package complete |
| R2-06-15 | Cutover runbook + rollback rehearsal | OPS | 1.0 | R2-06-14 | — | Rehearsed |
| R2-06-16 | V2 go/no-go review | QA | 0.5 | R2-06-14/15 | — | GO recorded |

**Sprint Total:** ~27 dev-days · **Team:** 2 BE + 1 FE + 0.5 INT + 1 QA + 0.5 OPS

---

## 6. Program Totals

| Phase | Sprints | Duration | Dev-days | Team |
|:---| :-: | :--- | :-: | :--- |
| MVP (S1–S12) | 12 | ~6 months | ~316 | 2 BE + 2 FE + 0.5 INT + 1 QA |
| v1.1 (R2-S1–S7) | 7 | ~3.5 months | ~114 | 2 BE + 1 FE + 0.5 INT + 0.5 QA |
| v2.0 (R2-S8–S12) | 5 | ~2.5 months | ~48 | 2 BE + 1 FE + 0.5 INT + 1 QA |
| **Total** | **24** | **~12 months** | **~478** | — |

### Dependency Chain (Critical Path)

```
S1-2 (Platform) ──────────────────────────────────────────────────────────┐
  │                                                                       │
  └──► S3 (Interface) ──► S4-5 (Scheduling) ──► S6-7 (MWL/MPPS/Tracking) │
                                                       │                  │
                           S8-9 (Reporting) ◀──────────┘                  │
                                │                                         │
                           S10 (Critical+Dist) ◀──────────────────────────┘
                                │
                           S11 (Billing)
                                │
                           S12 (Hardening)
                                │
                           R2-S1-2 (Prior-Auth+Reminders)
                                │
                           R2-S3-4 (Denial+Templates)
                                │
                           R2-S5-6 (IDN Grants) ──► R2-S7 (FHIR Read)
                                                        │
                                                   R2-S8-9 (Full FHIR+Portal)
                                                        │
                                                   R2-S10-12 (AI+Chargeback)
```

### Key Milestones

| Milestone | Sprint | Date (est.) | Gate |
|:---|:---|:---|:---|
| Platform green | S2 | Week 4 | — |
| First HL7 order | S3 | Week 6 | — |
| Conflict-free booking | S5 | Week 10 | G2 |
| Scanner pulls MWL | S6 | Week 12 | G1 |
| MPPS → tracking live | S7 | Week 14 | G3 |
| Report sign → distribute | S9 | Week 18 | — |
| Critical results loop | S10 | Week 20 | — |
| Auto charge drop | S11 | Week 22 | G4, G5 |
| **MVP RELEASABLE** | **S12** | **Week 24** | **G1–G7** |
| Prior-auth ≥ 95% | R2-S2 | Week 28 | RVG-1 |
| Unbilled $0 > 5d | R2-S4 | Week 32 | RVG-2 |
| IDN grants live | R2-S6 | Week 36 | RVG-3 |
| FHIR read green | R2-S7 | Week 38 | RVG-4 |
| **v1.1 RELEASABLE** | **R2-S7** | **Week 38** | **RVG-1…4** |
| Portal results live | R2-S9 | Week 42 | RVG-5 |
| **v2.0 RELEASABLE** | **R2-S12** | **Week 50** | **RVG-6** |
