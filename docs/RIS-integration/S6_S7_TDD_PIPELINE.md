# S6-S7 TDD Implementation Pipeline — MWL/MPPS + Tracking Board

**Date:** 2026-08-20
**Baseline:** 1985 backend tests + frontend test suite passing
**Source:** CONSOLIDATED_SPRINT_PLAN.md S6-S7, sprint_mvp_04 detail
**Pattern:** Vertical-slice TDD per the TDD skill (RED → GREEN → REFACTOR)

---

## 1. Current State Assessment

### Already Implemented (S6-S7 scope)
| ID | Task | Status | Location |
|----|------|--------|----------|
| S6-01 | MWL SCP C-FIND handler | ✅ DONE | `dcm/server.py` |
| S6-03 | Station AE endpoint | ✅ DONE | `api/worklist.py:WorklistStationAeHandler` |
| S6-04 | MWL conformance tests | ✅ DONE | `tests/test_mwl_handler.py` |
| S6-05 | MWL REST API + filters + pagination | ✅ DONE | `api/worklist.py:WorklistHandler` |
| S6-06 | worklist_entries MWL fields | ✅ DONE | `db/worklist.py` (full schema) |
| MWL sync | ADR-028 MWL-RS mirror | ✅ DONE | `api/mwl_sync.py` |

### Remaining (to implement)
| ID | Task | Effort | Dep |
|----|------|--------|-----|
| S6-02 | MWL priority sort (STAT first) | 1.0 | S6-05 |
| S6-07 | MPPS consumer service | 3.0 | S6-01 |
| S6-08 | ris_mpps_events table + migration | 1.0 | — |
| S6-12 | MPPS → exam status linkage API | 1.5 | S6-07 |
| S6-13 | Tracking board API | 2.5 | S6-12 |
| S6-14 | KPI strip API | 1.0 | S6-13 |
| S6-15 | Status update API | 1.5 | S6-13 |
| S6-16 | Status timeline API | 0.5 | S6-13 |
| S6-17 | Tracking board UI (TrackingBoard.tsx) | 5.0 | S6-13 |
| S6-18 | KPI strip UI (KpiStrip.tsx) | 2.0 | S6-14 |
| S6-19 | Filters + search UI | 3.0 | S6-17 |
| S6-20 | Row actions UI | 2.5 | S6-15 |
| S6-21 | Critical-result badges | 1.0 | S6-17 |
| S6-22 | MWL E2E test | 2.0 | all |
| S6-25 | MPPS → tracking latency test | 1.0 | S6-07 |
| S6-26 | RLS on tracking | 0.5 | S6-13 |

---

## 2. Dependency Graph

```
S6-08 (mpps_events table) ──────────────┐
                                         ├──► S6-07 (MPPS consumer) ──┐
S6-01 (MWL SCP) ────────────────────────┘                            │
                                                                      │
S6-05 (MWL REST API) ──► S6-02 (priority sort)                       │
                                                                      │
S6-07 ──► S6-12 (exam status linkage) ──┐                            │
                                         │                            │
S6-12 ──► S6-13 (tracking board API) ───┴────────────────────────────┘
                                              │
                 ┌────────────────────────────┤
                 │                │           │
            S6-14 (KPI API)  S6-15 (status)  S6-16 (timeline)
                 │                │           │
                 │                │           │
            S6-18 (KPI UI)  S6-20 (actions)  │
                 │                │           │
                 │                │           │
            S6-17 (TrackingBoard UI) ────────┘
                 │
            S6-19 (filters) + S6-21 (critical badges)
                 │
            S6-22, S6-25, S6-26 (E2E + RLS)
```

---

## 3. TDD Pipeline (8 Vertical Slices)

### Cycle 1: MPPS Events Table + Consumer Service
**Files:** `db/ris_mpps.py`, `services/mpps_consumer/__init__.py`, `services/mpps_consumer/service.py`, Alembic migration, `tests/test_mpps_consumer.py`

**RED:** Create `tests/test_mpps_consumer.py`:
```python
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

class TestMppsEventsTable:
    """S6-08: ris_mpps_events table persists MPPS lifecycle events."""

    @pytest.mark.asyncio
    async def test_create_event(self):
        """N-CREATE event is persisted with IN_PROGRESS status."""
        ...

    @pytest.mark.asyncio
    async def test_update_event(self):
        """N-SET event updates existing row to COMPLETED status."""
        ...

    @pytest.mark.asyncio
    async def test_event_audit_trail(self):
        """Events carry timestamps and raw DICOM message."""
        ...

class TestMppsConsumer:
    """S6-07: MPPS consumer handles N-CREATE and N-SET."""

    def test_service_exists(self):
        from services.mpps_consumer.service import MppsConsumer
        assert callable(MppsConsumer)

    @pytest.mark.asyncio
    async def test_n_create_sets_in_progress(self):
        """N-CREATE with accession → worklist entry → IN_PROGRESS."""
        ...

    @pytest.mark.asyncio
    async def test_n_set_sets_completed(self):
        """N-SET with COMPLETED → worklist entry → performed + exam status."""
        ...

    @pytest.mark.asyncio
    async def test_n_set_discontinued(self):
        """N-SET with DISCONTINUED → worklist entry → cancelled."""
        ...
```

**GREEN:** Implement:
- `db/ris_mpps.py`: RisMppsEvents model (event_type, accession_number, mpps_status, raw_message, timestamps)
- Alembic migration for `ris_mpps_events` table
- `services/mpps_consumer/service.py`: MppsConsumer class with handle_n_create() and handle_n_set()
- Wire to `dcm/server.py` as N-CREATE/N-SET handlers

**REFACTOR:** Extract DICOM status mapping constants.

---

### Cycle 2: MPPS → Exam Status Linkage API
**Files:** `api/exams.py` (extend), `tests/test_mpps_consumer.py`

**RED:** Add to `tests/test_mpps_consumer.py`:
```python
class TestMppsExamLinkage:
    """S6-12: MPPS events drive exam status transitions."""

    @pytest.mark.asyncio
    async def test_n_create_links_exam_to_in_progress(self):
        """N-CREATE with study_uid → exam.status = in_progress."""
        ...

    @pytest.mark.asyncio
    async def test_n_set_links_exam_to_completed(self):
        """N-SET COMPLETED → exam.status = completed."""
        ...

    @pytest.mark.asyncio
    async def test_pacs_echo_triggered_on_status_change(self):
        """Status change triggers PACS echo (async)."""
        ...
```

**GREEN:** Implement in `api/exams.py` or `services/mpps_consumer/service.py`:
- On N-CREATE: find exam by accession → update status to in_progress, store study_uid
- On N-SET COMPLETED: find exam → update status to completed
- On N-SET DISCONTINUED: find exam → update status to discontinued
- Trigger PACS echo (stub/mock for now)

**REFACTOR:** Extract exam status transition helper.

---

### Cycle 3: MWL Priority Sort (STAT First)
**Files:** `db/worklist.py`, `tests/test_mwl_handler.py`

**RED:** Add to `tests/test_mwl_handler.py`:
```python
class TestMwlPrioritySort:
    """S6-02: MWL results prioritize STAT entries first."""

    @pytest.mark.asyncio
    async def test_stat_entries_sort_first(self):
        """STAT priority entries appear before routine in C-FIND results."""
        ...

    @pytest.mark.asyncio
    async def test_priority_sort_within_same_date(self):
        """Within same date, STAT > urgent > routine ordering."""
        ...
```

**GREEN:** Update `db/worklist.py` Worklist.search() to order by priority (STAT first), then by scheduled_date/time.

**REFACTOR:** Extract priority sort order constant.

---

### Cycle 4: Tracking Board API
**Files:** `api/worklist.py` (extend), `tests/test_worklist_api.py`

**RED:** Add to `tests/test_worklist_api.py`:
```python
class TestTrackingBoardAPI:
    """S6-13: Live tracking board API with filters and pagination."""

    @pytest.mark.asyncio
    async def test_tracking_endpoint_returns_exam_list(self):
        """GET /api/ris/tracking returns exams with patient, status, priority."""
        ...

    @pytest.mark.asyncio
    async def test_tracking_filters_by_modality(self):
        """Filter by modality returns matching exams."""
        ...

    @pytest.mark.asyncio
    async def test_tracking_filters_by_status(self):
        """Filter by status returns matching exams."""
        ...

    @pytest.mark.asyncio
    async def test_tracking_pagination(self):
        """Pagination works with page and per_page params."""
        ...

    @pytest.mark.asyncio
    async def test_tracking_includes_worklist_data(self):
        """Tracking response includes worklist entry data."""
        ...
```

**GREEN:** Implement `TrackingHandler` in `api/worklist.py`:
- `GET /api/ris/tracking` — joins worklist_entries + exams, filters by modality/status/priority/date, paginated
- Response includes: patient (masked), accession, modality, procedure, scheduled time, room, status, priority

**REFACTOR:** Extract tracking query builder.

---

### Cycle 5: KPI Strip + Status Timeline + Status Update APIs
**Files:** `api/worklist.py` (extend), `tests/test_worklist_api.py`

**RED:**
```python
class TestKpiStripAPI:
    """S6-14: KPI strip returns live counts."""

    def test_returns_volume_in_progress_overdue_stat(self):
        ...

class TestStatusTimelineAPI:
    """S6-16: Status timeline shows lifecycle changes."""

    def test_returns_ordered_status_transitions(self):
        ...

class TestStatusUpdateAPI:
    """S6-15: Manual status update with guard validation."""

    def test_valid_transition_succeeds(self):
        ...

    def test_invalid_transition_rejected(self):
        ...
```

**GREEN:** Implement:
- `GET /api/ris/tracking/kpi` — returns today's volume, in_progress, awaiting_read, overdue, stat_count
- `GET /api/ris/tracking/{id}/timeline` — returns ordered status changes from audit_log
- `PUT /api/ris/tracking/{id}/status` — manual status update with valid-transition guard + audit

**REFACTOR:** Extract status machine constants.

---

### Cycle 6: TrackingBoard.tsx UI
**Files:** `frontend/src/worklist/TrackingBoard.tsx`, `frontend/src/worklist/TrackingBoard.css`, `frontend/src/test/TrackingBoard.test.tsx`

**RED:**
```typescript
// frontend/src/test/TrackingBoard.test.tsx
describe('TrackingBoard', () => {
  it('renders exam list from API', async () => {
    render(<TrackingBoard />);
    expect(screen.getByText('Loading')).toBeInTheDocument();
    await waitFor(() => {
      expect(screen.getByText('Smith^John')).toBeInTheDocument();
    });
  });

  it('shows status badges with correct colors', async () => {
    render(<TrackingBoard />);
    await waitFor(() => {
      expect(screen.getByText('in_progress')).toBeInTheDocument();
    });
  });

  it('shows priority badges', async () => {
    render(<TrackingBoard />);
    await waitFor(() => {
      expect(screen.getByText('STAT')).toBeInTheDocument();
    });
  });
});
```

**GREEN:** Create `TrackingBoard.tsx`:
- Ant Design Table with columns: Patient, Accession, Modality, Procedure, Scheduled, Room, Status, Priority
- Status colors: scheduled=blue, in_progress=orange, completed=green, cancelled=red
- Priority badges: stat=red, urgent=orange, routine=default
- Auto-refresh every 30s
- `withSidebar` wrapper

**REFACTOR:** Extract status color mapping to shared constants.

---

### Cycle 7: KpiStrip + Filters + Row Actions
**Files:** `frontend/src/worklist/KpiStrip.tsx`, extend `TrackingBoard.tsx`, `frontend/src/test/TrackingBoard.test.tsx`

**RED:**
```typescript
describe('KpiStrip', () => {
  it('displays volume, in-progress, overdue counts', () => {
    render(<KpiStrip data={{ volume: 42, in_progress: 5, overdue: 2 }} />);
    expect(screen.getByText('42')).toBeInTheDocument();
  });
});

describe('TrackingBoard filters', () => {
  it('filters by modality', async () => {
    render(<TrackingBoard />);
    // ...select CT from modality filter...
  });

  it('filters by status', async () => {
    render(<TrackingBoard />);
    // ...select in_progress from status filter...
  });
});
```

**GREEN:** Implement:
- `KpiStrip.tsx`: Ant Design Statistic cards for volume, in_progress, awaiting_read, overdue, stat
- Extend `TrackingBoard.tsx` with filter controls (Select components for modality, status, priority)
- Row actions: Check-in, Mark Arrived, Reschedule, Cancel (with status guards)

**REFACTOR:** Extract filter controls to shared component.

---

### Cycle 8: MWL/MPPS E2E + RLS Tests
**Files:** `tests/test_ris_e2e.py` (extend), `tests/test_ris_tenant_isolation.py` (extend)

**RED:**
```python
class TestMwlMppsE2E:
    """S6-22: Full MWL → MPPS → tracking flow."""

    @pytest.mark.asyncio
    async def test_book_to_mwl_to_mpps_to_tracking(self):
        """Book appointment → MWL entry → C-FIND → MPPS N-CREATE → IN_PROGRESS →
        MPPS N-SET → COMPLETED → tracking board updates."""
        ...

class TestTrackingRLS:
    """S6-26: Cross-facility tracking denied."""

    @pytest.mark.asyncio
    async def test_cross_facility_tracking_denied(self):
        ...
```

**GREEN:** Wire the complete flow: book → MWL → MPPS → tracking. Implement RLS policies on tracking queries.

**REFACTOR:** Extract shared test fixtures.

---

## 4. Execution Order

```
Week 1 (Backend):
  Day 1-2: Cycle 1 (MPPS table + consumer) + Cycle 2 (exam linkage)
  Day 3:   Cycle 3 (MWL priority sort)
  Day 4:   Cycle 4 (tracking board API)
  Day 5:   Cycle 5 (KPI + timeline + status APIs)

Week 2 (Frontend + E2E):
  Day 1-2: Cycle 6 (TrackingBoard.tsx)
  Day 3:   Cycle 7 (KpiStrip + filters + row actions)
  Day 4:   Cycle 8 (E2E + RLS tests)
  Day 5:   Exit gate + cleanup
```

## 5. Exit Gate

```bash
# Backend
cd backend && .venv/bin/python -m pytest tests/ -v --tb=short -W error::Warning

# Frontend
cd frontend && npx tsc --noEmit && npx vitest run

# MPPS conformance
cd backend && .venv/bin/python -m pytest tests/test_mpps_consumer.py -v

# MWL E2E
cd backend && .venv/bin/python -m pytest tests/test_ris_e2e.py -k "mwl_mpps" -v
```
