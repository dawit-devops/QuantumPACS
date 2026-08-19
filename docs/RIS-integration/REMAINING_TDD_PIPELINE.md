# Remaining TDD Implementation Pipeline — All 3-Agent Review Findings

**Date:** 2026-08-19
**Baseline:** 59 frontend + 53 backend tests passing (26/40 findings complete)
**Source:** Consolidated 3-agent review (Arch/QA/Security)
**Pattern:** RED → GREEN → REFACTOR per finding

---

## Completion Status

### ✅ Done (26/40 findings)

| ID | Finding | Category |
|----|---------|----------|
| F-01 | Worklist per_page clamp | Security |
| F-02 | Patient-existence + order/patient match | Security |
| F-03 | CANCELLED slots released from capacity | Security |
| F-06 | Malformed dates → 422 | Security |
| F-07 | Schema max_lengths | Security |
| F-08 | Whitespace override strip | Security |
| D1 | Canonical modalities.ts | Correctness |
| R1 | ScheduleBoard seq guard | Correctness |
| R2 | ScheduleBoard tenant refetch | Correctness |
| P1 | Permission gate alignment | Correctness |
| S11 | RescheduleModal stable deps | Correctness |
| S12 | Dead spans cleanup | Cleanup |
| ME-04 | Dead test mocks cleanup | Cleanup |
| CR-001 | RescheduleModal tests | QA |
| CR-002 | ResourceManager tests | QA |
| CR-003 | BookingFormModal 409 test | QA |
| HI-001 | Order-less booking tests | QA |
| HI-002 | Day navigation tests | QA |
| HI-003 | CancelModal validation tests | QA |
| HI-005 | Permission gating tests | QA |
| R3 | Stale grid fix + test | Correctness |
| T1 | UTC day anchor fix + test | Correctness |
| HI-006 | Tenant refetch verify | QA |
| ME-001 | Error states tests | QA |
| S1/D2 | ScheduleDayNav extraction | Refactor |
| S5-01 | MWL SCP (already existed) | Feature |

### 🔲 Remaining (14/40 findings)

---

## Tier 1 — High Impact (S4 architectural hardening)

### 1. S1+D2: Consolidate slot math into boardSlots.ts
**Source:** Arch review S1, D2
**Severity:** High (Arch)
**Why:** ScheduleBoard re-implements buildSlots/slotIndexFor with a different window (8-18 vs 7-19) and different index math (clamping vs null-return). The shared module boardSlots.ts exists but ScheduleBoard doesn't use it. This is the root cause of two scheduling surfaces rendering different grids.
**Files:** `backend/src/schedule/boardSlots.ts`, `ScheduleBoard.tsx`, `CalendarView.tsx`

**TDD Cycle:**
```
RED:  it("boardSlots.buildSlots respects explicit window bounds", ...)
      → import { buildSlots } from boardSlots
      → buildSlots({ start: 8, end: 18, slotMinutes: 30 })
      → assert first slot is "08:00", last is "17:30"

RED:  it("boardSlots.slotIndexFor returns null for out-of-window", ...)
      → slotIndexFor("07:00", { start: 8, end: 18 }) → null
      → slotIndexFor("19:00", { start: 8, end: 18 }) → null

RED:  it("boardSlots.slotSpanFor calculates multi-slot spans", ...)
      → 60-min appointment → span = 2

GREEN: Parameterize buildSlots/slotIndexFor/slotSpanFor in boardSlots.ts
       with explicit window argument. ScheduleBoard imports with {start:8,end:18}.
       CalendarView uses default {start:7,end:19}.

REFACTOR: Export WINDOW_8_18 and WINDOW_7_19 constants.
```

**Tests:** 4 new unit tests in `test/boardSlots.test.ts`

---

### 2. A1: Keyboard-accessible free cells in calendar grid
**Source:** Arch review A1
**Severity:** Medium (A11y)
**Why:** Free cells are mouse-only (`div` with `onClick` but no `tabIndex`, no `role="button"`, no keyboard handler). Keyboard users can only book via the header button, which targets the first free slot — not the cell they want. This is the primary booking surface.
**Files:** `CalendarView.tsx`, `ScheduleBoard.tsx`

**TDD Cycle:**
```
RED:  it("free cells are focusable and activatable via keyboard", ...)
      → render CalendarView → focus free cell via tab
      → assert cell has tabIndex={0}
      → press Enter → booking modal opens
      → press Space → booking modal opens

RED:  it("free cells announce correct role to screen readers", ...)
      → assert free cell has role="button"
      → assert aria-label includes "(free)"

GREEN: Add tabIndex={0}, role="button", onKeyDown handler to free cells
       in CalendarView.tsx and ScheduleBoard.tsx.
```

**Tests:** 2 new in `ScheduleCalendar.test.tsx`, 1 new in `ScheduleBoard.test.tsx`

---

### 3. A2: Space key activation + aria-selected on order results
**Source:** Arch review A2
**Severity:** Low (A11y)
**Why:** `role="button"` elements handle Enter but not Space (standard activation key). Order result rows in BookingFormModal lack `aria-selected`.
**Files:** `CalendarView.tsx`, `ScheduleBoard.tsx`, `BookingFormModal.tsx`

**TDD Cycle:**
```
RED:  it("Space key activates free cell", ...)
      → focus free cell → press Space → booking modal opens

GREEN: Add case ' ' to onKeyDown handlers (same as Enter).

REFACTOR: Extract shared keyboard handler.
```

**Tests:** 1 new in `ScheduleCalendar.test.tsx`

---

## Tier 2 — Medium Impact (security + correctness)

### 4. F-04: Real CSRF token (or drop static header)
**Source:** Security review F-04
**Severity:** Low (CSRF)
**Why:** `X-CSRF-Token: "1"` is constant — not a real token. CSRF protection relies entirely on SameSite=Strict cookies. If SameSite is ever relaxed (OAuth/embedded flow), there's zero defense. The header is theater.
**Files:** `frontend/src/api/client.ts`, `frontend/src/api/session.ts`, `backend/api/auth.py`

**TDD Cycle:**
```
RED:  it("client sends CSRF token matching server-set cookie", ...)
      → set document.cookie = "csrf_token=abc123"
      → make request → assert X-CSRF-Token header === "abc123"

RED:  it("server sets csrf_token cookie on login", ...)
      → POST /api/auth/login → assert Set-Cookie includes csrf_token

GREEN: Server sets HttpOnly=false, SameSite=Strict csrf_token cookie
       on login. Client reads it and echoes in X-CSRF-Token header.
       Falls back to "1" if cookie missing (backwards compat).
```

**Tests:** 2 new: 1 frontend (`client.test.ts`), 1 backend (`test_auth.py`)

---

### 5. F-10: Align board route gate with actual permissions
**Source:** Security review F-10
**Severity:** Info (permission drift)
**Why:** Route gate is `SCHEDULE_READ` but sidebar uses `WORKLIST_READ`. The board needs both (worklist + appointments endpoints). Some roles hold one but not the other — dead ends.
**Files:** `frontend/src/index.tsx`, `frontend/src/common/Sidebar.tsx`

**TDD Cycle:** Already partially addressed by P1 fix. Verify remaining alignment:
```
RED:  it("schedule-board route accepts WORKLIST_READ-only user", ...)
      → seedUser(["WORKLIST_READ"])
      → navigate to /schedule-board → not redirected

RED:  it("schedule-board route accepts SCHEDULE_READ-only user", ...)
      → seedUser(["SCHEDULE_READ"])
      → navigate to /schedule-board → not redirected
```

**Tests:** 2 new in `route-gates.test.tsx`

---

### 6. F-09: Unify check-in permission
**Source:** Security review F-09
**Severity:** Low (permission consistency)
**Why:** `/ris/patients/{id}/check-in` is gated on `SCHEDULE_WRITE` but the Visits UI uses `PUT /visits/{id}` gated on `REGISTRATION_WRITE`. The grants coincide for receptionists but could diverge for future roles.
**Files:** `backend/api/frontdesk.py`

**TDD Cycle:**
```
RED:  it("check-in endpoint requires REGISTRATION_WRITE", ...)
      → create user with SCHEDULE_WRITE only (no REGISTRATION_WRITE)
      → POST /ris/patients/{id}/check-in → 403

GREEN: Change RisPatientCheckInHandler permission from SCHEDULE_WRITE
       to REGISTRATION_WRITE (or the union of both).
```

**Tests:** 1 new in `test_ris_checkin.py`

---

### 7. S3: Deduplicate dayjs.extend(utc) calls
**Source:** Arch review S3
**Severity:** Low (duplication)
**Why:** `dayjs.extend(utc)` is called in 4 files. Idempotent but noisy — a cross-cutting concern scattered.
**Files:** NEW `frontend/src/schedule/time.ts`, CalendarView.tsx, BookingFormModal.tsx, RescheduleModal.tsx, CancelModal.tsx

**TDD Cycle:**
```
RED:  it("slotToIso converts slot start to ISO string", ...)
      → slotToIso("2026-08-20", "09:00") → "2026-08-20T09:00:00.000Z"

GREEN: Create schedule/time.ts that imports dayjs, extends utc,
       exports slotToIso(day, time) and re-exports dayjs.
       Replace 4 inline dayjs.utc() calls.

REFACTOR: Remove dayjs.extend(utc) from 4 files.
```

**Tests:** 2 new in `test/time.test.ts`

---

## Tier 3 — Low Priority (cleanup + robustness)

### 8. E1: Close booking modal on 409 conflict
**Source:** Arch review E1
**Severity:** Low (UX)
**Why:** After 409, the modal stays open on the stale slot. User can hit Confirm repeatedly, stacking 409s. Better UX: close modal, let user re-pick from refreshed grid.
**Files:** `BookingFormModal.tsx`, `RescheduleModal.tsx`

**TDD Cycle:**
```
RED:  it("closes modal after 409 conflict and shows warning", ...)
      → mockBook.mockRejectedValue({status:409})
      → confirm → modal closes → warning toast shown
      → calendar refetches → user can re-pick

GREEN: In catch block, call onClose() after onConflict() instead
       of keeping modal open.
```

**Tests:** 1 new in `ScheduleCalendar.test.tsx` (modify existing 409 test)

---

### 9. D3: Adopt toErrorMessage in legacy booking surfaces
**Source:** Arch review D3
**Severity:** Low (error handling)
**Why:** Legacy surfaces use `e.message` which renders "undefined" for thrown strings/unknown values. All new code uses `toErrorMessage()`.
**Files:** `ScheduleBoard.tsx`, `AppointmentBooking.tsx`, `Visits.tsx`

**TDD Cycle:**
```
RED:  it("shows meaningful error when booking throws non-Error", ...)
      → mockCreateAppointment.mockRejectedValue("string error")
      → trigger booking → assert "string error" shown (not "undefined")

GREEN: Replace e.message || fallback with toErrorMessage(e) || fallback
       in 3 files (mechanical).
```

**Tests:** 1 new in `ScheduleBoard.test.tsx`

---

### 10. R4: Visits list fetch seq guard
**Source:** Arch review R4
**Severity:** Low (race condition)
**Why:** detailSeq protects the drawer, but the list fetch (filtered by statusFilter) is unguarded. Rapid chip switching lets an earlier filter's response overwrite the newer one.
**Files:** `Visits.tsx`

**TDD Cycle:**
```
RED:  it("recent status filter wins over earlier slow response", ...)
      → switch filter to "arrived" → immediately switch to "checked_in"
      → first request resolves → assert checked_in data shown (not arrived)

GREEN: Add listSeq ref to Visits list fetch (same pattern as detailSeq).
```

**Tests:** 1 new in `FrontDesk.test.tsx`

---

### 11. R5: ResourceManager drawer load seq guard
**Source:** Arch review R5
**Severity:** Low (race condition)
**Why:** Opening resource A's schedule drawer then quickly resource B lets A's finally flip schedLoading off while B's data is still pending.
**Files:** `ResourceManager.tsx`

**TDD Cycle:**
```
RED:  it("schedules drawer shows loading for the correct resource", ...)
      → open drawer for resource A → immediately open for B
      → B resolves first → assert B's data shown, spinner off

GREEN: Add per-open seq ref to schedule drawer fetch.
```

**Tests:** 1 new in `ResourceManager.test.tsx`

---

### 12. T2: Drop redundant reschedule slot filter
**Source:** Arch review T2
**Severity:** Low (dead code)
**Why:** The filter `s.start !== dayjs.utc(selected.start_time).format("HH:mm")` is redundant — the engine already excludes the appointment's own range from free slots. For off-boundary appointments it silently does nothing.
**Files:** `CalendarView.tsx`

**TDD Cycle:**
```
REFACTOR: Remove the filter in CalendarView.tsx (lines 196-199, 389-396).
          Existing reschedule tests still pass (the engine provides the
          correct free slots without client-side filtering).
```

**Tests:** 0 new (existing tests verify)

---

### 13. S13: Reset patient state on AppointmentBooking close
**Source:** Arch review S13
**Severity:** Low (UX)
**Why:** After completing a booking, reopening the modal still shows the previous patient. Scheduler can accidentally book for the wrong patient.
**Files:** `AppointmentBooking.tsx`

**TDD Cycle:**
```
RED:  it("clears patient selection when modal is reopened", ...)
      → complete booking → reopen modal → assert patient search input empty
      → assert no "Change" button present

GREEN: Reset pickedPatient/patientQuery/patientResults in the open effect.
```

**Tests:** 1 new in `FrontDesk.test.tsx`

---

### 14. S14: Fix stale pageSize closure in Visits pagination
**Source:** Arch review S14
**Severity:** Low (pagination)
**Why:** onChange calls setPagination then fetch(pagination.current), but fetch reads pageSize from its closure (stale). One-request inconsistency on page-size change.
**Files:** `Visits.tsx`

**TDD Cycle:**
```
RED:  it("page-size change uses the new page size", ...)
      → change pageSize → assert request per_page matches new size

GREEN: Pass pageSize explicitly into fetch() parameter.
```

**Tests:** 1 new in `FrontDesk.test.tsx`

---

### 15. LO-001: Delete dbg.test.tsx
**Source:** QA review LO-001
**Severity:** Low (cleanup)
**Why:** Leftover debug test file with no assertions beyond "renders". Duplicates fixture setup. Runs in every CI cycle.
**Files:** DELETE `frontend/src/test/dbg.test.tsx`

**TDD Cycle:**
```
REFACTOR: Delete file. Verify npm test still passes.
```

---

### 16. LO-002: Fix dayjs() determinism in ScheduleBoard test
**Source:** QA review LO-002
**Severity:** Low (test reliability)
**Why:** Two separate dayjs() calls could flake at midnight rollover.
**Files:** `ScheduleBoard.test.tsx`

**TDD Cycle:**
```
REFACTOR: Compute once: const today = dayjs(); const tomorrow = today.add(1, "day")
```

---

### 17. LO-003: Board cancel + 500-exam warning tests
**Source:** QA review LO-003
**Severity:** Low (test coverage)
**Why:** Board cancel flow and 500-exam truncation warning are untested.
**Files:** `ScheduleBoard.test.tsx`

**TDD Cycle:**
```
RED:  it("shows 500-exam warning when worklist exceeds limit", ...)
      → mockRequest.mockResolvedValue({data: Array(500), total:500})
      → assert Alert with "first 500 exams" message

RED:  it("cancel appointment from board re-fetches both lists", ...)
      → seedUser(["SCHEDULE_WRITE","SCHEDULE_READ","WORKLIST_READ"])
      → open cancel confirm → confirm → assert both fetch calls made
```

**Tests:** 2 new in `ScheduleBoard.test.tsx`

---

## Dependency Graph

```
Tier 1 (architectural):
  S1+D2 (boardSlots consolidation) ──┐
  A1 (keyboard a11y) ────────────────┤
  A2 (Space key + aria-selected) ────┴──► S4 ARCH DONE

Tier 2 (security + correctness):
  F-04 (CSRF token) ─────────────────┐
  F-10 (route gate verify) ──────────┤
  F-09 (check-in permission) ────────┤
  S3 (dayjs dedup) ──────────────────┴──► S4 SECURITY DONE

Tier 3 (cleanup + robustness):
  E1 (409 close modal) ─────────────┐
  D3 (toErrorMessage adoption) ─────┤
  R4 (Visits list seq guard) ───────┤
  R5 (ResourceManager seq guard) ───┤
  T2 (drop reschedule filter) ──────┤
  S13 (patient state reset) ────────┤
  S14 (stale pageSize) ─────────────┤
  LO-001 (delete dbg.test) ─────────┤
  LO-002 (dayjs determinism) ───────┤
  LO-003 (board cancel tests) ──────┴──► S4 COMPLETE
```

## Execution Order (by dependency + effort)

```
Phase A — Low-effort, high-signal (1-2 days):
  1. LO-001  Delete dbg.test.tsx              (5 min)
  2. LO-002  Fix dayjs determinism            (10 min)
  3. S3      dayjs dedup → time.ts            (30 min)
  4. T2      Drop reschedule filter           (15 min)
  5. D3      toErrorMessage adoption          (30 min)

Phase B — Correctness + security (2-3 days):
  6. S1+D2   boardSlots consolidation         (2h)
  7. F-10     Route gate verify               (30 min)
  8. F-09     Check-in permission unify       (30 min)
  9. F-04     CSRF token                      (2h)

Phase C — A11y + robustness (2-3 days):
  10. A1      Keyboard-accessible free cells  (1h)
  11. A2      Space key + aria-selected        (30 min)
  12. E1      409 close modal                 (30 min)
  13. S13     Patient state reset             (30 min)

Phase D — Race conditions + edge cases (1-2 days):
  14. R4      Visits list seq guard           (1h)
  15. R5      ResourceManager seq guard       (30 min)
  16. S14     Stale pageSize fix              (30 min)
  17. LO-003  Board cancel + 500 tests        (1h)

Exit gate: all tests green, tsc --noEmit clean, 0 findings remaining
```

## Test Score Targets

| Phase | Expected tests added | Cumulative total |
|-------|---------------------|-----------------|
| Baseline | — | 112 (59 FE + 53 BE) |
| Phase A | +6 | 118 |
| Phase B | +5 | 123 |
| Phase C | +4 | 127 |
| Phase D | +6 | 133 |
| **Final** | **+21 total** | **133** |
