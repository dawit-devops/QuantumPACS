# S5 TDD Implementation Plan — RIS Integration

**Date:** 2026-08-19
**Derived from:** 3-Agent Review (Arch/QA/Security) + CONSOLIDATED_SPRINT_PLAN.md
**Scope:** S4.5 (security/correctness completion) → S5 (MWL/MPPS + Tracking Board)
**Pattern:** Vertical-slice TDD per the TDD skill (RED → GREEN → REFACTOR)

---

## Sprint S4.5 — Security & Correctness Completion (Blocker for S5)

**Goal:** Close all P0 security findings and P1 frontend correctness gaps from the 3-agent review. Every fix is test-first. Exit gate: all S4.5 tests pass + existing suite green.

### Dependency Order (TDD Pipeline)

```
F-01 (worklist clamp) ─────────────────────────┐
F-02 (patient check) ──────────────────────────┤
F-03 (cancelled slot release) ──────────────────┤──► S5 gate
F-08 (whitespace override) ────────────────────┤
F-06 (date validation) ────────────────────────┤
D1 (canonical modalities) ─────────────────────┤
R1 (ScheduleBoard seq guard) ──────────────────┤
P1 (permission gate align) ────────────────────┘
```

### TDD Cycle 1: F-01 — Clamp worklist per_page

**RED:**
```python
# backend/tests/test_worklist_clamp.py
class TestWorklistPaginationClamp:
    """F-01 — per_page must be clamped to prevent bulk PHI dump."""

    def test_per_page_capped_at_200(self):
        client = TestClient(_worklist_app(['WORKLIST_READ']))
        resp = client.get('/worklist?per_page=999999')
        assert resp.status_code == 200
        # Response must not contain more than 200 entries
        assert len(resp.json().get('data', [])) <= 200

    def test_per_page_rejects_non_numeric(self):
        client = TestClient(_worklist_app(['WORKLIST_READ']))
        resp = client.get('/worklist?per_page=abc')
        assert resp.status_code == 422

    def test_per_page_negative_is_rejected(self):
        client = TestClient(_worklist_app(['WORKLIST_READ']))
        resp = client.get('/worklist?per_page=-1')
        assert resp.status_code == 422
```

**GREEN:** Add clamping in `backend/api/worklist.py`:
```python
try:
    page = max(1, int(request.query_params.get('page', '1')))
    per_page = min(200, max(1, int(request.query_params.get('per_page', '20'))))
except (TypeError, ValueError):
    return validation_error('Invalid pagination parameters')
```

**REFACTOR:** Also reduce `ScheduleBoard.tsx:96` from `per_page: 500` to `per_page: 200`.

---

### TDD Cycle 2: F-02 — Patient-existence check in order-less booking

**RED:**
```python
# Already in test_scheduling_engine.py as TestOrderlessPatientCheck
# But engine.py does NOT implement the check yet — tests would fail
# in production (mocked in unit tests). Need integration test:

# backend/tests/test_scheduling_engine.py
class TestOrderlessPatientCheck:
    """Tests already written — verify impl makes them pass."""

    def test_orderless_book_rejects_unknown_patient(self):
        # Already exists — but engine doesn't have the impl yet
        ...

    def test_orderless_book_accepts_known_patient(self):
        # Already exists
        ...
```

**GREEN:** Add to `SchedulingEngine.book()`:
```python
if not order_id and patient_id:
    # R5-06: refuse phantom-patient bookings.
    patients_repo = None
    from db.frontdesk import FrontDesk
    patients_repo = self._patients or FrontDesk(conn)
    patient = await patients_repo.get_by_mrn(patient_id)
    if patient is None:
        raise ValueError(f'Patient {patient_id} not found')
elif order is not None:
    if order.get('patient_id') != patient_id:
        raise SchedulingConflict(
            'order.patient_id and booking patient_id must match')
```

**REFACTOR:** Inject `patients` repo in `__init__` for testability. Update `_repos()`.

---

### TDD Cycle 3: F-03 — Cancelled slot release

**RED:**
```python
# Tests already exist in test_scheduling_engine.py:
# TestCancelledSlotRelease and TestAvailableSlots.test_available_slots_treats_cancelled_as_free

# Also need integration test with real DB:
# backend/tests/test_ris_appointments.py — extend with:
class TestCancelledSlotRelease:
    def test_cancelled_appointment_does_not_block_new_booking(self):
        # Book at 09:00, cancel it, book again at 09:00 — must succeed
```

**GREEN:** Filter cancelled from `for_resource` query in `db/ris_appointments.py`:
```python
# In RisAppointments.for_resource():
& (self.table.status != 'CANCELLED')
```

And update EXCLUDE constraint in a migration:
```sql
ALTER TABLE ris_appointments DROP CONSTRAINT no_double_book;
ALTER TABLE ris_appointments ADD CONSTRAINT no_double_book
    EXCLUDE USING gist (
        resource_id WITH =,
        tstzrange(start_time, end_time) WITH &&
    ) WHERE (status IS DISTINCT FROM 'CANCELLED');
```

**REFACTOR:** Add data migration to delete existing CANCELLED rows.

---

### TDD Cycle 4: F-08 — Whitespace override strip

**RED:**
```python
# Test already exists: TestRequestHardening.test_override_reason_whitespace_only
```

**GREEN:** In `SchedulingEngine.book()`:
```python
if override_reason:
    override_reason = override_reason.strip()
if not override_reason:
    override_reason = ''
```

---

### TDD Cycle 5: F-06 — Date validation (422 not 500)

**RED:**
```python
# Tests already exist in test_ris_scheduling_api.py TestRequestHardening
# But engine._as_date also needs guard:
class TestDateValidation:
    def test_engine_rejects_non_iso_date(self):
        with pytest.raises(ValueError):
            SchedulingEngine._as_date('Aug-20')
```

**GREEN:** Add try/except in scheduling.py handlers:
```python
try:
    day_parsed = date.fromisoformat(day)
except ValueError:
    return api_error('VALIDATION', f'Invalid date format: {day}', status=422)
```

---

### TDD Cycle 6: D1 — Canonical modality list

**RED:**
```typescript
// frontend/src/test/__tests__/modalities.test.ts
import { MODALITIES, isValidModality } from '../common/modalities';

test('canonical list has no duplicates', () => {
  expect(new Set(MODALITIES).size).toBe(MODALITIES.length);
});

test('MR and MRI are both recognized', () => {
  expect(isValidModality('MR')).toBe(true);
  expect(isValidModality('MRI')).toBe(true);
});
```

**GREEN:** Create `frontend/src/common/modalities.ts`:
```typescript
export const MODALITIES = [
  'CT', 'MR', 'MRI', 'PET', 'DX', 'US', 'MG', 'FL', 'XA', 'NM',
] as const;
export type Modality = (typeof MODALITIES)[number];
export const isValidModality = (m: string): m is Modality =>
  (MODALITIES as readonly string[]).includes(m);
```

**REFACTOR:** Replace all 5 inline arrays with imports from this module.

---

### TDD Cycle 7: R1 — ScheduleBoard seq guard

**RED:**
```typescript
// frontend/src/test/ScheduleBoard.test.tsx
it('does not paint stale data from an earlier day-change', async () => {
  // Simulate rapid day changes: fetch for day 1 slow, day 2 fast
  // Assert day 2 data wins (day 1 response discarded)
});
```

**GREEN:** Add `useRef(0)` seq guard matching CalendarView pattern.

---

### TDD Cycle 8: P1 — Permission gate alignment

**RED:**
```typescript
// frontend/src/test/route-gates.test.tsx
it('allows WORKLIST_READ user to access /schedule-board', () => {
  seedUser(['WORKLIST_READ']);
  render(<MemoryRouter><App /></MemoryRouter>);
  expect(screen.getByText('Schedule Board')).toBeInTheDocument();
});
```

**GREEN:** Align route gate to accept both `WORKLIST_READ` and `SCHEDULE_READ`.

---

## Sprint S5 — MWL/MPPS + Tracking Board

**Goal:** Modality pulls MWL via DICOM C-FIND, performs exam, MPPS updates tracking live < 5s.
**Depends on:** S4.5 gate green (all P0/P1 fixes merged)

### TDD Pipeline (vertical slices)

| Cycle | Task | RED | GREEN | REFACTOR |
|-------|------|-----|-------|----------|
| S5.1 | MWL SCP service | Test C-FIND returns worklist entries | Implement `services/mwl_scp/service.py` | Extract DICOM dataset builder |
| S5.2 | MWL query filters | Test station_ae, name, modality filters | Add filter support in C-FIND handler | — |
| S5.3 | ALTER worklist_entries | Test migration runs cleanly | Add MWL columns via Alembic | — |
| S5.4 | MWL conformance tests | Test DICOM MWL IOD compliance | Wire conformance assertions | — |
| S5.5 | MPPS consumer | Test N-CREATE → IN_PROGRESS | Implement `services/mpps_consumer/service.py` | — |
| S5.6 | MPPS events table | Test event persistence | Create `db/ris_mpps.py` + migration | — |
| S5.7 | MPPS → PACS echo | Test study status update on N-SET | Wire to dcm_server.py | — |
| S5.8 | Tracking board API | Test live exam list + filters + pagination | Extend `api/worklist.py` | — |
| S5.9 | KPI strip API | Test volume/in-progress/overdue counts | Add KPI endpoint | — |
| S5.10 | Status update API | Test manual status with guard validation | Add PUT /ris/tracking/{id}/status | — |
| S5.11 | Status timeline API | Test chronological status changes | Add timeline endpoint | — |
| S5.12 | Tracking board UI | Test live board render | Create `TrackingBoard.tsx` | — |
| S5.13 | KPI strip UI | Test KPI render | Create `KpiStrip.tsx` | — |
| S5.14 | Filters + search UI | Test modality/site/status filters | Extend TrackingBoard | — |
| S5.15 | Row actions UI | Test check-in/arrived/cancel actions | Extend TrackingBoard | — |
| S5.16 | MWL E2E | Test book → MWL → C-FIND → MPPS → tracking | Integration test | — |
| S5.17 | MPPS latency | Test < 5s p95 | Instrument histogram | — |
| S5.18 | RLS on tracking | Test cross-facility denied | Add RLS policies | — |

### Exit Gate

```bash
# Backend
cd backend && python -m pytest tests/ -v --tb=short -W error::Warning

# Frontend
cd frontend && npx tsc --noEmit && npx vitest run

# MWL conformance
cd backend && python -m pytest tests/integration/test_mwl_conformance.py -v

# MPPS E2E
cd backend && python -m pytest tests/integration/test_mpps_e2e.py -v
```

---

## Execution Order (vertical-slice TDD)

```
S4.5 (8 cycles, ~2 days):
  F-01 → F-02 → F-03 → F-08 → F-06 → D1 → R1 → P1

S5 (18 cycles, ~8 days):
  S5.1 → S5.2 → S5.3 → S5.4 → S5.5 → S5.6 → S5.7
  → S5.8 → S5.9 → S5.10 → S5.11
  → S5.12 → S5.13 → S5.14 → S5.15
  → S5.16 → S5.17 → S5.18
```

Each cycle: write ONE test → implement → verify → refactor → next.
