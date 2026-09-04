# S5–S10 RIS Implementation Review Report

**Branch:** `feature/ris-integration` · **HEAD:** `eee9b20` · **Date:** 2026-08-20
**Scope:** MVP sprints S4–S10 per [`CONSOLIDATED_SPRINT_PLAN.md`](CONSOLIDATED_SPRINT_PLAN.md):

- S4–S5 Scheduling Engine (E-RIS-04/05, exit gate G2)
- S6–S7 MWL/MPPS + Tracking Board (E-RIS-06/07, gates G1/G3)
- S8–S9 Reporting + Sign-Off (E-RIS-08)
- S10 Critical Results + Distribution (E-RIS-09/10)

**Reviewed:** 114 plan tasks · ~11k backend LOC · ~28k frontend LOC · migrations 066–072 · 25 test files. Four parallel review streams (scheduling, MWL/MPPS/tracking, reporting/critical, frontend) + manual verification of all Critical findings against source.

**Verdict:** Approximately 70% of S4–S8 surface is implemented with solid foundations. S10 is largely **not delivered** (flag UI unreachable, distribution/escalation engines dead code). Three block-level defects break core flows (tracking status 500s, MPPS never completes exams, signed reports editable). RLS acceptance tests (S4-21, S8-20, S10-15) are not implemented — xfail or vacuous.

---

## 1. Task Coverage Matrix

### S4–S5 · Scheduling Engine (22 tasks)

| Task | Status | Evidence |
|---|---|---|
| S4-01 Order search API | ✅ | `api/ris_orders.py:64-97`, `db/ris_orders.py:93-137` |
| S4-02 Order detail API | ⚠️ Partial — no appointments in response | `ris_orders.py:100-112` |
| S4-03 Status transition API | ✅ audited, 422 on invalid | `ris_orders.py:139-158`, `services/order_lifecycle/service.py:34-53` |
| S4-04 Status history API | ⚠️ Partial — details dropped (B-3) | `ris_orders.py:115-136` |
| S4-05 Referring-MD view | ⚠️ Filter only, no identity scoping | `ris_orders.py:80` |
| S4-06 `ris_resources` + schedules | ✅ | `068_ris_resources.py`, `db/ris_resources.py` |
| S4-07 Resource API | ✅ | `api/scheduling.py:39-104` |
| S4-09 Appointments + EXCLUDE + GiST | ✅ real-DB proven | `069_ris_appointments.py:35-67` |
| S4-10 Scheduling engine | ✅ (contraindication gate unplumbed) | `services/scheduling/engine.py:79-220` |
| S4-11 Reschedule/cancel API | ⚠️ Slot-release bugs (B-1, B-5, B-6) | `engine.py:228-280` |
| S4-12 Override flow | ✅ mandatory reason + audit | `engine.py:150-165` |
| S4-13 Appointment → worklist | ⚠️ Duplicate MWL entries on override; stale on cancel | `engine.py:197-219` |
| S4-18/19 E2E | ✅ | `tests/integration/test_ris_scheduling_e2e.py`, `test_ris_e2e.py` |
| S4-20 EXCLUDE stress test | ⚠️ Bypasses engine (raw repo inserts) | `test_scheduling_concurrency.py:54-113` |
| S4-21 RLS | ❌ **Not implemented** (xfail tests) | `test_scheduling_concurrency.py:230-302` |

### S6–S7 · MWL/MPPS + Tracking (26 tasks)

| Task | Status | Evidence |
|---|---|---|
| S6-01 MWL SCP AE 11113 | ⚠️ Dedicated AE dormant (`dicom_mwl_port` empty); MWL rides main C-STORE AE | `lifecycle.py:61-78,135-137,160-162`, `config.py:63` |
| S6-02 MWL filters + STAT sort | ✅ with caveats (M-7) | `dcm/server.py:169-192`, `db/worklist.py:194-205` |
| S6-03 Station AE endpoint | ✅ | `api/worklist.py:147-152` |
| S6-04 MWL conformance | ⚠️ Unit-mocked only; parity test targets dcm4chee | `test_mwl_handler.py`, `tests/integration/test_mwl_cfind_parity.py` |
| S6-05 MWL REST filters | ⚠️ No `priority` filter exposed | `api/worklist.py` |
| S6-06 ALTER worklist_entries | ❌ **Missing** — no `ris_order_id`/`mpps_status`/`body_part`/`contrast` | `060_mwl_sync_columns.py` (MWL-RS only) |
| S6-07 MPPS consumer | ⚠️ Wrong DICOM element (CR-2), tenant bypass (CR-3) | `services/mpps_consumer/service.py` |
| S6-08 `ris_mpps_events` | ✅ table; ❌ no read path | `070_ris_mpps_events.py` |
| S6-09 PACS echo | ❌ **Missing** | — |
| S6-10 MPPS conformance | ❌ MagicMock only | `test_mpps_consumer.py` |
| S6-11 MPPS latency histogram | ❌ **Missing** | `api/telemetry.py:117-124` |
| S6-12 exams.py linkage | ⚠️ Linkage in consumer, not `api/exams.py`; no protocol assignment | `service.py:66-75,137-153` |
| S6-13 Tracking board API | ⚠️ Status CHECK mismatch (CR-1) | `api/worklist.py:169-246` |
| S6-14 KPI strip API | ✅ (definitional gaps, L-4) | `api/worklist.py:249-287` |
| S6-15 Status update guard | ⚠️ Writes illegal statuses (CR-1) | `api/worklist.py:309-367` |
| S6-16 Status timeline | ⚠️ MPPS transitions never in audit_log | `api/worklist.py:290-305` |
| S6-22/24/25/26 E2E/latency/RLS | ⚠️ Mocked or vacuous; latency unmeasured | `test_mwl_mpps_e2e.py` |
| S6-23 STAT E2E | ❌ Missing | — |

### S8–S9 · Reporting + Sign-Off (20 tasks)

| Task | Status | Evidence |
|---|---|---|
| S8-01 ALTER reports | ✅ | `071_ris_reporting_tables.py:29-42` |
| S8-02 Reading list API | ⚠️ No pagination, no unread concept | `api/reports.py:109-159` |
| S8-05 Assignment API | ✅ | `api/reports.py:162-195` |
| S8-06 Templates + seed 10 | ⚠️ **Seed never runs in prod** | `db/ris_templates.py:168-175` (tests only) |
| S8-07 Templates API | ⚠️ Lists empty table; POST unvalidated | `api/reports.py:545-565` |
| S8-08 Versioning | ⚠️ All edits attributed to creator (V-1) | `db/reports.py:105-113` |
| S8-09 Autosave | ⚠️ Client-only dedup (V-4) | `ReadingConsole.tsx:155-249` |
| S8-12 Sign & route | ✅ (charge stub double-fired, V-3) | `api/reports.py:288-362` |
| S8-13 ORU stub | ✅ stub; real engine unwired | `api/reports.py:321-335` |
| S8-14 Charge drop stub | ⚠️ Called twice per sign; runtime DDL | `api/billing.py:39-59` |
| S8-17/18/19 E2E | ⚠️ DB-level only, no API tests | `test_reporting_s8.py` |
| S8-20 RLS on reports | ❌ **No `tenant_id` column on `reports`** | `db/reports.py:245-259` |

### S10 · Critical Results + Distribution (15 tasks)

| Task | Status | Evidence |
|---|---|---|
| S10-01 `ris_critical_results` | ✅ | `072_ris_critical_results.py` |
| S10-02 Critical flag API | ⚠️ ED recipient cosmetic (CR-7) | `api/notifications.py:120-159` |
| S10-03 Ack API | ⚠️ Any user can ack; no audit | `api/notifications.py:162-174` |
| S10-04 Escalation | ❌ **Dead code — never wired** | `services/notification/escalation.py` |
| S10-05 ORU OBX flag | ⚠️ Code exists, engine unreachable; `is_critical` not settable via API | `services/results_distribution/service.py:27-34` |
| S10-06 Flag UI | ❌ **Unreachable** — no route/nav/mount + broken submit (CR-5/6) | `CriticalResults.tsx` |
| S10-07 List API | ✅ tenant-filtered | `api/notifications.py:123-132` |
| S10-08 Badges | ⚠️ ReadingWorklist only; not on tracking board | `ReadingWorklist.tsx:197-207` |
| S10-09 ORU engine | ❌ **Dead code** — no network I/O; `SENT` fabricated | `services/results_distribution/service.py` |
| S10-10 Delivery retry | ❌ No-op — nothing ever `FAILED` | `service.py:79-94` |
| S10-11 SMS/email/portal | ❌ **Not implemented**; events absent from `EVENT_CATALOG` | `db/notification_prefs.py:32-46` |
| S10-12 Delivery status API | ❌ 500 — table created only by never-run engine | `api/notifications.py:177-189` |
| S10-13/14 E2E | ⚠️ Unit-level only | `test_critical_results_s10.py` |
| S10-15 RLS | ⚠️ ack/escalate unscoped; vacuous test | `db/ris_critical_results.py:116-126` |

---

## 2. Critical Findings (8)

**CR-1 (S6) Tracking status updates guaranteed 500.** `TRACKING_VALID_TRANSITIONS` allows `arrived`/`completed` (`api/worklist.py:309-315`) but the `worklist_entries.status` CHECK only permits `scheduled/in_progress/performed/cancelled` (`db/worklist.py:52-53`, migration `042`). Every check-in/complete on the board raises `CheckViolationError`. Tests mask it with mocked `conn.execute` (`test_tracking_api.py:219-232`).

**CR-2 (S6) MPPS reads the wrong DICOM element.** `_extract_sps_status` reads `ScheduledProcedureStepSequence[0].ScheduledProcedureStepStatus` (`service.py:171-176`); MPPS status is `PerformedProcedureStepSequence[0].PerformedProcedureStepStatus` (0040,0252). N-SET COMPLETED never maps to `performed` → exams never complete. Tests encode the same wrong element (`test_mpps_consumer.py:28-31`).

**CR-3 (S6) MPPS consumer bypasses tenant scoping.** `handle_n_create/n_set` (`dcm/server.py:386-416`) never call `tenant_db_scope`/`_tenant_scope_for_ae`, unlike C-FIND (`:159,196`) and C-STORE. Events land on the main pool, stamped `tenant_id='default'` (`get_tenant_slug()` is `''` on DICOM threads). Multi-tenant AEs get `0xA700`.

**CR-4 (S8) Signed/final reports silently editable; `REPORT_SIGN` bypassable.** PUT rejects only `submitted` (`api/reports.py:246-285`); a `final` report can be reverted to `preliminary` (frontend actively sends `preliminary` for finals: `ReadingConsole.tsx:206`). Any `REPORT_WRITE` holder can set `status='final'` via the draft endpoint, bypassing the sign gate (`:291`), impression check (`:304-307`), and `signed_by` stamping (`api/schemas/reports.py:14`).

**CR-5 (FE) Critical-flag submit always fails.** `request()` JSON-stringifies only `options.data` (`api/client.ts:164-178`), but `CriticalResults.tsx:68` sends `body:` → `TypeError` on every flag. Test never submits (`CriticalResults.test.tsx` renders only).

**CR-6 (S10) Critical-results UI unreachable.** No route in `index.tsx`, no nav item in `Sidebar.tsx`, no flag button in `ReadingConsole.tsx`; component imported only by its test.

**CR-7 (S10) "ED physician" recipient is cosmetic.** Frontend sends only `recipient_role`/`recipient_name` (`CriticalResults.tsx:75-76`); backend `notify_role('radiologist')` fallback fires for any selection (`api/notifications.py:144-158`). `ed_physician` role exists in RBAC but is never notified.

**CR-8 (S10) Distribution + escalation engines are dead code.** `ResultsDistributionEngine` and `CriticalEscalationEngine` are imported nowhere in production; sign path fabricates `SENT` audit event with no transmission (`api/reports.py:321-335`); `DeliveryStatusHandler` queries `ris_results_distribution`, a table only the never-run engine's runtime `CREATE TABLE IF NOT EXISTS` creates → 500.

---

## 3. High Findings (12)

1. **S4** — All scheduling audit events `actor='system'` (`api/scheduling.py:100,133,155,170`), defeating S4-11/12 "audited" acceptance and HIPAA accountability.
2. **S4** — Engine race → uncaught `ExclusionViolationError` → 500 instead of 409 (`api/scheduling.py:142,161`).
3. **S4** — No transaction around override delete+insert: data-loss window if insert fails after delete commits (`engine.py:160-161`).
4. **S4** — Reschedule rejects slots held by CANCELLED rows while calendar shows them free (`engine.py:247-254` vs `:296`).
5. **S4** — Worklist entries not synced: override duplicates, reschedule stale, cancel never marks cancelled (B-5).
6. **S6** — S6-06 columns entirely missing (H-3).
7. **S6** — MPPS transitions never in `audit_log` → timeline (S6-16) broken (H-2).
8. **S6** — S6-09 PACS echo + S6-11 latency histogram absent (H-4).
9. **S8** — `ris_report_templates` never seeded in prod; parallel legacy template system (CR-4).
10. **S8** — Version history attributes every edit to report creator (`edited_by` dropped) (V-1).
11. **S10** — No SMS/email/portal delivery; `critical.*` events missing from `EVENT_CATALOG` → opt-out impossible (B-3).
12. **S10** — Ack endpoint: any `REPORT_READ` user can ack anyone's finding, overwriting prior state (S-3, V-2).
13. **FE** — Sign & Next shows previous patient's report under new exam URL; no seq guard in `useExamImaging` (H-1); autosave loses keystrokes on Back/unmount (H-3).
14. **S10** — Delivery-status endpoint exposes full ORU payload (PHI) to any `REPORT_READ` holder (S-4).

---

## 4. Medium Findings (representative)

- **S4**: 500s on missing resources/orders (B-7), malformed datetimes (B-8), missing `resource_id` (B-2); order history drops `from/to/reason` and booking events (B-3/B-4); referring-MD filter not identity-scoped (S-4); no FK `appointments.order_id → ris_orders` (C-4); prior-auth `EXPIRED` not blocked (C-7); UTC-only day window (B-10).
- **S6**: wrong DIMSE status `0xA700` for unknown accession (M-1); non-transactional consumer writes (M-2); N-CREATE regresses terminal states (M-3); no read path for MPPS events (M-4); unguarded AE thread entrypoints (M-5); UUID used as MediaStorageSOPInstanceUID (M-6); MWL matching diverges from DICOM (M-7); 1000-row C-FIND + 30s block (M-8); concurrent status-update race (M-9); duplicated transition maps (M-10).
- **S8**: duplicate `ris_charges` rows per sign (V-3); version snapshot on every PUT (V-4); `%` unescaped in search (S-6); assignment accepts any user id (S-7); escalation query unscoped (V-5); `Reports.create` drops template/order linkage (V-6).
- **S10**: flag POST validates nothing (S-8); retry logic no-op (B-6); version diff 500 on non-numeric (B-7).
- **FE**: TrackingBoard pagination resets to page 1 (M-2); no staleness guard (M-1); unnamed icon-only buttons (M-4); unlabeled textareas (M-5); KPI failures silently swallowed (M-8); no critical column on board — S6-21 unmet (M-3); 4 duplicated STATUS_COLORS maps (M-6); day semantics diverge between boards (M-7); BookingFormModal Enter-only (M-9); monolith components >300 lines (M-10).

---

## 5. RLS / Multi-Tenancy Status (acceptance gaps)

- **Zero** `ENABLE ROW LEVEL SECURITY`/`CREATE POLICY` statements in the repo. Isolation relies on per-tenant DB pool separation (`db/conn.py`).
- S4-21: xfail; S8-20: no `tenant_id` on `reports` at all; S10-15: ack/escalate unscoped; S6-26: `hasattr` assert. All four exit-gate acceptance tests are not met; none may ship as green.

---

## 6. What Is Done Well

- EXCLUDE + GiST double-book prevention is real and DB-proven (50-concurrent test) — though it bypasses the engine.
- Calendar/booking UI: UTC anchoring, stale-fetch guards, 409 handling, Enter+Space keyboard support, `ScheduleCalendar.test.tsx` (643 lines) is genuinely strong.
- Reading-list priority sort (critical→STAT/urgent→FIFO); autosave interval with refs (no stale closures); sign confirmation + impression checks + audit.
- Consistent permission gating on all new HTTP endpoints; association-policy hardening on MWL/MPPS AEs.
- Migrations 066–072 idempotent; `ScheduleDayNav`/`boardSlots.ts` good extractions.

---

## 7. Recommended Remediation Plan (phased)

**Phase 1 — Blockers (ship-blocking):**
1. Tracking status CHECK mismatch: migration adding `arrived`/`completed` (and align consumer `performed` mapping) or map guard targets to existing statuses.
2. MPPS: read `PerformedProcedureStepStatus`; add real DIMSE conformance test.
3. Tenant-scope MPPS consumer via `tenant_db_scope` + AE→slug resolution.
4. Reports PUT: reject edits to `final`; remove `final` from `SaveReportRequest.status`; enforce `REPORT_SIGN` re-sign path.
5. FE: `body:`→`data:`; mount FlagCriticalModal + route/nav; send `recipient_id` with user picker.

**Phase 2 — S10 delivery:** wire distribution + escalation engines into `lifecycle.py` (real ORU build/HTTP or explicit stub w/ config flag); migration for `ris_results_distribution`; `critical.*` in `EVENT_CATALOG`; ack identity enforcement; PHI-scope delivery-status.

**Phase 3 — S4/S6 correctness:** transactional engine ops + `ExclusionViolationError`→409; real `actor_id`; S6-06 columns migration; worklist sync on reschedule/cancel; audit events for MPPS transitions; S6-09 echo + S6-11 histogram.

**Phase 4 — Tests & RLS:** replace xfail/isinstance RLS tests with real cross-tenant asserts; API-level tests for sign/critical endpoints; concurrency test through `SchedulingEngine.book()`; S6-23/24/25 tests.

---

## 8. Appendix — Review Method

Four parallel review streams, one per sprint area (S4–S5 scheduling backend, S6–S7 MWL/MPPS/tracking, S8–S10 reporting/critical/distribution, S4–S10 frontend), each producing a task-ID→evidence coverage map and severity-rated findings; followed by manual source verification of all Critical findings (all confirmed). Tests were not executed; findings are static-analysis based unless noted.