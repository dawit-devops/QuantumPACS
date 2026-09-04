# Sprint Plan Conformance Report — vs. Master Spec & Interview Decisions

**Date:** 2026-08-18  
**Documents validated:** `CONSOLIDATED_SPRINT_PLAN.md` vs. `ris-integration-spec.md` + interview decisions  
**Method:** Section-by-section cross-reference of every spec requirement against sprint plan tasks

---

## 1. Interview Decisions Compliance

| Decision | Spec Reference | Sprint Plan Status | Notes |
|:---|:---|:---|:---|
| **Consolidated full plan** (MVP + v1.1 + v2.0) | §1.2, §9 | ✅ | 24 sprints covered (S1–S12 + R2-S1–R2-S12) |
| **Replace + extend** existing modules | §1.3 | ✅ | 24 existing files to modify, 30 new files to create |
| **All 11 human + 6 machine actors** | §7.2 | ✅ | All personas in role-permission matrix |
| **Evolve existing schema** | §3.1 | ✅ | ALTER TABLE for worklist_entries, exams, reports; new tables alongside |
| **New HL7 interface engine** | §2.2, §5.5 | ✅ | S3: `services/hl7_engine/` with queue, parse, route, retry |
| **New scheduling engine** (EXCLUDE) | §2.2, §5.2 | ✅ | S4: `services/scheduling/engine.py` + EXCLUDE constraint |
| **New MWL SCP + MPPS consumer** | §2.2, §5.3/5.4 | ✅ | S6: `services/mwl_scp/` + `services/mpps_consumer/` |
| **Extend existing worklist** to tracking | §1.3, §6.2 | ✅ | S6: TrackingBoard.tsx extends Worklist.tsx |
| **Dictation only** (no AI coding for v3) | §1.2 | ✅ | Speech recognition deferred to v1.1; AI coding in v2.0 |
| **Extend existing billing** | §1.3 | ✅ | S11: CPT suggestion, auto charge drop, unbilled aging |
| **IDN from the start** | §1.2 | ⚠️ | S1 includes `app_cross_accessible_facilities()` reuse; full IDN in R2-S5–S6 |
| **Full SRE plan** (SLAs + metrics + alerts) | §10 | ✅ | S12: perf tests; spec §10.4: 11 Prometheus metrics; §10.5: 4 alert rules |
| **Per-phase branches** | — | ✅ | Implied by sprint structure (MVP, v1.1, v2.0 phases) |
| **PRD + Engineering spec merged** | §1–11 | ✅ | Spec covers both product and engineering |
| **Full DDL + API contracts** | §3.2, §4.1 | ✅ | 6 migrations in spec; 50+ endpoints defined |
| **Order status + child statuses** | §3.1, §4.3 | ✅ | `ris_orders.status` lifecycle; worklist/exams/reports have sub-statuses |

**Result: 15/16 decisions fully compliant, 1 partial (IDN — by design, full in v1.1)**

---

## 2. Spec Section Conformance

### §2 Architecture

| Spec Requirement | Sprint Plan Task | Status |
|:---|:---|:---|
| HL7 Interface Engine at `services/hl7_engine/` | S3-01/02/03 | ✅ |
| MWL SCP at `services/mwl_scp/` | S5-01/02 | ✅ |
| MPPS Consumer at `services/mpps_consumer/` | S5-06 | ✅ |
| Scheduling Engine at `services/scheduling/` | S4-10 | ✅ |
| Order Lifecycle at `services/order_lifecycle/` | S3-09 | ✅ |
| Prior-Auth Engine at `services/prior_auth/` | R2-01-05 | ✅ |
| Results Distribution at `services/results_distribution/` | S7-09 | ✅ |
| Enhanced `api/worklist.py` | S5-03/05/11/13 | ✅ |
| Enhanced `api/exams.py` | — | ⚠️ **Gap**: no explicit task to modify `api/exams.py` for MPPS status linkage |
| Enhanced `api/reports.py` | S6-06/07/08/11 | ✅ |
| Enhanced `api/billing.py` | S8-02/03/04/05 | ✅ |
| Enhanced `api/frontdesk.py` | S3-10/14 | ✅ |
| Enhanced `api/hl7.py` → route to engine | S3-01 (implicit) | ⚠️ **Gap**: no explicit task to modify `api/hl7.py` routing |
| Enhanced `api/notifications.py` | S7-02/03/04 | ✅ |

### §3 Data Model (6 Migrations)

| Migration | Spec §3.2 | Sprint Plan Task | Status |
|:---|:---|:---|:---|
| v1: `ris_orders`, `ris_order_procedures`, `ris_appointments`, `ris_resources`, `ris_resource_schedules` | ✅ DDL defined | S3-06/07, S4-06/09 | ✅ |
| v2: ALTER `worklist_entries`, `ris_mpps_events` | ✅ DDL defined | S5-07 (MPPS only) | ⚠️ **Gap**: ALTER TABLE worklist_entries tasks not explicit (should be in S5 with MWL) |
| v3: ALTER `reports`, `ris_report_versions`, `ris_report_templates`, `ris_critical_results` | ✅ DDL defined | S6-05/07, S7-01 | ⚠️ **Gap**: ALTER TABLE reports tasks not explicit |
| v4: `ris_charges`, `ris_claims` | ✅ DDL defined | S8-01 | ✅ |
| v5: `ris_interface_endpoints`, `ris_hl7_messages`, `ris_interface_events` | ✅ DDL defined | S3-03/06 | ✅ |
| v6: `ris_prior_auth_requests` | ✅ DDL defined | R2-01-01 | ✅ |

### §4 API Contracts (50+ Endpoints)

| Endpoint Group | Spec §4.1 | Sprint Plan Coverage | Status |
|:---|:---|:---|:---|
| Orders (7 endpoints) | ✅ | S3-06/08/09, S4-01/02/03/04/05 | ✅ |
| Scheduling (8 endpoints) | ✅ | S4-07/10/11 | ✅ |
| Tracking Board (4 endpoints) | ✅ | S5-11/12/13/14 | ✅ |
| Registration (6 endpoints) | ✅ | S3-10/11/14 | ✅ |
| Reading Worklist & Reports (8 endpoints) | ✅ | S6-01/04/06/08/11 | ✅ |
| Critical Results (4 endpoints) | ✅ | S7-02/03/07 | ✅ |
| Billing (6 endpoints) | ✅ | S8-02/04/05/06/07 | ✅ |
| Prior-Auth (4 endpoints) | ✅ | R2-01-02 | ✅ |
| Interface Engine (5 endpoints) | ✅ | S3-15 | ✅ |
| Reports reading-list (2 endpoints) | ✅ | S6-01/04 | ✅ |

### §5 Service Layer

| Service | Spec §5 | Sprint Plan | Status |
|:---|:---|:---|:---|
| `OrderLifecycleService.transition()` | §5.1 | S3-09 | ✅ |
| `SchedulingEngine.book()` | §5.2 | S4-10 | ✅ |
| `MwlScpService.handle_c_find()` | §5.3 | S5-01 | ✅ |
| `MppsConsumerService.handle_n_create/set()` | §5.4 | S5-06 | ✅ |
| `Hl7InterfaceEngine.receive_message()` | §5.5 | S3-01 | ✅ |
| `PriorAuthEngine.check_booking_eligibility()` | §5.6 | R2-01-05 | ✅ |

### §6 Frontend Components

| New Component | Spec §6.1 | Sprint Plan | Status |
|:---|:---|:---|:---|
| `TrackingBoard.tsx` | ✅ | S5-15 | ✅ |
| `TrackingBoard.css` | ✅ | S5-15 | ✅ |
| `KpiStrip.tsx` | ✅ | S5-16 | ✅ |
| `CalendarGrid.tsx` | ✅ | S4-14 | ✅ |
| `BookingForm.tsx` | ✅ | S4-15 | ✅ |
| `ResourceManager.tsx` | ✅ | S4-08 | ✅ |
| `OrderIntake.tsx` | ✅ | — | ❌ **Gap**: not in sprint plan (order creation is HL7-driven, no manual form needed) |
| `PriorAuthPanel.tsx` | ✅ | R2-01-03 | ✅ |
| `CriticalResults.tsx` | ✅ | S7-06 | ✅ |
| `ReportEditor.tsx` | ✅ | — | ⚠️ Covered by ReportPanel.tsx enhancement (S6-09) |
| `BillingQueue.tsx` | ✅ | S8-11 | ✅ |
| `DenialRework.tsx` | ✅ | R2-02-02 | ✅ |
| `InterfaceDashboard.tsx` | ✅ | S3-16 | ✅ |
| `ExceptionQueue.tsx` | ✅ | — | ⚠️ Implicit in S3-16 (dashboard includes exception queue) |

| Enhanced Component | Spec §6.2 | Sprint Plan | Status |
|:---|:---|:---|:---|
| `Worklist.tsx` → Tracking Board | ✅ | S5-15 (new TrackingBoard.tsx) | ✅ |
| `ReadingWorklist.tsx` | ✅ | S6-02/03 | ✅ |
| `ReportPanel.tsx` | ✅ | S6-09/10/14 | ✅ |
| `CreateEntry.tsx` → OrderIntake | ✅ | — | ⚠️ See OrderIntake gap above |
| `CalendarView.tsx` | ✅ | S4-16 | ✅ |

### §7 RBAC Permissions

| Requirement | Spec §7 | Sprint Plan | Status |
|:---|:---|:---|:---|
| 18 new Permission enum values | §7.1 | S1-03 | ✅ |
| 11 roles with permission mappings | §7.2 | S1-03/23/24 | ✅ |

### §8 Integration Contracts

| Requirement | Spec §8 | Sprint Plan | Status |
|:---|:---|:---|:---|
| HL7 ADT^A04/A08/A40, ORM^O01, ORU^R01 | §8.1 | S3-01/02/12, S7-09 | ✅ |
| MWL SCP port 11113, AE `QPACS_MWL` | §8.2 | S5-01 | ✅ |
| MPPS Consumer port 11114, AE `QPACS_MPPS` | §8.2 | S5-06 | ✅ |
| FHIR ServiceRequest/DiagnosticReport | §8.3 | R2-04-01, R2-05-01 | ✅ |

### §9 Implementation Phases

| Spec Phase | Sprint Plan | Status |
|:---|:---|:---|
| MVP S1–S12 (12 epics) | ✅ All 12 sprints | ✅ |
| v1.1 R2-S1–R2-S7 (7 sprints) | ✅ All 7 sprints | ✅ |
| v2.0 R2-S8–R2-S12 (5 sprints) | ✅ All 5 sprints | ✅ |
| MVP Exit Gates G1–G7 | S9-18…24 | ✅ |
| v1.1 Exit Gates RVG-1…4 | R2-04-04…07 | ✅ |
| v2.0 Exit Gates RVG-5…6 | R2-06-10…12 | ✅ |

### §10 SLAs & SRE Plan

| SLA | Spec §10 | Sprint Plan | Status |
|:---|:---|:---|:---|
| MWL < 1s p95 (RIS-SL-10) | §10.1 | S9-01 | ✅ |
| Booking < 1.5s p95 (RIS-SL-11) | §10.1 | S9-02 | ✅ |
| Registration < 1s p95 (RIS-SL-12) | §10.1 | — | ⚠️ Not explicitly tested in S12 |
| Worklist < 1s p95 (RIS-SL-13) | §10.1 | S9-04 | ✅ |
| Report autosave < 1s (RIS-SL-14) | §10.1 | — | ⚠️ Not explicitly tested in S12 |
| Tracking ≤ 30s (RIS-SL-15) | §10.1 | S9-03 | ✅ |
| Order < 1 min (RIS-SL-20) | §10.2 | S3-18 | ✅ |
| MPPS < 5s (RIS-SL-22) | §10.2 | S5-22 | ✅ |
| Interface > 99.9% (RIS-SL-23) | §10.2 | S9-05 | ✅ |
| Report → EMR < 5 min (RIS-SL-24) | §10.2 | S7-14 | ✅ |
| Critical ack 100% (RIS-SL-25) | §10.2 | S7-13 | ✅ |
| STAT TAT < 30–60 min (RIS-SL-30) | §10.4 | — | ❌ **Gap**: no TAT metric instrumented |
| Inpatient TAT < 2–4h (RIS-SL-31) | §10.4 | — | ❌ **Gap**: same |
| Outpatient TAT 24–48h (RIS-SL-32) | §10.4 | — | ❌ **Gap**: same |
| MWL ≥ 98% (RIS-SL-33) | §10.4 | S9-18 | ✅ |
| Conflicts = 0 (RIS-SL-34) | §10.4 | S9-19 | ✅ |
| Prior-auth ≥ 95% (RIS-SL-36) | §10.4 | R2-01-15 | ✅ |
| Dup MRN < 1% (RIS-SL-37) | §10.4 | S3-19 | ✅ |
| Charge ≥ 98% (RIS-SL-40) | §10.4 | S9-21 | ✅ |
| Unbilled $0 > 5d (RIS-SL-41) | §10.4 | S8-13 | ✅ |
| Coding ≥ 95% (RIS-SL-43) | §10.4 | S8-12 | ✅ |
| Charge drop < 24h (RIS-SL-44) | §10.4 | — | ⚠️ Instrumented in spec §10.4 but no explicit perf test |
| Metering 100% (RIS-SL-50) | §10.4 | S2-04 | ✅ |
| Provisioning < 15 min (RIS-SL-51) | §10.4 | S9-23 | ✅ |
| Audit 100% (RIS-SL-60) | §10.4 | S9-09 | ✅ |
| Isolation 0 incidents (RIS-SL-61) | §10.4 | S9-06 | ✅ |

### §11 Testing Strategy

| Test Type | Spec §11 | Sprint Plan | Status |
|:---|:---|:---|:---|
| Unit tests (pytest) | §11.1 | Engineering DoD per sprint | ✅ |
| Integration tests | §11.1 | E2E tasks per sprint | ✅ |
| E2E tests | §11.1 | S3-18/19, S4-18/19, S5-20/21, S6-16/17/18, S7-13/14, S8-12/13 | ✅ |
| Conformance tests (DICOM) | §11.1 | S5-04/09 | ✅ |
| RLS tests | §11.1 | S1-11, S2-05, S3-20, S4-21, S5-23, S6-19, S7-15, S8-15, S9-06 | ✅ |
| Component tests (Vitest) | §11.2 | Implicit in Engineering DoD | ✅ |
| E2E (Playwright) | §11.2 | QA tasks per sprint | ✅ |
| Accessibility (axe) | §11.2 | S9-29 | ✅ |

---

## 3. Identified Conformance Gaps

### Gap A — Task ID Numbering Error (Critical)
**Impact:** Confusion during implementation  
**Details:** Sprint S6–S7 tasks are labeled `S5-xx` instead of `S6-xx`. This cascades: S8–S9 = `S6-xx`, S10 = `S7-xx`, S11 = `S8-xx`. The numbering is internally consistent but misleading relative to the sprint names.  
**Fix:** Renumber all tasks to match sprint numbers: S6-xx for S6–S7, S8-xx for S8–S9, etc.

### Gap B — `api/exams.py` Not Modified (Medium)
**Impact:** MPPS status not linked to exams  
**Details:** Spec §2.3 says `api/exams.py` gets "Add MPPS status linkage, protocol assignment, dose tracking" but no sprint task modifies it.  
**Fix:** Add task to S6 to update `api/exams.py` with MPPS-driven status updates.

### Gap C — `api/hl7.py` Routing Not Explicit (Medium)
**Impact:** Existing HL7 receiver doesn't route to new engine  
**Details:** Spec §2.3 says `api/hl7.py` should "Route to new interface engine instead of inline processing" but no sprint task modifies it.  
**Fix:** Add task to S3 to modify `api/hl7.py` to route to `services/hl7_engine/`.

### Gap D — ALTER TABLE worklist_entries Not Explicit (Medium)
**Impact:** MWL fields not added to existing table  
**Details:** Spec §3.2 Migration v2 defines ALTER TABLE commands for `worklist_entries` (add `ris_order_id`, `station_ae`, `priority`, `mpps_status`, etc.) but no sprint task explicitly creates this migration.  
**Fix:** Add migration task to S6 (MWL sprint) for the ALTER TABLE worklist_entries statements.

### Gap E — ALTER TABLE reports Not Explicit (Medium)
**Impact:** Report fields not added  
**Details:** Spec §3.2 Migration v3 defines ALTER TABLE for `reports` (add `ris_order_id`, `template_id`, `signed_at`, `signed_by`, `distributed_at`, `is_critical`) but no sprint task creates this migration.  
**Fix:** Add migration task to S8 (Reporting sprint) for the ALTER TABLE reports statements.

### Gap F — Manager Dashboard Missing (High — from Validation Report GAP #1)
**Impact:** M-priority story RIS-US-P07-01 with no tasks  
**Details:** Spec §6.3 lists `/dashboard` route and `RISDashboard` component, but no sprint creates the dashboard API or component.  
**Fix:** Add `GET /api/ris/dashboard/kpi` endpoint and `RISDashboard.tsx` component to S12 or a new task in S6.

### Gap G — STAT End-to-End Prioritization (Medium — from Validation Report GAP #2)
**Impact:** M-priority story RIS-US-P09-01 not fully verified  
**Details:** STAT priority exists in order model but MWL serves by date, not priority. No task sorts MWL by priority.  
**Fix:** Add priority-based MWL sort to S5-02 and STAT E2E test to S9.

### Gap H — ED Physician Recipient (Low — from Validation Report GAP #3)
**Impact:** Critical results recipient selection doesn't include ED physician  
**Details:** Spec §7.2 lists ED Physician with `CRITICAL_RESULTS_READ` but S7-06 (recipient dialog) doesn't explicitly add ED physician as an option.  
**Fix:** Add ED physician to recipient options in S7-06.

### Gap I — Registration SLA Not Tested (Low)
**Impact:** RIS-SL-12 not verified  
**Details:** Spec §10.1 defines registration < 1s p95 but S12 has no explicit registration perf test.  
**Fix:** Add registration perf test to S9.

### Gap J — Report Autosave SLA Not Tested (Low)
**Impact:** RIS-SL-14 not verified  
**Details:** Spec §10.1 defines report autosave < 1s but S12 has no explicit test.  
**Fix:** Add autosave perf test to S9.

### Gap K — Report TAT Metrics Not Instrumented (Medium — from Validation Report GAP #9)
**Impact:** RIS-SL-30/31/32 not tracked  
**Details:** Spec §10.4 does NOT include `ris_report_tat_seconds` histogram (identified in validation report). TAT SLAs exist but have no metric.  
**Fix:** Add `ris_report_tat_seconds` histogram to spec §10.4 and instrumentation task to S6 or S12.

### Gap L — `OrderIntake.tsx` Not Created (Low)
**Impact:** Spec §6.1 lists component but no sprint creates it  
**Details:** Order creation is HL7-driven (no manual form needed), so this component may be unnecessary.  
**Fix:** Remove from spec §6.1 or document as deprecated (HL7-driven intake replaces manual form).

---

## 4. Summary

| Category | Total Items | ✅ Compliant | ⚠️ Partial | ❌ Gap |
|:---| :-: | :-: | :-: | :-: |
| Interview Decisions (16) | 16 | 15 | 1 | 0 |
| Architecture (§2) | 14 | 12 | 2 | 0 |
| Data Model (§3) | 6 migrations | 4 | 2 | 0 |
| API Contracts (§4) | 10 groups | 10 | 0 | 0 |
| Service Layer (§5) | 6 services | 6 | 0 | 0 |
| Frontend (§6) | 19 components | 15 | 3 | 1 |
| RBAC (§7) | 2 items | 2 | 0 | 0 |
| Integration (§8) | 4 items | 4 | 0 | 0 |
| Phases (§9) | 6 items | 6 | 0 | 0 |
| SLAs (§10) | 25 metrics | 20 | 3 | 2 |
| Testing (§11) | 8 types | 8 | 0 | 0 |
| **Total** | **106** | **92** | **12** | **3** |

**Conformance: 92/106 = 87% fully compliant, 12 partial, 3 gaps**

---

## 5. Recommended Fixes (Priority Order)

| Priority | Gap | Fix | Sprint |
|:---|:---|:---|:---|
| **P0** | A — Task ID renumbering | Renumber S5-xx → S6-xx, S6-xx → S8-xx, S7-xx → S10, S8-xx → S11 | All |
| **P1** | F — Manager Dashboard | Add `GET /api/ris/dashboard/kpi` + `RISDashboard.tsx` | S12 |
| **P1** | B — `api/exams.py` | Add MPPS status linkage task | S6 |
| **P1** | C — `api/hl7.py` routing | Add routing task to interface engine | S3 |
| **P1** | D — ALTER worklist_entries | Add migration task for ALTER TABLE | S6 |
| **P1** | E — ALTER reports | Add migration task for ALTER TABLE | S8 |
| **P2** | G — STAT prioritization | Add priority MWL sort + STAT E2E | S5, S12 |
| **P2** | K — TAT metrics | Add `ris_report_tat_seconds` to spec + instrumentation | S6 or S12 |
| **P3** | H — ED physician recipient | Add to recipient options | S10 |
| **P3** | I — Registration SLA test | Add perf test | S12 |
| **P3** | J — Autosave SLA test | Add perf test | S12 |
| **P3** | L — OrderIntake.tsx | Remove from spec or mark deprecated | Spec |
