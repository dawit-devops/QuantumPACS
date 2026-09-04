# UI/UX Redesign v2 — Front Desk / Receptionist TDD Implementation Plan

**Spec:** `docs/ui-ux-redesign-spec.md` §2.1 (v2.0)
**Branch:** `feature/ris-integration`
**Baseline:** 2561 passed / 2 skipped backend; FE portal suites 34 green, ReadingConsole 44 green (1 pre-existing flake); tsc clean; FE build clean.
**Method:** Vertical TDD slices — one RED test → minimal GREEN → refactor → suite gate. No horizontal batching. One commit per slice.

## 0. Preconditions & Decisions

### D0: Front desk UI contract — rewire to `/api/ris/*` or keep legacy dual-track?

The spec §2.1 APIs all point at `/api/ris/*` (RIS contract). The existing front desk UI runs entirely on the legacy `/api/*` contract (`patients`, `visits`, `appointments`, `queue`, `schedule/availability`). The portal round rewired portal from legacy to RIS (commit `6813947`). 

**Two options:**
- **Option A (rewire):** Move front desk UI to the spec's RIS endpoints. Split registration: `POST /api/ris/patients` (RIS, FD-01) → `POST /api/visits` (legacy, INHERIT). Check-in: `POST /api/ris/appointments/{id}/check-in` (new, FD-04). Queue: `GET /api/ris/tracking?status=arrived` (existing but needs wait-time, FD-05). Timeline: `GET /api/ris/appointments?date=today` (new, FD-06). Search: `GET /api/ris/patients/search` (existing, FD-07). This converges the platform but requires reworking the front desk form flow.
- **Option B (parallel):** Keep the front desk UI on its legacy contract as a QuantumPACS INHERITED surface. Build only the missing pieces that RIS endpoints require (new `POST /ris/appointments/{id}/check-in`, wait-time on tracking, eligibility non-stub, DOB/phone search, today-filtered appointments endpoint). The legacy visits/queue continue to work alongside. Dual-track appointment sources (legacy `appointments` ↔ `ris_appointments`) remain unresolved.

**Recommendation:** Option B — the portal round showed that a full rewire is feasible, but the front desk's registration flow (patient+visit+orders+consents in one chain) is tightly coupled to the legacy visit model. The portal had a clean separation (portal endpoints are read-only view + limited writes). The front desk form is CRUD-heavy. Rewiring the registration alone would split it into two API calls (RIS patient + legacy visit) with no transactional guarantee. Revisit when the RIS order/visit model matures.

**DECIDED 2026-08-24:** Option B (parallel) — front desk UI stays on legacy contract (INHERIT). Build only the missing RIS-side pieces + front desk UI features. Scope: all P0+P1 slices S1–S8.

### D1: Permission grants — WORKLIST_WRITE for receptionist

FD-04 (one-click check-in) needs to flip `ris_appointments.status = 'ARRIVED'`. The existing kiosk `mark_checked_in` does this via token auth. The staff endpoint should be gated `SCHEDULE_WRITE` (receptionist already holds it). **No WORKLIST_WRITE needed** — the appointment status transition is on `ris_appointments`, not `worklist_entries`.

### D2: Permission grants — BILLING_READ for receptionist (deferred P2)

FD-10 (co-pay prompt) needs `BILLING_READ` or a scoped `COPAY_READ` to check invoice balance. Deferred to P2.

### D3: Permission grants — PATIENT_MERGE NOT granted

Fuzzy similar-patient alert (FD-01 G8) is a soft-warn banner, not a merge. The merge itself stays gated `PATIENT_MERGE` (correctly not held by receptionist).

## 1. Refined Gap Backlog (post platform cross-check)

**P0 — Must ship now**
1.  **FD-04**: `POST /api/ris/appointments/{id}/check-in` endpoint missing. Staff needs to flip SCHEDULED→ARRIVED without a kiosk token.
2.  **FD-05**: No wait-time data. `ris_appointments` lacks `checked_in_at` column. `GET /ris/tracking` returns no arrival timestamp, no `wait_minutes`, no color-coding.
3.  **FD-02**: Insurance eligibility is a hardcoded stub. No copay/deductible/coverage data model. Schema `insurance_records` lacks provider/member_id/copay/deductible fields.

**P1 — Ship in this round**
4.  **FD-06**: No "Today's Schedule" front-desk page. `GET /ris/appointments` 500s without `resource_id`. No cross-resource today aggregate. No status/modality quick-filters.
5.  **FD-07**: Patient search is name/MRN only. No DOB, no phone. No global search overlay. No recent searches.
6.  **FD-05**: Queue color-coding in `WaitingQueue.tsx` (green <15m, amber 15-30m, red >30m). Spec HIPAA-named queue vs legacy initials+last4 — align with spec.
7.  **FD-01**: Submit-time MPI fuzzy alert not wired. 409 caught as generic toast, not "similar patient exists" banner.
8.  **FD-01**: Phone keyed into MPI dedup (currently name+DOB only).

**P2 — Deferred**
9.  FD-08 Registration Status Badge (client-side)
10. FD-09 Print Registration Summary (client-side)
11. FD-10 Co-pay Collection Prompt (new endpoint + BILLING grant)
12. Dashboard widgets (kpi-today-checkins, kpi-waiting-count, kpi-overdue-wait, today-timeline, patient-search, quick-actions)

## 2. Vertical Slices (RED → GREEN → refactor → gate)

### S1 — Staff one-click check-in endpoint (P0-1, FD-04)

**Behaviors:** `POST /api/ris/appointments/{id}/check-in` (gated `SCHEDULE_WRITE`) calls `RisAppointments.mark_checked_in` (SCHEDULED→ARRIVED). Returns the updated appointment row. Idempotent (already-ARRIVED → 200 OK, no-op). Invalid appointment → 404. Audit event `ris.checkin_staff`.

**RED:** `test_ris_scheduling_api.py` — new `TestAppointmentCheckIn` class: 200 on SCHEDULED, 404 on missing, 200 idempotent on ARRIVED, SCHEDULE_WRITE gate enforcement (no-perm → 403), audit event shape.

**GREEN:** New handler in `backend/api/scheduling.py` (or `backend/api/checkin.py`) — `RisAppointmentCheckInHandler.post`, route at `routes.py:407` (after cancel). Reuses `RisAppointments.mark_checked_in`. Audit `ris.checkin_staff`.

**Files:** `backend/api/scheduling.py`, `backend/api/routes.py`, `backend/api/checkin.py`, `backend/tests/test_ris_scheduling_api.py`.

**Gate:** `pytest tests/test_ris_scheduling_api.py tests/test_rbac_matrix.py -q`

---

### S2 — checked_in_at column + wait-time payload (P0-2, FD-05)

**Behaviors:** Migration adds `checked_in_at TIMESTAMPTZ` to `ris_appointments` (nullable, set by `mark_checked_in` via `now()`). `GET /ris/tracking?status=arrived` response includes `checked_in_at` and computed `wait_minutes` (elapsed since arrival). `GET /ris/tracking/kpi` adds `overdue_wait_count` (ARRIVED >30m). `WaitingQueue.tsx` renders color-coded badge (green <15m, amber 15-30m, red >30m) and sorts by arrival ascending.

**RED:** `test_tracking_api.py` — new fields on arrived rows: `checked_in_at` IS NOT NULL, `wait_minutes` ≥ 0, KPI includes `overdue_wait_count`. `test_ris_v21_preregistration.py` — `mark_checked_in` sets `checked_in_at`. FE: `test/FrontDesk.test.tsx` — color badge renders correct class per threshold.

**GREEN:** Migration 090: `ALTER TABLE ris_appointments ADD COLUMN checked_in_at TIMESTAMPTZ`. Update `mark_checked_in` to SET `checked_in_at = now()`. Extend tracking query to project `checked_in_at` + `EXTRACT(EPOCH FROM (now() - checked_in_at))/60 AS wait_minutes`. Extend KPI query for overdue count. `WaitingQueue.tsx` color logic + sort.

**Files:** `backend/migrations/versions/`, `backend/db/ris_appointments.py`, `backend/api/worklist.py`, `frontend/src/frontdesk/WaitingQueue.tsx`, `frontend/src/test/FrontDesk.test.tsx`, `backend/tests/test_tracking_api.py`, `backend/tests/test_ris_v21_preregistration.py`.

**Gate:** `pytest tests/test_tracking_api.py tests/test_ris_v21_preregistration.py -q` + `npx vitest run src/test/FrontDesk.test.tsx`

---

### S3 — Insurance eligibility non-stub (P0-3, FD-02)

**Behaviors:** `GET /api/ris/patients/{id}/eligibility` returns real coverage data computed from `insurance_records`: provider, member_id, copay_amount, deductible_total, deductible_remaining, coverage_status. `CreateInsuranceRequest` extended with provider, member_id, copay_amount, deductible_total fields. `insurance_records` table extended with those columns (migration).

**RED:** `test_ris_eligibility.py` — new test class asserts real provider/member_id/copay/deductible/coverage in response, not stub. POST extended schema round-trips. Stub path removed.

**GREEN:** Migration 090 extends `insurance_records` with `provider`, `member_id`, `copay_amount`, `deductible_total`, `deductible_remaining` columns. `RisPatientEligibilityHandler` computes from stored policy (no real payer API — returns stored copay/deductible from the most recent insurance record). `CreateInsuranceRequest` schema extended. Front desk `Visits.tsx` eligibility tab displays real values.

**Files:** `backend/migrations/versions/`, `backend/api/frontdesk.py`, `backend/api/schemas/frontdesk.py`, `backend/db/frontdesk.py`, `frontend/src/frontdesk/Visits.tsx`, `frontend/src/api/frontdesk.ts`, `backend/tests/test_ris_eligibility.py`.

**Gate:** `pytest tests/test_ris_eligibility.py tests/test_ris_patients.py -q` + `npx vitest run src/test/FrontDesk.test.tsx`

---

### S4 — Today's Schedule page (P1-4, FD-06)

**Behaviors:** New sidebar entry "Today's Schedule" → `GET /api/ris/appointments?date=today` (cross-resource aggregate, no `resource_id` required). Quick-filter chips by modality and status. Time column, patient name, modality, room, status.

**RED:** `test_ris_scheduling_api.py` — GET without `resource_id` returns 200 (not 500) with today's appointments across all resources. Modality/status filter params work. `test/FrontDesk.test.tsx` — new page renders chips, filters, appointment rows.

**GREEN:** `RisAppointmentsHandler.get` — when `resource_id` omitted, aggregate across all resources for the given date (join `ris_resources` for modality). Modality/status filters via WHERE clause. New `frontend/src/frontdesk/ScheduleToday.tsx` page. Sidebar entry "Today's Schedule" in `Sidebar.tsx`. Route `/frontdesk/schedule` → `ScheduleToday.tsx`.

**Files:** `backend/api/scheduling.py`, `backend/db/ris_appointments.py`, `backend/api/routes.py`, `frontend/src/frontdesk/ScheduleToday.tsx`, `frontend/src/common/Sidebar.tsx`, `frontend/src/navigator.ts`, `frontend/src/test/FrontDesk.test.tsx`, `backend/tests/test_ris_scheduling_api.py`.

**Gate:** `pytest tests/test_ris_scheduling_api.py -q` + `npx vitest run src/test/FrontDesk.test.tsx`

---

### S5 — Patient Quick Search: DOB/phone + overlay (P1-5, FD-07)

**Behaviors:** `GET /api/ris/patients/search` accepts `?dob=`, `?phone=` in addition to `?q=`. Global search overlay (modal) on front desk workspace — search by name, MRN, DOB, phone. Shows recent searches (localStorage). Click to navigate to patient detail.

**RED:** `test_ris_patients.py` — search by DOB and phone returns matching patients. `test/FrontDesk.test.tsx` — overlay renders, recent searches persist, navigation fires.

**GREEN:** Extend `search_patients` in `backend/db/frontdesk.py` to accept `dob` and `phone` params (ILIKE + exact match). Extend `RisPatientsSearchHandler` to pass query params. New `frontend/src/frontdesk/PatientSearchOverlay.tsx` modal component. Wire into `Sidebar.tsx` "Patient Search" item + search icon in top bar. Recent searches via `localStorage`.

**Files:** `backend/db/frontdesk.py`, `backend/api/frontdesk.py`, `frontend/src/frontdesk/PatientSearchOverlay.tsx`, `frontend/src/common/Sidebar.tsx`, `frontend/src/api/frontdesk.ts`, `frontend/src/test/FrontDesk.test.tsx`, `backend/tests/test_ris_patients.py`.

**Gate:** `pytest tests/test_ris_patients.py -q` + `npx vitest run src/test/FrontDesk.test.tsx`

---

### S6 — MPI fuzzy alert + phone dedup (P1-6/7, FD-01)

**Behaviors:** `POST /api/ris/patients` with duplicate name+DOB+phone → 409 `PATIENT_EXISTS` (phone added to dedup key). `POST /api/ris/patients` with similar name+DOB (matching fuzzy trigram) → 200 with `warning: { is_duplicate: true, existing_patient_id: ..., existing_patient_name: ... }` in response. Front desk registration form surfaces the warning banner.

**RED:** `test_ris_patients.py` — phone duplicate → 409. Fuzzy name match → 200 with warning. `test/FrontDesk.test.tsx` — warning banner renders on duplicate response.

**GREEN:** `find_patient_duplicate` in `backend/db/frontdesk.py` adds phone to WHERE clause. `_register_patient` in `backend/api/frontdesk.py` — when exact name+DOB misses, runs `search_patients_fuzzy(name, birth_date)`. If fuzzy match found, returns 200 with `warning` in response body (not 409). `Registration.tsx` handles `response.warning` → renders `Alert` banner with "Similar patient exists: {name} — Review or continue" + link to patient detail.

**Files:** `backend/db/frontdesk.py`, `backend/api/frontdesk.py`, `frontend/src/frontdesk/Registration.tsx`, `frontend/src/test/FrontDesk.test.tsx`, `backend/tests/test_ris_patients.py`.

**Gate:** `pytest tests/test_ris_patients.py tests/test_frontdesk_api.py -q` + `npx vitest run src/test/FrontDesk.test.tsx`

---

### S7 — Queue spec alignment (P1-6, FD-05)

**Behaviors:** `WaitingQueue.tsx` shows patient name (not HIPAA initials+last4) per spec FD-05. Color-coded wait time badge. Sorted by arrival (oldest first). Priority column (STAT flagged). Modality/room columns.

**RED:** `test/FrontDesk.test.tsx` — full name displayed, color badge, priority chip, modality/room columns. `test_frontdesk_api.py` — queue returns full name (HIPAA reconsideration: spec says named queue, this is internal staff view).

**GREEN:** `WaitingQueueHandler` switches to full name projection (no initials+last4). `WaitingQueue.tsx` adds priority/modality/room columns, color-coded wait badge, arrival sort. This replaces the legacy privacy-projected queue for the front desk workspace.

**Files:** `backend/api/frontdesk.py`, `backend/db/frontdesk.py`, `frontend/src/frontdesk/WaitingQueue.tsx`, `frontend/src/test/FrontDesk.test.tsx`, `backend/tests/test_frontdesk_api.py`.

**Gate:** `pytest tests/test_frontdesk_api.py -q` + `npx vitest run src/test/FrontDesk.test.tsx`

---

### S8 — Sidebar + landing alignment (P1, spec §2.1)

**Behaviors:** Sidebar lists: Registration, Today's Schedule, Waiting Queue, Patient Search. Landing `/frontdesk/registration` shows Registration form (as-is) + quick-action cards (New Registration, Check-in, Walk-in Book).

**RED:** `test/FrontDesk.test.tsx` — sidebar items present, landing renders quick-action cards.

**GREEN:** Sidebar.tsx adds "Patient Search" item, renames "Visits & Check-In" → "Today's Schedule". Landing page `Registration.tsx` (or wrapper) adds quick-action cards row.

**Files:** `frontend/src/common/Sidebar.tsx`, `frontend/src/frontdesk/Registration.tsx`, `frontend/src/test/FrontDesk.test.tsx`.

**Gate:** `npx vitest run src/test/FrontDesk.test.tsx`

## 3. Migration 090

Accumulates: `ris_appointments.checked_in_at`, `insurance_records` provider/member_id/copay/deductible_remaining/deductible_total. Down-revision `089`.

## 4. Permission Grant Request (for human review)

| ID | Permission | Grant to | Feature | Reason |
|----|-----------|----------|---------|--------|
| — | WORKLIST_WRITE | (not needed) | FD-04 | S1 uses SCHEDULE_WRITE (already held) on ris_appointments, not worklist_entries |
| G1 | — | — | FD-05 queue | Queue reads from legacy `/api/queue` (QUEUE_READ, already held). RIS tracking uses WORKLIST_READ (already held). No new grant. |
| G2 | PATIENT_MERGE | (NOT granted) | FD-01 | Fuzzy alert is soft-warn only; merge is separate flow gated PATIENT_MERGE. Correctly withheld. |
| G3 | BILLING_READ | MATRIX_A_RECEPT | FD-10 | Deferred P2. Needed for co-pay balance check. Add when S9 is scheduled. |

**No new permissions required for P0/P1 slices.** All existing permissions (`SCHEDULE_WRITE`, `PATIENT_WRITE`, `PATIENT_READ`, `WORKLIST_READ`, `QUEUE_READ`, `REGISTRATION_READ`, `REGISTRATION_WRITE`) are already held by `MATRIX_A_RECEPT`.

## 5. Verification Gates (per slice)

1. Targeted RED fails for the stated reason
2. GREEN: slice tests pass
3. `pytest tests/<affected-suites> -q` + RBAC suite if touch permissions
4. FE: `npx vitest run src/test/FrontDesk.test.tsx frontend/src/test/frontdesk-api.test.ts` + `npx tsc --noEmit`
5. Full backend suite before each commit: `pytest tests/ -q`
6. FE build: `npx vite build`

## 6. Commit Strategy

One commit per slice, messages referencing spec IDs (FD-xx) and slice numbers. Conventional commits (`feat:`, `fix:`, `chore:`). Work tree clean after each.

```text
feat: S1 staff one-click check-in endpoint POST /ris/appointments/{id}/check-in (FD-04)
feat: S2 checked_in_at column + wait-time payload + color-coded queue (FD-05)
feat: S3 insurance eligibility non-stub with copay/deductible fields (FD-02)
feat: S4 Today's Schedule page with cross-resource aggregate + filters (FD-06)
feat: S5 patient quick search DOB/phone + global overlay (FD-07)
feat: S6 MPI fuzzy alert + phone dedup on patient create (FD-01)
feat: S7 queue spec alignment: full name, wait-time colors, priority (FD-05)
feat: S8 sidebar + landing spec alignment (FD landing)
```