# S4-S5 TDD Implementation Pipeline — Re-mapped

**Date:** 2026-08-19
**Baseline:** 47 frontend tests + 53 backend tests passing
**Derived from:** Consolidated 3-agent review (Arch/QA/Security)
**Pattern:** Vertical-slice TDD per the TDD skill (RED → GREEN → REFACTOR)

---

## Completed (this session)

| # | ID | Finding | Severity | Status |
|---|-----|---------|----------|--------|
| 1 | F-01 | Worklist per_page unbounded (PHI dump) | P0 Security | DONE |
| 2 | F-02 | Patient-existence check in order-less booking | P0 Security | DONE |
| 3 | F-03 | CANCELLED appointments block capacity | P0 Security | DONE |
| 4 | F-06 | Malformed dates return 500 not 422 | P0 Security | DONE |
| 5 | F-07 | Schema max_lengths on appointment fields | P0 Security | DONE |
| 6 | F-08 | Whitespace override bypasses audit | P0 Security | DONE |
| 7 | D1 | 5 conflicting MODALITY arrays | P1 Correctness | DONE |
| 8 | R1 | ScheduleBoard no seq guard | P1 Correctness | DONE |
| 9 | R2 | ScheduleBoard no tenant refetch | P1 Correctness | DONE |
| 10 | P1 | Sidebar vs route gate contradict | P1 Correctness | DONE |
| 11 | S11 | RescheduleModal unstable deps | M1 Correctness | DONE |
| 12 | S12 | Dead spans variable | Low Cleanup | DONE |
| 13 | ME-04 | Dead test mocks | Low Cleanup | DONE |
| 14 | CR-001 | RescheduleModal zero test coverage | CRITICAL QA | DONE |
| 15 | CR-002 | ResourceManager zero test coverage | CRITICAL QA | DONE |
| 16 | CR-003 | BookingFormModal 409 untested | CRITICAL QA | DONE |

---

## Remaining: Next 10 Prioritized Implementations

### Tier 1 — High Impact (S4 completion)

#### 1. HI-001: Order-less booking + order-search edge paths
**Source:** QA review HI-001
**Why:** The booking modal supports order-less flow (type patient ID directly) and order search failures — neither path is tested. A regression here silently breaks the scheduler's primary workflow.
**Files:** `frontend/src/test/ScheduleCalendar.test.tsx`
**Tests to add:**
- Books without an order by typing patient ID directly
- Does not search on single-character term
- Surfaces order search failure as toast

**TDD Cycle:**
```
RED:  it("books without an order by typing patient ID directly", ...)
      → mockBook.mockResolvedValue(...)
      → open free cell → type patient ID in "Or patient ID directly" → confirm
      → assert mockBook called with order_id: "", patient_id: "P999"

RED:  it("does not search on single-character term", ...)
      → type "J" in order search → mockSearchOrders NOT called
      → type "Jane" → mockSearchOrders called

RED:  it("surfaces order search failure as toast", ...)
      → mockSearchOrders.mockRejectedValue({message: "search down"})
      → type "Jane{Enter}" → message.error fired
```

---

#### 2. HI-002: Day navigation + modal-state reset
**Source:** QA review HI-002
**Why:** The calendar's Prev/Today/Next buttons and their interaction with open modals are untested. A modal stranded across a day change is a clinical hazard.
**Files:** `frontend/src/test/ScheduleCalendar.test.tsx`
**Tests to add:**
- Navigates days and re-fetches for new day
- Closes booking modal when navigating to another day

**TDD Cycle:**
```
RED:  it("navigates days and re-fetches appointments", ...)
      → render → click Next day → assert mockListResources called again
      → assert grid aria-label contains next day's date

RED:  it("closes booking modal when navigating to another day", ...)
      → open booking modal from free cell → click Next day
      → assert "Book Appointment" modal title no longer present
      → assert mockBook NOT called
```

---

#### 3. HI-003: CancelModal validation + failure path
**Source:** QA review HI-003
**Why:** The cancel flow requires a reason (audit-critical). The disabled button and failure toast are untested.
**Files:** `frontend/src/test/ScheduleCalendar.test.tsx`
**Tests to add:**
- Blocks cancelling without a reason (button disabled)
- Shows error when cancel request fails

**TDD Cycle:**
```
RED:  it("blocks cancelling without a reason", ...)
      → open appointment → click Cancel → confirm button disabled
      → click confirm → mockCancel NOT called

RED:  it("shows error when cancel request fails", ...)
      → mockCancel.mockRejectedValue({message: "Cancel failed"})
      → type reason → click confirm → message.error fired
```

---

#### 4. HI-005: Permission gating across surfaces
**Source:** QA review HI-005
**Why:** Only CalendarView's drawer is gate-tested. Cell-click booking, ResourceManager, and board cancel are untested — a read-only user could click a free cell and open the booking modal.
**Files:** `frontend/src/test/ScheduleCalendar.test.tsx`, `frontend/src/test/ResourceManager.test.tsx`
**Tests to add:**
- CalendarView: read-only user clicking free cell does NOT open booking modal
- ResourceManager: read-only user cannot see New Resource or Schedules buttons (already partially covered)

**TDD Cycle:**
```
RED:  it("does not open booking modal when read-only user clicks free cell", ...)
      → seedUser(["SCHEDULE_READ"])
      → click free cell → "Book Appointment" modal NOT present
      → assert mockBook NOT called
```

---

### Tier 2 — Medium Impact (S4 hardening)

#### 5. R3: CalendarView stale grid after fetch failure
**Source:** Arch review R3
**Why:** After navigating to a new day whose fetch fails, the grid still shows the previous day's bookings under the new date header. A scheduler acts on wrong-day data.
**Files:** `frontend/src/schedule/CalendarView.tsx`, `frontend/src/test/ScheduleCalendar.test.tsx`
**Test + Fix:**
```
RED:  it("clears grid data when fetch fails", ...)
      → mockListResources.mockRejectedValueOnce(...)
      → render → navigate to new day → error shown
      → assert grid shows empty (no stale blocks from previous day)

GREEN: In CalendarView.tsx fetch(), clear setAppointments({}) and
       setFreeSlots({}) on fetch start or in the catch block.
```

---

#### 6. T1: UTC day anchor (browser-local vs UTC)
**Source:** Arch review T1
**Why:** Day label uses `dayjs()` (browser-local) but backend interprets as UTC. Users in UTC+8 between 00:00-08:00 see "Today" pointing at yesterday's UTC date.
**Files:** `frontend/src/schedule/CalendarView.tsx`, `frontend/src/test/ScheduleCalendar.test.tsx`
**Test + Fix:**
```
RED:  it("anchors day in UTC", ...)
      → mock dayjs.utc() to return fixed date
      → assert header shows UTC date not browser-local

GREEN: Change useState initial to dayjs.utc().format("YYYY-MM-DD")
       and Today button to dayjs.utc().format("YYYY-MM-DD")
```

---

#### 7. HI-006: Tenant refetch wiring verification
**Source:** QA review HI-006
**Why:** useTenantRefetch is mocked to no-op in all scheduling tests. The integration contract — that pages re-fetch on tenant switch — is never asserted.
**Files:** `frontend/src/test/ScheduleCalendar.test.tsx`, `frontend/src/test/ResourceManager.test.tsx`
**Tests to add:**
- CalendarView: capture useTenantRefetch callback, invoke it, assert refetch
- ResourceManager: same pattern

**TDD Cycle:**
```
RED:  it("refetches resources on tenant change", ...)
      → mock useTenantRefetch to capture the registered callback
      → render → initial fetch done → invoke captured callback
      → assert mockListResources called again
```

---

#### 8. ME-001: Error states on scheduling surfaces
**Source:** QA review ME-001
**Why:** No suite ever tests the error Alert + Retry paths. A regression in error handling leaves the user staring at a blank screen.
**Files:** `frontend/src/test/ScheduleCalendar.test.tsx`, `frontend/src/test/ScheduleBoard.test.tsx`
**Tests to add:**
- CalendarView: fetch failure shows error Alert
- ScheduleBoard: fetch failure shows error + Retry button works

**TDD Cycle:**
```
RED:  it("shows error alert on fetch failure", ...)
      → mockListResources.mockRejectedValue(...)
      → assert Alert role present with error text

RED:  it("retry button re-fires request on schedule board", ...)
      → mockRequest.mockRejectedValueOnce(...) then mockResolvedValue(...)
      → click Retry → assert data re-rendered
```

---

### Tier 3 — S5 Prep (architectural)

#### 9. Extract shared ScheduleDayNav component
**Source:** Arch review S1/D2
**Why:** CalendarView and ScheduleBoard both render identical prev/Today/next nav blocks with different constants. Extracting a shared component eliminates the duplication and makes both surfaces consistent.
**Files:** NEW `frontend/src/schedule/ScheduleDayNav.tsx`, CalendarView.tsx, ScheduleBoard.tsx
**Test + Refactor:**
```
RED:  it("ScheduleDayNav renders prev/today/next buttons", ...)
      → render <ScheduleDayNav day="2026-08-20" onDayChange={fn} />
      → assert three buttons, Today button text, aria-labels

GREEN: Extract the nav block from CalendarView into ScheduleDayNav.
       Update CalendarView and ScheduleBoard to import it.
       Verify existing tests still pass.
```

---

#### 10. S5-01: MWL SCP service — C-FIND handler (S5 kickoff)
**Source:** CONSOLIDATED_SPRINT_PLAN S6-01
**Why:** The first S5 task. MWL SCP lets modalities query the worklist via DICOM C-FIND — the bridge between RIS scheduling and actual imaging.
**Files:** NEW `backend/services/mwl_scp/service.py`, NEW `backend/tests/test_mwl_scp.py`
**TDD Cycle:**
```
RED:  it("C-FIND returns matching worklist entries", ...)
      → Create worklist entries in test DB
      → Send C-FIND request to MWL SCP
      → Assert response contains matching entries

RED:  it("C-FIND with station_ae filter returns subset", ...)
      → Create entries with different station_ae
      → C-FIND with station_ae filter
      → Assert only matching entries returned

GREEN: Implement MwlScpService.handle_c_find() that queries
       worklist_entries WHERE status IN ('scheduled','arrived')
       and applies DICOM wildcard matching.

REFACTOR: Extract DICOM dataset builder for MWL IOD attributes.
```

---

## Dependency Graph

```
Completed (this session):
  F-01..F-08 (security) ─┐
  D1 (modalities) ───────┤
  R1,R2,P1,S11,S12 ──────┤──► S4 DONE
  CR-001..CR-003 (tests) ─┘

Next 10 (S4 completion → S5 kickoff):
  1. HI-001 (order-less booking tests) ──────┐
  2. HI-002 (day nav tests) ─────────────────┤
  3. HI-003 (cancel validation tests) ───────┤──► S4 test coverage
  4. HI-005 (permission gating tests) ───────┘    complete

  5. R3 (stale grid fix) ────────────────────┐
  6. T1 (UTC day anchor) ────────────────────┤──► S4 correctness
  7. HI-006 (tenant refetch verify) ─────────┤    hardened
  8. ME-001 (error states) ──────────────────┘

  9. ScheduleDayNav extract ─────────────────┐──► S4 refactor
                                             │    complete
  10. S5-01 MWL SCP service ────────────────┘──► S5 KICKOFF
```

## Execution Order

```
Week 1 (S4 test completion):
  Day 1-2: HI-001 + HI-003 (booking + cancel tests)
  Day 3:   HI-002 (day navigation tests)
  Day 4:   HI-005 (permission gating tests)
  Day 5:   HI-006 (tenant refetch verify)

Week 2 (S4 hardening + refactor):
  Day 1:   R3 (stale grid fix + test)
  Day 2:   T1 (UTC anchor fix + test)
  Day 3:   ME-001 (error state tests)
  Day 4:   ScheduleDayNav extraction
  Day 5:   S5-01 MWL SCP service (S5 kickoff)

Exit gate: all tests green, tsc --noEmit clean
```
