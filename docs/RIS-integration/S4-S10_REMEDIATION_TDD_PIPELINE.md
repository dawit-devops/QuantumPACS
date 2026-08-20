# S4-S10 Remediation TDD Pipeline — Prioritized Implementation Plan

**Date:** 2026-08-20
**Source:** [`S5-S10_REVIEW_REPORT.md`](S5-S10_REVIEW_REPORT.md) findings · [`CONSOLIDATED_SPRINT_PLAN.md`](CONSOLIDATED_SPRINT_PLAN.md) · [`S6_S7_TDD_PIPELINE.md`](S6_S7_TDD_PIPELINE.md)
**Pattern:** Vertical-slice TDD per the TDD skill (RED → GREEN → REFACTOR), one test → one fix per cycle.
**Branch:** `feature/ris-integration`

---

## 1. Prioritization (dependency-ordered)

The review found 8 Critical + 12 High + 20+ Medium findings. Fix order follows both severity and the sprint dependency graph: tracking statuses (S6-15) gate the board UI, MPPS correctness (S6-07) gates exam linkage (S6-12), and sign-off integrity (S8-12) gates everything downstream (S10).

| Phase | Findings | Effort | Depends on |
|-------|----------|--------|------------|
| **P1 Blockers** | CR-1..CR-8 | ~3d | — |
| **P2 Correctness** | H-1..5 (S4), H-6..8 (S6), H-9..10 (S8), H-11..14 (S10/FE) | ~4d | P1 |
| **P3 RLS/Tests** | S4-21, S8-20, S10-15 RLS; S6-23/24/25 tests | ~3d | P1, P2 |
| **P4 Mediums** | B-series, M-series, V-series, FE M-series | ~5d | P2 |

**P1 Blockers are the ship-gate.** Everything below assumes P1 green.

---

## 2. Phase 1 — Blockers (8 vertical slices)

### Cycle B1: Tracking status CHECK mismatch (CR-1)
**RED:** `tests/test_tracking_status_constraint.py` — API-level test (TestClient + mocked conn is insufficient — the bug is a real-DB CHECK). Add DB-backed test: create worklist entry, PUT `arrived` from `scheduled` → 200; PUT `completed` from `in_progress` → 200.
**GREEN:** Migration `073_tracking_status_values.py` — extend CHECK to `('scheduled','arrived','in_progress','performed','completed','cancelled')`; align `dcm/server.py:_entry_to_dataset` mapping (MPPS writes `performed`; manual writes `arrived`/`completed` — distinct tracks, both valid).
**REFACTOR:** Single source of truth for `TRACKING_VALID_TRANSITIONS` (remove duplicate at `api/worklist.py:160-166`).

### Cycle B2: MPPS reads wrong DICOM element (CR-2)
**RED:** `tests/test_mpps_consumer.py` — dataset with `PerformedProcedureStepSequence[0].PerformedProcedureStepStatus='COMPLETED'` (and SPS echo `'IN_PROGRESS'`) → N-SET maps to `performed`; N-CREATE with PPS `'IN_PROGRESS'` → `in_progress`. Existing tests construct SPS-only datasets — update to the correct element.
**GREEN:** `_extract_sps_status` → `_extract_mpps_status` reading `PerformedProcedureStepSequence[0].PerformedProcedureStepStatus` (0040,0252), falling back to SPS status only when PPS absent (lenient for non-conformant modalities).
**REFACTOR:** none expected.

### Cycle B3: MPPS consumer tenant scoping (CR-3)
**RED:** `tests/test_mpps_consumer.py` — `handle_n_create`/`handle_n_set` invoked with AE mapped to a non-default tenant: assert worklist lookup happens inside `tenant_db_scope` with resolved slug (mock `_tenant_scope_for_ae`).
**GREEN:** In `dcm/server.py` `handle_n_create`/`handle_n_set` — resolve slug via `_tenant_scope_for_ae(ae_title)` and wrap the consumer call in `tenant_db_scope(slug, tenant_info)` (mirror `handle_find_async` at `:159-196`). Also fix `0xA700` → `0x0112` for unknown accession and `0x0110` for processing failure (M-1 folded in).
**REFACTOR:** extract `_run_mpps(fn, event)` helper shared by both handlers.

### Cycle B4: Signed/final reports editable + REPORT_SIGN bypass (CR-4)
**RED:** `tests/test_reporting_s8.py` (API-level, TestClient): PUT draft with `status='final'` → 422/409 (not allowed); PUT on existing `final` report → 409 (locked); PUT on `submitted` still locked (existing behavior); sign endpoint still works.
**GREEN:** `api/schemas/reports.py` — `SaveReportRequest.status` allowed `draft|preliminary` only (remove `final`); `api/reports.py:246-285` — if `existing.status in ('final','submitted')` → 409 `validation_error('Signed/submitted reports are locked')`.
**REFACTOR:** shared `_assert_editable(report)` helper.
**Frontend:** `ReadingConsole.tsx:206` — stop sending `preliminary` for final reports (the PUT now rejects it anyway; remove the status flip entirely — autosave only drafts).

### Cycle B5: Critical-flag submit broken (CR-5)
**RED:** `frontend/src/test/CriticalResults.test.tsx` — render + submit form; assert `request` called with `data:` payload (JSON body, not `[object Object]`).
**GREEN:** `CriticalResults.tsx:66-78` — `body:` → `data:`.

### Cycle B6: Critical UI unreachable (CR-6)
**RED:** `frontend/src/test/CriticalResults.test.tsx` — render app shell at `/critical` route → component mounts; ReadingConsole renders "Flag Critical" button.
**GREEN:** Route `/critical` → `CriticalResults` in `index.tsx`; nav item in `Sidebar.tsx` (radiologist section); "Flag Critical" button in `ReadingConsole.tsx` opening `FlagCriticalModal` (pass exam/report context).
**REFACTOR:** modal opens with pre-filled exam/report ids.

### Cycle B7: ED-physician recipient wiring (CR-7)
**RED:** FE test: submit with `recipient_role='ed_physician'` + selected user → `recipient_id` in payload. BE test: POST critical with `recipient_id` → `notify_user` called for that user; without → role fallback.
**GREEN:** FE — user picker (search by role) in `FlagCriticalModal`; send `recipient_id`. BE — `api/notifications.py:144-158` — already branches on `recipient_id`; keep role fallback.
**REFACTOR:** none.
### Cycle B8: Distribution + escalation engines dead code (CR-8)
**RED:** `tests/test_critical_results_s10.py` — `DeliveryStatusHandler` returns 200 with rows when `ris_results_distribution` exists (assert query succeeds, PHI payload not leaked to non-owner); sign path invokes `ResultsDistributionEngine` (mock asserts called).
**GREEN:** Migration `074_ris_results_distribution.py` — create `ris_results_distribution` (report_id, recipient, status, payload, retry_count, created_at, tenant_id); wire `ResultsDistributionEngine.distribute` into sign handler (S8-13 stub replaced); `CriticalEscalationEngine` background loop in `lifecycle.py` (daemon thread, interval check).
**REFACTOR:** none.

---

## 3. Phase 2 — Correctness (High findings, after P1)

| Cycle | Finding | Fix |
|-------|---------|-----|
| H1 | S4 audit actor='system' | `api/scheduling.py` — pass `request.user.id` into `SchedulingEngine(actor_id=...)` on all handlers |
| H2 | S4 ExclusionViolationError → 500 | `services/scheduling/engine.py` — catch `asyncpg.exceptions.ExclusionViolationError` in `book()`, re-raise `SchedulingConflict` → 409 |
| H3 | S4 override delete+insert not transactional | Wrap delete→audit→insert→transition in `conn.transaction()`; on insert failure roll back the delete |
| H4 | S4 reschedule rejects CANCELLED-held slots | `engine.py:247-254` — filter `status != 'CANCELLED'` in conflict list (mirror `book()`) |
| H5 | S4 worklist sync on override/reschedule/cancel | Delete stale MWL entries on override; `Worklist.update_entry` on reschedule; `Worklist.cancel` on cancel |
| H6 | S6-06 columns missing | Migration `075_ris_worklist_ris_columns.py` — add `ris_order_id`, `mpps_status`, `body_part`, `contrast` to `worklist_entries` |
| H7 | S6 MPPS transitions not in audit_log | `services/mpps_consumer/service.py` — `AuditLog.log_event` on each N-CREATE/N-SET (resource_type='worklist_entry') |
| H8 | S6-09 echo + S6-11 histogram | C-ECHO SCU stub to PACS on MPPS COMPLETED; `ris_mpps_latency_seconds` histogram in `api/telemetry.py` |
| H9 | S8 templates never seeded | Call `seed_defaults()` on `GET /reports/templates` when empty (or in `db_init`); reconcile with legacy `report_templates` |
| H10 | S8 version attribution | `api/reports.py` PUT — pass `edited_by=request.user.id` into `Reports.update()`; `add_version` uses it |
| H11 | S10 no SMS/email/portal; opt-out missing | Add `critical.flagged`/`critical.escalated` to `EVENT_CATALOG`; notify via existing channel framework (portal notification) honoring prefs |
| H12 | S10 ack overwrites state; any user acks | `acknowledge()` — require `status='flagged'`; require acker is recipient or has `CRITICAL_RESULTS_READ` + audit event |
| H13 | FE Sign & Next stale state | `ReadingConsole.tsx` — reset report/findings/impression on `examId` change; seq guard in `useExamImaging` |
| H14 | FE autosave flush on unmount | `beforeunload` handler + flush on `goBack()` |

---

## 4. Phase 3 — RLS + Test Gaps

- S4-21 / S8-20 / S10-15: enable RLS policies or document pool-separation as the control; replace `xfail`/`isinstance` tests with real cross-tenant asserts (two-tenant fixture exists in `test_ris_tenant_isolation.py`).
- S6-23 STAT E2E, S6-24 50-concurrent tracking updates, S6-25 latency p95 < 5s: add tests.
- S4-20: reroute stress test through `SchedulingEngine.book()` (currently raw repo inserts).

---

## 5. Phase 4 — Medium findings (backlog, after P2)

B-series (S4: 500s on missing ids/dates, history details, referring-MD scope, FK order_id; S6: DIMSE codes, transactional consumer, N-CREATE regression guard, event read path, AE thread guards, UID validity, MWL wildcards, C-FIND paging, status race; S8: charge dup, version dedup, search escape, assignment role check; S10: flag validation, retry no-op) + FE M-series (pagination reset, staleness guard, aria-labels, KPI errors, critical column, dedup maps, day semantics, monolith split).

---

## 6. Exit Gate (per phase)

```bash
# P1 gate — backend
cd backend && .venv/bin/python -m pytest tests/test_mpps_consumer.py tests/test_tracking_api.py tests/test_reporting_s8.py tests/test_critical_results_s10.py -v --tb=short

# P1 gate — frontend
cd frontend && npx tsc --noEmit && npx vitest run src/test/CriticalResults.test.tsx src/test/TrackingBoard.test.tsx

# Full regression (each phase end)
cd backend && .venv/bin/python -m pytest tests/ -q --tb=short
cd frontend && npx tsc --noEmit && npx vitest run

# Migrations must stay idempotent: alembic upgrade head on a fresh DB
cd backend && .venv/bin/python -m alembic upgrade head
```
