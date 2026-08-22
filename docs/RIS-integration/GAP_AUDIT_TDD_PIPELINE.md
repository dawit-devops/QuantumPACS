# Gap-Audit Remediation TDD Pipeline — Refined Implementation Plan

**Date:** 2026-08-22
**Source:** Full-sprint gap audit vs [`CONSOLIDATED_SPRINT_PLAN.md`](CONSOLIDATED_SPRINT_PLAN.md) · [`S11 S12 Re Review Audit.md`](S11%20S12%20Re%20Review%20Audit.md) · [`V2_1_SPRINT_COMPLETION.md`](V2_1_SPRINT_COMPLETION.md) · platform-inheritance diff vs `origin/v3-dev`
**Pattern:** Vertical-slice TDD (RED → GREEN → REFACTOR), one test → one fix per cycle.
**Branch:** `feature/ris-integration` (merges to `v3-dev`; PACS + integrated RIS ship as ONE platform)
**Scope decision (user-approved):** Phases A–F complete · legacy stub-charge data-fix migration included · real MPPS-forward SCU (C3).

---

## 0. Execution Status

| Phase | State | Commit | Verification |
|---|---|---|---|
| **A** P0 defect kills (A1, A1b, A2, A3, A4) | ✅ DONE | `363e26c` | Full suite 2357 passed / 2 skipped; migrations 086+087 applied |
| **B** Interface-engine substance (B1, B2, B3) | ✅ DONE | `9eb8f3f` | Full suite 2365 passed (+1 live-MLLP load-flake passing in isolation); integration pkg 276 green |
| **C** Scheduling/MWL/MPPS coherence (C1–C5) | ⬜ pending | — | — |
| **D** Reporting/billing/platform (D1–D7) | ⬜ pending | — | — |
| **E** FHIR/portal v2.0 (E1–E3) | ⬜ pending | — | — |
| **F** Honest gate evidence (F1–F4) | ⬜ pending | — | — |

---

## 0. Ground Rules

### 0.1 Test discipline (why this pipeline exists)

The S11/S12 re-review proved CI blind spots: `test_ris_billing.py` asserted SQL substrings against `_Conn` mocks while **C-1 (auto charge-drop dead code) shipped green**. Therefore:

- Any cycle touching sign→charge→claim/ORU/check-in chains uses **real-DB fixtures** (`TestDenialChainRealDb` pattern in `backend/tests/test_ris_billing_rework.py`).
- No new SQL-string-mock tests. Mocks allowed only at transport boundaries (HTTP endpoints, DICOM associations, SMTP/Twilio adapters).
- Every cycle: failing test committed first or same commit as fix (conventional commits: `test(ris): …` then `fix(ris)/feat(ris): …`).

### 0.2 Platform-inheritance rules (do NOT duplicate v3-dev capabilities)

When this branch merges, the platform already provides — verified on `origin/v3-dev` @ `4796f09`:

| Capability | Inherit via | Rule |
|---|---|---|
| Tenant isolation | `api/tenant_middleware.py` pools + `tenant_id` tag cols | Never add literal Postgres RLS/facility_id policies; isolation tests assert pool/tag behavior |
| Audit logging | `db/audit_log.py` shared `logs` table | All new events via `AuditLog.log_event`; no new tables |
| Metering | `db/metering.py` + `TenantMiddleware.record_request` | `/ris/*` API_CALLS ride middleware; only domain counters added |
| Notifications fan-out | `api/notify.py` + `db/notification_prefs.py` | New alerts reuse `notify_role/user`; SMS/email remain adapter stubs until provider chosen |
| Share links | `api/files.py`, `db/share_files.py` | Extend release-policy checks there; no parallel share mechanism |
| Rate limiting primitives | `api/ratelimit.py` `TokenBucket`/`RedisTokenBucket` | D5 wraps these in app middleware; do not fork a second limiter |
| Provisioning | `db/tenant_provisioner.py` | RIS defaults plug into `provision()` hooks |
| Permission catalog UI | `api/permissions.py PERMISSION_GROUPS` → `frontend/src/roles/` | New perms = enum value + group entry; zero FE work |
| FHIR substrate | `api/fhir.py` CapabilityStatement, `tests/integration/test_fhir.py` | E3 extracts shared harness both suites import |
| HL7/DICOM services | `services/ingestion/hl7_server.py`, `dcm/server.py`, lifecycle daemon threads | New handlers register into existing registries |

### 0.3 Deliberate non-builds (documented deferrals)

- Literal Postgres RLS / `facility_id` policies — pool+tag substitution stands (documented in `066_ris_orders.py:12-17`).
- `services/coding_suggestion/` AI module — static `ris_coding_map` + Prometheus acceptance counters satisfy pilot instrumentation; R2-06-11 decides after 30-day data.
- Real SMS/email providers — channel interfaces exist (`services/reminders/service.py`); provider selection is a procurement decision.
- Platform-wide multi-site chargeback rollup — needs cross-tenant aggregation design; servicing-side view ships (R2-06-04).
- X12 validators for 837/835 — JSON stubs until clearinghouse chosen; payload-schema validation added in D3 only.

---

## 1. Phase Overview (dependency-ordered)

| Phase | Focus | Cycles | Effort | Depends on | Ship-gate |
|---|---|---|---|---|---|
| **A** | P0 correctness defects | A1–A4b | ~2d | — | **Yes** |
| **B** | Interface-engine substance | B1–B3 | ~3d | A | — |
| **C** | Scheduling/MWL/MPPS coherence | C1–C5 | ~5d | A | — |
| **D** | Reporting/billing/platform extensions | D1–D7 | ~5d | A | — |
| **E** | FHIR/portal v2.0 (security prereqs) | E1–E3 | ~4d | D5 | unblocks R2-06-09 |
| **F** | Honest gate evidence | F1–F4 | ~4d | A–E | RVG/UAT package |

B/C/D are mutually independent once A lands and may run as parallel streams with exclusive file ownership:
B owns `services/hl7_engine/`, `services/ingestion/hl7_server.py`, `tests/test_hl7_*`;
C owns `services/scheduling/`, `services/mpps_consumer/`, `frontend/src/schedule/`, `frontend/src/worklist/TrackingBoard*`;
D owns `db/reports.py` consumers, `db/ris_charges.py`, `api/billing.py`, `api/ratelimit*`, `lifecycle.py` (coordinate with B's worker additions), `frontend/src/billing/`.

---

## 2. Phase A — P0 Defect Kills

### Cycle A1: Auto charge-drop shadowed by legacy stub
**Evidence:** `db/reports.py:134-164` calls `drop_charge_stub` inside `sign()`; enriched `drop_charge` (`api/reports.py:409-427`) then no-ops on its `NOT EXISTS(report_id)` guard → bare $0 charges, wrong tenant, G4 fails.
**RED:** `backend/tests/test_ris_billing.py` — new class `TestChargeDropRealDb`: sign a report (real DB fixture) → assert exactly **one** `ris_charges` row; fields `cpt_code`/`icd10_code` resolved from procedure map, `patient_id`/`patient_name` populated, `tenant_id == requesting tenant slug` (not `'default'`), `charge_amount > 0`.
**GREEN:** Remove the `drop_charge_stub` invocation block from `Reports.sign()` (version-add stays). Delete `drop_charge_stub` from `api/billing.py` after `grep -rn drop_charge_stub backend/` confirms no other callers. Enriched path keeps its guard.
**REFACTOR:** Single idempotency owner = `drop_charge`.

### Cycle A1b: Legacy stub-row data fix (migration 086)
**RED:** Migration test: apply on DB seeded by 077 fixtures → 17 legacy coding-less PENDING rows become `VOID`; unbilled-aging query returns 0 for them; down-migration restores.
**GREEN:** `migrations/versions/086_void_legacy_stub_charges.py` — extend `ris_charges.status` CHECK with `'VOID'` (if absent), `UPDATE ris_charges SET status='VOID' WHERE cpt_code IS NULL AND charge_amount = 0 AND status='PENDING'`; verify partial index predicate still matches intent (unbilled = PENDING only).
**REFACTOR:** none.

### Cycle A2: ORU first-send fake success + unscheduled retry
**Evidence:** `services/results_distribution/service.py:66-70` records `SENT` without transmitting; `_deliver()` unused on first send; `retry_failed_deliveries` has no scheduler outside tests; inline `CREATE TABLE IF NOT EXISTS` duplicates migration 074.
**RED:**
1. `tests/test_results_distribution.py` — inject failing transport: `distribute_report()` → row status `FAILED` with error text; succeeding transport → `SENT` **only after** `_deliver` returns True.
2. Lifecycle test — `lifecycle.setup()` starts retry loop; FAILED row + passing transport → flipped `SENT` within interval.
**GREEN:** `distribute_report()` awaits `_deliver()` and records outcome accordingly; register retry worker thread in `lifecycle.py` beside the escalation/reminders workers (interval from `default_config`, e.g. `results_retry_interval_seconds: 60`). Route persistence through the migration-074 schema via a small `db/ris_results_distribution.py` module (drop inline DDL).
**REFACTOR:** transport becomes constructor-injectable (protocol class) so prod HTTP and tests share code paths.

### Cycle A3: Template publish/rollback SQL error (missing tenant_id)
**Evidence:** `db/ris_templates.py:212-218` UPDATE filters `tenant_id=$4`; `ris_report_templates` (migration 071) has no such column → runtime failure on migrated DBs.
**RED:** Real-DB test: `publish_version()` succeeds; `rollback_version()` restores content; tenant B cannot publish/pull tenant A's templates.
**GREEN:** Migration `087_template_tenant_scope.py` — `ALTER TABLE ris_report_templates ADD COLUMN tenant_id text NOT NULL DEFAULT 'default'` + index; backfill seeds stay `'default'`; keep the existing filter (now valid). Seed routine stamps creator tenant.
**REFACTOR:** `db/ris_templates.py` reads/writes tenant consistently (list filtered, admin override documented).

### Cycle A4: HIM hold not enforced in portal/share flows
**Evidence:** Only FHIR DR search checks `release_status` (`api/fhir.py:974`); `db/portal.py:93-105` lists any `final` report; share flow never consults it → held reports patient-visible.
**RED:**
1. Portal test: report held (`release_status='held'`) → absent from list, GET → 404, audit event `report.hold_blocked`.
2. Share test: minting a share for held report → 409; direct access to pre-existing share of now-held report → 404 at fetch time.
**GREEN:** Centralize `_assert_releasable(report_row)` in `db/reports.py` (released OR policy `auto`); call from `db/portal.py` list/get and `api/files.py` share mint + access paths; blocked attempts emit audit events (reuse `AuditLog`).
**REFACTOR:** FHIR search switches to the same helper (single source).

**Phase A exit gate**

```bash
cd backend && .venv/bin/python -m pytest tests/test_ris_billing.py tests/test_ris_billing_rework.py \
  tests/test_results_distribution.py tests/test_reporting_s8.py tests/test_portal_api.py -v --tb=short
cd backend && .venv/bin/python -m pytest tests/ -q --tb=short   # full suite green
cd backend && .venv/bin/python -m alembic upgrade head          # 086+087 idempotent on fresh DB
```

Commits: `fix(billing): kill charge-drop shadow…` · `feat(billing): void legacy stub charges (migration 086)` · `fix(distribution): transmit ORU on first send + schedule retries` · `fix(templates): tenant-scope ris_report_templates (migration 087)` · `fix(portal): enforce HIM release policy across portal and shares`

---

## 3. Phase B — Interface Engine Substance

### Cycle B1: Multi-OBR ORM collapses procedures
**Evidence:** `services/ingestion/hl7_server.py:209` dict-comprehension overwrites duplicate OBR segments; `_handle_orm` creates exactly one procedure (`hl7_engine/service.py:231`); REST path supports multiples.
**RED:** Corpus test — ORM message with 3 OBR segments → order created with **3** `ris_order_procedures` rows (accession idempotent, single order row).
**GREEN:** Parser collects OBR blocks into a list (`parse_hl7_message` return shape gains `procedures[]`, backward-compatible key); `_handle_orm` loops `RisOrderProcedures.create`.
**REFACTOR:** Conformance corpus (`tests/hl7_conformance_corpus.py`) gains multi-OBR sample; ≥95% parse assertion unchanged.

### Cycle B2: PV1/DG1 unparsed
**Evidence:** `parse_hl7_message` extracts MSH/PID/MRG/ORC/OBR only; `parser.py:4` docstring overstates coverage.
**RED:** Unit tests — PV1 attending doctor (PV1-7), patient class (PV1-2), visit number (PV1-19); DG1 list (code/description) present in `parsed_segments`; ADT upsert persists visit number.
**GREEN:** Extend parser extraction; store DG1 diagnoses on order meta (ORM) and patient encounter context (ADT); fix docstring.
**REFACTOR:** Shared segment-extraction helpers to stop positional-index repetition.

### Cycle B3: ADT merge propagation is shallow
**Evidence:** A40/A06 sets `meta.merged_into` + deactivates loser only (`hl7_server.py:302-307, 409-434`); orders/appointments/worklist keep stale patient refs — plan acceptance "Merges propagate".
**RED:** Real-DB test — create order + appointment under patient L; send A40 (L→S survivor) → order/appointment queries resolve under S; loser deactivated; audit event includes re-pointed row counts.
**GREEN:** Inside `_merge_patients` transaction: `UPDATE ris_orders/appointments/worklist_entries SET patient_id=survivor WHERE patient_id=loser` (tables per actual FK columns — verify during GREEN), then metadata marker as today.
**REFACTOR:** none expected.

**Phase B exit gate**

```bash
cd backend && .venv/bin/python -m pytest tests/test_hl7_engine.py tests/test_hl7_conformance.py \
  tests/test_ris_mpi.py tests/test_ris_orders.py -v --tb=short
```

Commits: `feat(hl7): multi-OBR ORM orders` · `feat(hl7): PV1/DG1 parsing` · `fix(hl7): propagate merges across RIS references`

---

## 4. Phase C — Scheduling / MWL / MPPS Coherence

### Cycle C1: Booked MWL entries lack station_ae_title
**Evidence:** `services/scheduling/engine.py:284-299` never stamps resource identity → station-scoped C-FIND misses booked entries (plan ≥98% auto-fill at risk).
**RED:** Real-DB test — book appointment on resource "CT1" → C-FIND with `ScheduledStationAE='CT1'` (via `dcm/server.py handle_find_async`) returns the entry; reschedule to CT2 moves it.
**GREEN:** Stamp `station_ae_title` from the resource (name/AE field — reconcile with `ris_resources` columns during GREEN) in entry creation and reschedule move.
**REFACTOR:** Resource↔AE mapping helper shared with ResourceManager UI validation.

### Cycle C2: Dead columns mpps_status/body_part/contrast
**Evidence:** Migration 075 added them; zero writers (`grep` clean); tracking board can't show MPPS state from the column.
**RED:** Consumer tests — N-CREATE writes `mpps_status='IN_PROGRESS'`, N-SET terminal states; `body_part`/`contrast` populated from linked order procedure when available; tracking API response exposes `mpps_status`.
**GREEN:** `services/mpps_consumer/service.py` extends its existing UPDATE statements; join order procedures for body part/contrast when resolvable.
**REFACTOR:** Column constants shared between consumer and tracking query.

### Cycle C3: PACS echo = connectivity ping (replace with MPPS forward SCU)
**Evidence:** `services/pacs_echo/service.py:18-56` fires C-ECHO only — no study/exam status reaches PACS (S6-09 substance missing). User-approved: build real forward.
**RED:** Test spins a local pynetdicom SCP accepting N-CREATE/N-SET → after consumer processes N-CREATE/N-SET with forwarding enabled, the remote AE received both operations with matching accession/PPS status; forwarding failure logs warning + counter bump, never raises, local state unaffected; disabled config → no association attempted.
**GREEN:** New `services/mpps_forward/service.py` — SCU sending the original N-CREATE/N-SET datasets to configured peer; config keys in `default_config`: `mpps_forward_enabled: false`, `mpps_forward_host/port/called_ae`; hook after local persist in consumer (fire-and-forget with timeout, mirrors `pacs_echo` guard rails). Add `dicom_mpps_port` to `default_config` while touching config (drift fix).
**REFACTOR:** Retire `services/pacs_echo/` if nothing else consumes it (check callers first).

### Cycle C4: Booking form gaps + override_reason never sent
**Evidence:** `BookingFormModal.tsx` lacks procedure/priority pickers and warnings; `override_reason` field exists in `frontend/src/api/scheduling.ts:45` but is never sent — conflicts just toast (R2-01-06 UX unmet); day view lacks priority badges.
**RED (vitest):**
1. Render modal with an order carrying 2 procedures → both selectable; selected procedure submitted.
2. Priority radio (STAT/urgent/routine) reflected in payload.
3. Backend conflict response → modal shows warning panel with "Override" action → confirmation prompt sends `override_reason` (assert request body).
4. CalendarView day blocks render priority badge from appointment payload.
**GREEN:** Wire pickers to existing APIs (resource schedules, order detail); send `override_reason` on explicit confirm; badge component reused from TrackingBoard.
**REFACTOR:** Extract shared `PriorityBadge` into `frontend/src/common/`.

### Cycle C5: Tracking board filter/action parity
**Evidence:** Board exposes modality/status/search only (`TrackingBoard.tsx:330-380`); plan wants site/room/priority/date filters + reassign/reschedule row actions (S6-19/S6-20); backend already accepts priority/date params? verify and extend `api/worklist.py TrackingHandler` minimally.
**RED (vitest + pytest):** Filters populate and refine results (mocked API asserting query params); row menu shows Reassign/Reschedule gated by `SCHEDULE_WRITE` → opens RescheduleModal prefilled with the entry's appointment; pytest: tracking endpoint honors `priority`/`date_from/date_to`/`room` params.
**GREEN:** Add filter controls (Select/DatePicker) + actions wired to scheduling endpoints; backend param support where missing.
**REFACTOR:** Filter bar extracted for reuse.

**Phase C exit gate**

```bash
cd backend && .venv/bin/python -m pytest tests/test_scheduling_engine.py tests/test_mpps_consumer.py \
  tests/test_mwl_mpps_conformance.py tests/test_ris_scheduling_api.py -v --tb=short
cd frontend && npx tsc --noEmit && npx vitest run src/test/TrackingBoard.test.tsx src/schedule/
```

Commits: `feat(scheduling): stamp station AE on MWL entries` · `feat(mpps): persist mpps_status/body_part/contrast` · `feat(mpps): MPPS-forward SCU to PACS (config-gated)` · `feat(schedule-fe): booking form pickers + override reason` · `feat(tracking-fe): full filter/action parity`

---

## 5. Phase D — Reporting / Billing / Platform Extensions

### Cycle D1: Reading-list pagination
**Evidence:** `db/reports.py:277` fetch-all → S12-05 perf risk.
**RED:** >25 signed reports → list returns page 1 (default 25) with total count; `_offset` navigates; sort stable across pages.
**GREEN:** `_count/_offset` params through `db/reports.py` list query (mirror FHIR paging conventions); FE ReadingWorklist pagination control.
**REFACTOR:** none.

### Cycle D2: Unbilled aging site/payer grouping
**Evidence:** Grouped by date only (`db/ris_charges.py:120-150`); FE already expects `facility_name`/`payer_name` (see stale mock note in `test_ris_billing.py:317-320`) — align API to the UI contract.
**RED:** Real-DB: charges across two sites + a claim with payer → aging rows carry `site`/`payer` dimensions; date buckets intact; gauges expose per-site totals.
**GREEN:** Join chain charge→order→appointment(resource/site) and charge→claims(payer) in the aging query; extend gauge labels conservatively (cardinality-safe).
**REFACTOR:** Aging query builder extracted for testability.

### Cycle D3: Denial-rework UX + orphaned prior_auth_id
**Evidence:** UI flat table without filters/grouping (`DenialRework.tsx`); claim submit passes only `(charge_id, claim_number, tenant_id)` (`billing.py:972-973`); `ris_charges.prior_auth_id` written nowhere.
**RED (vitest):** Status/date filters refine table; rows grouped under denial-code headers; correction drawer unchanged. **RED (pytest):** claim submit persists `prior_auth_id` when charge carries one; charge drop populates `prior_auth_id` from an approved prior-auth joined through the order's appointments.
**GREEN:** UI filter bar + grouping; API signature gains optional `prior_auth_id`; `drop_charge` resolves linkage via single JOIN.
**REFACTOR:** Claim-submit payload validated against a Pydantic schema (fold in the 837-stub payload check deferred from §0.3).

### Cycle D4: Escalation policy configurable
**Evidence:** SLA hardcoded 15 min and target hardcoded `'radiologist'` (`services/notification/escalation.py:13-14`) contradicting recipient-role design (072 defaults `ed_physician`).
**RED:** Defaults apply when config absent; overriding `critical_escalation_sla_minutes` / `critical_escalation_target_role` changes worker behavior within one tick; invalid config → logged + defaults (fail-safe).
**GREEN:** Keys in `default_config`; worker reads each tick; alert text names the configured target.
**REFACTOR:** none.

### Cycle D5: App-level rate limiting for RIS surface (platform seam, not forks)
**Evidence:** `ratelimit.py` is login-only; nothing wires budgets into `app.py:253-265` middleware stack (S1-04 unmet).
**RED:** Middleware tests — burst beyond budget on `/api/v2/ris/*` → 429 with `Retry-After`; same burst on non-RIS route → untouched; login limiter behavior unchanged; per-tenant isolation of buckets.
**GREEN:** `api/ratelimit_middleware.py` wrapping existing `TokenBucket`/`RedisTokenBucket` primitives; mounted in `app.py` for `/api/v2/ris` prefix; budgets from `default_config` (`ris_rate_limit_per_minute`, per-class overrides keyed by permission group); exempt: kiosk `/api/v2/ris/checkin/*` (own tight token-bucket instead).
**REFACTOR:** ADR-031 documenting placement + bucket taxonomy.

### Cycle D6: Provisioner RIS defaults + rollback hygiene
**Evidence:** No default-data seeding (resources/templates) beyond schema; rollback marks decommissioned but leaves artifacts; rollback path untested.
**RED:** Provision test — READY tenant contains seeded default resources + report templates; forced migration failure → registry decommissioned AND partial DB cleaned (or documented retention) ; no orphan rows in registry.
**GREEN:** `provision()` gains RIS seeding hook (idempotent inserts after migrations, before active); `_mark_failed` extended with cleanup step; tests cover both paths.
**REFACTOR:** Seeding functions live beside `db/ris_resources.seed_defaults` / `db/ris_templates` seeders, invoked by provisioner only.

### Cycle D7: ed_physician missing from runtime roles
**Evidence:** Seeded in migrations (`052_trim_builtin_roles.py:56,144`) but absent from runtime `BUILT_IN_ROLES` (`api/permissions.py:386-402`) → cannot assign via UI.
**RED:** Roles-catalog test asserts `ed_physician` present with CRITICAL_RESULTS_* grants.
**GREEN:** Add to dict + canonical grant list; catalog/UI inherit automatically (platform rule §0.2).
**REFACTOR:** none.

**Phase D exit gate**

```bash
cd backend && .venv/bin/python -m pytest tests/test_ris_dashboard.py tests/test_ris_billing.py \
  tests/test_tenant_provisioner.py tests/test_ratelimit_middleware.py tests/test_roles_catalog.py -v --tb=short
cd frontend && npx tsc --noEmit && npx vitest run src/billing/ src/radiologist/
```

Commits: `feat(reports): paginate reading list` · `feat(billing): aging by site+payer` · `feat(billing): denial filters + prior-auth linkage` · `feat(critical): configurable escalation policy` · `feat(platform): rate-limit middleware for RIS surface (ADR-031)` · `feat(provisioner): RIS defaults + rollback cleanup` · `fix(rbac): register ed_physician at runtime`

---

## 6. Phase E — FHIR / Portal v2.0 (R2-06-09 prerequisites)

### Cycle E1: Portal consent gating
**Evidence:** Zero consent model in portal path (R2-05-07 acceptance).
**RED:** Patient without consent → portal list/get empty + audit `portal.consent_blocked`; consent granted (audited) → visible; withdrawal revokes future access.
**GREEN:** `patients.meta.consent_results` boolean (JSONB meta — avoids migration if column-free pattern exists; else migration 088) + toggle in Registration UI (REGISTRATION_WRITE); enforcement in `db/portal.py`; every check audited.
**REFACTOR:** Consent read helper shared by share-link path.

### Cycle E2: SMART-on-FHIR scopes
**Evidence:** No SMART/OAuth scope handling anywhere (`api/fhir.py`, auth, tokens) — required before security sweep R2-06-09.
**RED:** Token without `smart_scopes` → FHIR writes 403 (reads allowed, current behavior); token with `patient/Patient.read` only → ServiceRequest read 403; matching scope passes; scopes appear in CapabilityStatement security section.
**GREEN:** `create_token` accepts `smart_scopes=[...]` (flat claim); FHIR middleware maps resource+operation → required scope string; enforcement ahead of handlers; issuance via OAuth authorize param (read-only initial set: Patient/ServiceRequest/DiagnosticReport read).
**REFACTOR:** ADR-032 recording scope grammar + rollout stance.

### Cycle E3: Shared FHIR conformance harness
**Evidence:** RIS suite standalone-mocked (`test_fhir_ris_read.py:_make_app`); plan R2-05-03 wants one harness with PACS `tests/integration/test_fhir.py`.
**RED/GREEN:** Refactor test-infrastructure cycle — extract `backend/tests/fhir_harness.py` (client factory, CapabilityStatement assertions, Bundle paging helpers, scope-token helper from E2); both suites import it; combined run green; count duplicated assertions removed.
**REFACTOR:** Harness registered in test README/docs.

**Phase E exit gate**

```bash
cd backend && .venv/bin/python -m pytest tests/test_fhir_ris_read.py tests/integration/test_fhir.py \
  tests/test_portal_api.py -v --tb=short
```

Commits: `feat(portal): results consent gating` · `feat(fhir): SMART scopes enforcement` · `test(fhir): shared conformance harness`

---

## 7. Phase F — Honest Gate Evidence

### Cycle F1: Perf-gate integrity
**Evidence:** Gates measure mean labeled p95 (`test_perf_gates.py:36-39`); S12-03/S12-06 absent; HL7 throughput tests a local fake (`:294-319`).
**RED:** p95 helper test (known distribution → exact p95); HL7 throughput drives the **real** `Hl7InterfaceEngine` over in-process MLLP socket (100 msg/min, 0 failures, latency histogram sampled); booking/tracking/worklist gates assert p95 thresholds from the sprint plan (hard bounds, no soft skips); registration + autosave gates added.
**GREEN:** Replace mean math; wire real-engine fixture; add missing gates.
**REFACTOR:** Shared `perf_utils.py` (percentile, timed-fixture).

### Cycle F2: RBAC matrix sweep + IDOR expansion
**Evidence:** Sweep predates S11/S12 endpoints; IDOR covers 4 endpoints vs "all APIs".
**RED/GREEN:** Auto-generate cases from the route table × permission map (every RIS route: 403 anonymous/unpermitted, 200 permitted where cheap); IDOR parametrize over all RIS GET-by-id/PUT/DELETE handlers asserting cross-tenant 404/empty (pool-tag model, rule §0.2).
**REFACTOR:** Generator lives in `tests/rbac_matrix_gen.py`; runs in CI suite.

### Cycle F3: WCAG 2.1 AA automated pass
**Evidence:** S12-32 open for TrackingBoard, BillingQueue, DenialRework, RISDashboard, kiosk CheckIn, TemplateManager.
**RED:** vitest axe-core scans per page fail on violations.
**GREEN:** Fix violations (labels, contrast, focus order); scans green; manual keyboard-pass checklist recorded in evidence doc.

### Cycle F4: Persona UAT scripts (S12-14..20)
**Deliverable:** `docs/uat/` scripted walkthroughs (seed commands + click-path + expected outcomes) for radiologist, technologist, scheduler, front-desk, biller, RIS-admin, manager; plus `scripts/seed_uat.py` producing deterministic demo data per persona. Execution sign-off belongs to UAT owners, not this pipeline.

**Phase F exit gate**

```bash
cd backend && .venv/bin/python -m pytest tests/test_perf_gates.py tests/test_rbac_matrix.py -v --tb=short
cd frontend && npx vitest run --run src/a11y/   # or per-page axe specs
# Evidence refresh:
# docs/RIS-integration/S12_HARDENING_EVIDENCE.md regenerated from gate outputs
```

Commits: `test(perf): honest p95 gates incl. real-engine HL7 throughput` · `test(security): generated RBAC matrix + full IDOR net` · `fix(a11y): WCAG pass on RIS pages` · `docs(uat): persona scripts + seeder`

---

## 8. Documentation Artifacts (landed alongside code)

| Artifact | Content |
|---|---|
| `docs/RIS-integration/GAP_AUDIT_REFINED.md` | Full audit: gap register w/ file:line evidence, platform-inheritance map, deliberate non-builds (§0.3), per-sprint verdict tables |
| `docs/RIS-integration/V2_1_SPRINT_COMPLETION.md` | Append corrective note: gate-green caveat pending Phases A1/A2; link to this pipeline |
| `docs/decisions/ADR-031-ris-rate-limiting.md` | Middleware placement, bucket taxonomy, kiosk exemption |
| `docs/decisions/ADR-032-smart-scopes.md` | Scope grammar, read-only initial rollout, token claim shape |

## 9. Final Verification Protocol

```bash
# 1. Fresh-database migration chain (000 → head) incl. 086/087(/088)
cd backend && .venv/bin/python -m alembic upgrade head

# 2. Full backend regression (expect ≥ baseline 2339 passing + new nets, 0 failed)
cd backend && .venv/bin/python -m pytest tests/ -q --tb=short

# 3. Frontend: typecheck + budgeted batches, every failure re-run isolated
cd frontend && npx tsc --noEmit && npx vitest run

# 4. Services smoke via systemd dev stack
scripts/dev.sh restart && curl -fsS http://localhost:8080/healthz && curl -fsS http://localhost:5173/

# 5. Update completion/evidence docs; conventional-commit log reviewed for gate traceability
git log --oneline origin/v3-dev..HEAD | wc -l
```

**Residual deferrals carried forward (tracked, not built here):** AI coding module decision (R2-06-11) · real SMS/email providers · platform-wide chargeback rollup · X12 validators · UAT execution sign-offs (R2-06-13) · DR drill rehearsal (S12-31).
