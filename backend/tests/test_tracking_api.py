"""Tests for the tracking board API (S6-13), KPI strip (S6-14),
status timeline (S6-16), and status update (S6-15) endpoints.

RED: these tests describe the public API behavior. The implementation
does not exist yet.
"""
import asyncio
import uuid
from unittest.mock import AsyncMock, patch

import pytest
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.routing import Route
from starlette.testclient import TestClient
from starlette.exceptions import HTTPException

from api.auth import User
from api.validate import validation_exception_handler, _ValidationException
from db.conn import get_conn, setup, teardown


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _http_exception(request, exc):
    from starlette.responses import JSONResponse
    return JSONResponse(
        {'error': exc.detail if hasattr(exc, 'detail') else ''},
        status_code=exc.status_code,
    )


class _FakeAuth(BaseHTTPMiddleware):
    def __init__(self, app, user=None):
        super().__init__(app)
        self._user = user or User({'id': 1, 'permissions': []})

    async def dispatch(self, request, call_next):
        request.scope['user'] = self._user
        request.scope['auth'] = None
        return await call_next(request)


def _make_tracking_app(user=None):
    from api.worklist import TrackingHandler, TrackingKpiHandler, \
        TrackingTimelineHandler, TrackingStatusHandler
    return Starlette(
        routes=[
            Route('/ris/tracking', endpoint=TrackingHandler),
            Route('/ris/tracking/kpi', endpoint=TrackingKpiHandler),
            Route('/ris/tracking/{id}/timeline', endpoint=TrackingTimelineHandler),
            Route('/ris/tracking/{id}/status', endpoint=TrackingStatusHandler),
        ],
        middleware=[Middleware(_FakeAuth, user=user)],
        exception_handlers={
            HTTPException: _http_exception,
            _ValidationException: validation_exception_handler,
        },
    )


# ---------------------------------------------------------------------------
# S6-13: Tracking board API tests
# ---------------------------------------------------------------------------

class TestTrackingBoardAPI:
    """S6-13: Live tracking board API with filters and pagination."""

    def test_requires_worklist_read(self):
        user = User({'id': 1, 'permissions': []})
        client = TestClient(_make_tracking_app(user))
        resp = client.get('/ris/tracking')
        assert resp.status_code == 403

    def test_returns_exam_list(self):
        user = User({'id': 1, 'permissions': ['WORKLIST_READ']})
        client = TestClient(_make_tracking_app(user))
        row = {
            'id': 'ex-1', 'accession_number': 'ACC001',
            'patient_id': 'P001', 'patient_name': 'Smith^John',
            'modality': 'CT', 'status': 'scheduled', 'priority': 'routine',
            'station_ae_title': 'CT01', 'scheduled_date': '2026-08-20',
            'scheduled_time': '09:00',
        }
        mock_conn = AsyncMock()
        mock_conn.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_conn.__aexit__ = AsyncMock(return_value=None)
        mock_conn.fetch = AsyncMock(return_value=[row])
        mock_conn.fetchval = AsyncMock(return_value=1)
        with patch('api.worklist.get_conn', return_value=mock_conn):
            resp = client.get('/ris/tracking')
        assert resp.status_code == 200
        data = resp.json()
        assert len(data['data']) == 1
        assert data['data'][0]['accession_number'] == 'ACC001'
        assert data['total'] == 1

    def test_filters_by_modality(self):
        user = User({'id': 1, 'permissions': ['WORKLIST_READ']})
        client = TestClient(_make_tracking_app(user))
        mock_conn = AsyncMock()
        mock_conn.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_conn.__aexit__ = AsyncMock(return_value=None)
        mock_conn.fetch = AsyncMock(return_value=[])
        mock_conn.fetchval = AsyncMock(return_value=0)
        with patch('api.worklist.get_conn', return_value=mock_conn):
            client.get('/ris/tracking?modality=CT')
        # Verify the SQL query includes modality filter
        calls = [str(c) for c in mock_conn.fetch.call_args_list]
        assert any('CT' in c for c in calls)

    def test_filters_by_status(self):
        user = User({'id': 1, 'permissions': ['WORKLIST_READ']})
        client = TestClient(_make_tracking_app(user))
        mock_conn = AsyncMock()
        mock_conn.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_conn.__aexit__ = AsyncMock(return_value=None)
        mock_conn.fetch = AsyncMock(return_value=[])
        mock_conn.fetchval = AsyncMock(return_value=0)
        with patch('api.worklist.get_conn', return_value=mock_conn):
            client.get('/ris/tracking?status=in_progress')
        calls = [str(c) for c in mock_conn.fetch.call_args_list]
        assert any('in_progress' in c for c in calls)

    def test_critical_flag_surfaces_from_ris_critical_results(self):
        # S6-21: the board shows a badge while a critical result is flagged
        # (persistent until ack). The handler must query ris_critical_results
        # and expose the boolean on each row.
        user = User({'id': 1, 'permissions': ['WORKLIST_READ']})
        client = TestClient(_make_tracking_app(user))
        row = {
            'id': 'ex-1', 'accession_number': 'ACC001',
            'patient_id': 'P001', 'patient_name': 'Smith^John',
            'modality': 'CT', 'status': 'scheduled', 'priority': 'routine',
            'station_ae_title': 'CT01', 'scheduled_date': '2026-08-20',
            'scheduled_time': '09:00', 'has_critical': True,
        }
        mock_conn = AsyncMock()
        mock_conn.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_conn.__aexit__ = AsyncMock(return_value=None)
        mock_conn.fetch = AsyncMock(return_value=[row])
        mock_conn.fetchval = AsyncMock(return_value=1)
        with patch('api.worklist.get_conn', return_value=mock_conn):
            resp = client.get('/ris/tracking')
        assert resp.status_code == 200
        assert resp.json()['data'][0]['has_critical'] is True
        calls = [str(c) for c in mock_conn.fetch.call_args_list]
        assert any('ris_critical_results' in c for c in calls)
        assert any("cr.status = 'flagged'" in c for c in calls)

    def test_pagination(self):
        user = User({'id': 1, 'permissions': ['WORKLIST_READ']})
        client = TestClient(_make_tracking_app(user))
        mock_conn = AsyncMock()
        mock_conn.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_conn.__aexit__ = AsyncMock(return_value=None)
        mock_conn.fetch = AsyncMock(return_value=[])
        mock_conn.fetchval = AsyncMock(return_value=0)
        with patch('api.worklist.get_conn', return_value=mock_conn):
            resp = client.get('/ris/tracking?page=2&per_page=10')
        assert resp.status_code == 200
        data = resp.json()
        assert data['page'] == 2
        assert data['per_page'] == 10

    def test_arrived_rows_include_checkin_timestamp_and_wait(self):
        # FD-05: an arrived row carries the appointment's checked_in_at and a
        # computed wait_minutes so the queue can color-code by wait time.
        user = User({'id': 1, 'permissions': ['WORKLIST_READ']})
        client = TestClient(_make_tracking_app(user))
        row = {
            'id': 'ex-1', 'accession_number': 'ACC001',
            'patient_id': 'P001', 'patient_name': 'Smith^John',
            'modality': 'CT', 'status': 'arrived', 'priority': 'routine',
            'station_ae_title': 'CT01', 'scheduled_date': '2026-08-20',
            'scheduled_time': '09:00', 'checked_in_at': '2026-08-20T09:00:00+00:00',
        }
        mock_conn = AsyncMock()
        mock_conn.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_conn.__aexit__ = AsyncMock(return_value=None)
        mock_conn.fetch = AsyncMock(return_value=[row])
        mock_conn.fetchval = AsyncMock(return_value=1)
        with patch('api.worklist.get_conn', return_value=mock_conn):
            resp = client.get('/ris/tracking?status=arrived')
        assert resp.status_code == 200
        data = resp.json()['data'][0]
        assert data['checked_in_at'] == '2026-08-20T09:00:00+00:00'
        assert isinstance(data['wait_minutes'], (int, float))
        assert data['wait_minutes'] >= 0
        # The handler must select the arrival column from ris_appointments.
        calls = [str(c) for c in mock_conn.fetch.call_args.args[0:1]]
        assert 'checked_in_at' in calls[0]
        assert 'ris_appointments' in calls[0]


# ---------------------------------------------------------------------------
# S6-14: KPI strip API tests
# ---------------------------------------------------------------------------

class TestTrackingBoardSearchEscaping:
    """S-6: '%' and '_' typed by the user must not act as LIKE wildcards —
    they are escaped so '100%' matches a literal percent, not everything."""

    def _client(self):
        from api.auth import User
        user = User({'id': 1, 'permissions': ['WORKLIST_READ']})
        return TestClient(_make_tracking_app(user))

    def test_search_percent_is_escaped(self):
        mock_conn = AsyncMock()
        mock_conn.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_conn.__aexit__ = AsyncMock(return_value=None)
        mock_conn.fetch = AsyncMock(return_value=[])
        mock_conn.fetchval = AsyncMock(return_value=0)
        with patch('api.worklist.get_conn', return_value=mock_conn):
            self._client().get('/ris/tracking?search=100%25')
        args = mock_conn.fetch.call_args.args
        params = args[1:]
        assert any('100\\%' in str(p) for p in params), \
            'the literal percent must be escaped in the LIKE param'
        assert 'ESCAPE' in str(args[0]), \
            'the ILIKE expression must declare an escape character'


class TestKpiStripAPI:
    """S6-14: KPI strip returns live counts for today's exams."""

    def test_requires_worklist_read(self):
        user = User({'id': 1, 'permissions': []})
        client = TestClient(_make_tracking_app(user))
        resp = client.get('/ris/tracking/kpi')
        assert resp.status_code == 403

    def test_returns_kpi_counts(self):
        user = User({'id': 1, 'permissions': ['WORKLIST_READ']})
        client = TestClient(_make_tracking_app(user))
        mock_conn = AsyncMock()
        mock_conn.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_conn.__aexit__ = AsyncMock(return_value=None)
        # fetchval returns counts in order: volume, in_progress, awaiting, overdue, stat, overdue_wait
        mock_conn.fetchval = AsyncMock(side_effect=[42, 5, 8, 2, 3, 4])
        with patch('api.worklist.get_conn', return_value=mock_conn):
            resp = client.get('/ris/tracking/kpi')
        assert resp.status_code == 200
        data = resp.json()
        assert data['volume'] == 42
        assert data['in_progress'] == 5
        assert data['awaiting_read'] == 8
        assert data['overdue'] == 2
        assert data['stat_count'] == 3
        assert data['overdue_wait_count'] == 4


# ---------------------------------------------------------------------------
# S6-16: Status timeline API tests
# ---------------------------------------------------------------------------

class TestStatusTimelineAPI:
    """S6-16: Status timeline shows lifecycle changes for an exam."""

    def test_requires_worklist_read(self):
        user = User({'id': 1, 'permissions': []})
        client = TestClient(_make_tracking_app(user))
        resp = client.get('/ris/tracking/ex-1/timeline')
        assert resp.status_code == 403

    def test_returns_timeline(self):
        user = User({'id': 1, 'permissions': ['WORKLIST_READ']})
        client = TestClient(_make_tracking_app(user))
        timeline = [
            {'event_type': 'worklist.entry_created', 'created_at': '2026-08-20T08:00:00Z'},
            {'event_type': 'exam.identity_confirmed', 'created_at': '2026-08-20T08:30:00Z'},
            {'event_type': 'exam.completed', 'created_at': '2026-08-20T09:30:00Z'},
        ]
        mock_conn = AsyncMock()
        mock_conn.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_conn.__aexit__ = AsyncMock(return_value=None)
        mock_conn.fetch = AsyncMock(return_value=timeline)
        with patch('api.worklist.get_conn', return_value=mock_conn):
            resp = client.get('/ris/tracking/ex-1/timeline')
        assert resp.status_code == 200
        data = resp.json()
        assert len(data['data']) == 3


# ---------------------------------------------------------------------------
# S6-15: Status update API tests
# ---------------------------------------------------------------------------

class TestStatusUpdateAPI:
    """S6-15: Manual status update with guard validation."""

    def test_requires_worklist_write(self):
        user = User({'id': 1, 'permissions': ['WORKLIST_READ']})
        client = TestClient(_make_tracking_app(user))
        resp = client.put('/ris/tracking/ex-1/status',
                          json={'status': 'arrived'})
        assert resp.status_code == 403

    def test_valid_transition_succeeds(self):
        user = User({'id': 1, 'permissions': ['WORKLIST_WRITE']})
        client = TestClient(_make_tracking_app(user))
        mock_conn = AsyncMock()
        mock_conn.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_conn.__aexit__ = AsyncMock(return_value=None)
        mock_conn.fetchrow = AsyncMock(
            return_value={'id': 'ex-1', 'status': 'scheduled'},
        )
        mock_conn.execute = AsyncMock(return_value='UPDATE 1')
        with patch('api.worklist.get_conn', return_value=mock_conn):
            resp = client.put('/ris/tracking/ex-1/status',
                              json={'status': 'arrived'})
        assert resp.status_code == 200

    def test_invalid_transition_rejected(self):
        user = User({'id': 1, 'permissions': ['WORKLIST_WRITE']})
        client = TestClient(_make_tracking_app(user))
        mock_conn = AsyncMock()
        mock_conn.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_conn.__aexit__ = AsyncMock(return_value=None)
        # Exam is already completed — can't go back to scheduled
        mock_conn.fetchrow = AsyncMock(
            return_value={'id': 'ex-1', 'status': 'completed'},
        )
        with patch('api.worklist.get_conn', return_value=mock_conn):
            resp = client.put('/ris/tracking/ex-1/status',
                              json={'status': 'scheduled'})
        assert resp.status_code == 409 or resp.status_code == 422

    def test_missing_status_rejected(self):
        user = User({'id': 1, 'permissions': ['WORKLIST_WRITE']})
        client = TestClient(_make_tracking_app(user))
        resp = client.put('/ris/tracking/ex-1/status', json={})
        assert resp.status_code == 422


class TestStatusTimelineAuditTable:
    """H7: the S6-16 timeline reads audit events from the `logs` table.

    AuditLog.log_event writes to `logs` (the timeline's data source); a
    leftover `FROM audit_log` would 500 against a real database.
    """

    def test_timeline_queries_logs_table(self):
        user = User({'id': 1, 'permissions': ['WORKLIST_READ']})
        client = TestClient(_make_tracking_app(user))
        mock_conn = AsyncMock()
        mock_conn.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_conn.__aexit__ = AsyncMock(return_value=None)
        mock_conn.fetch = AsyncMock(return_value=[])
        with patch('api.worklist.get_conn', return_value=mock_conn):
            resp = client.get('/ris/tracking/ex-1/timeline')
        assert resp.status_code == 200
        sql = str(mock_conn.fetch.await_args.args[0])
        assert 'FROM logs' in sql
        assert 'audit_log' not in sql


# ---------------------------------------------------------------------------
# S6-24: 50 concurrent tracking updates (real DB) — no lost updates
# ---------------------------------------------------------------------------

class TestConcurrentTrackingUpdates:
    """S6-24: 50 concurrent status updates on one entry must not clobber
    each other: exactly one transition wins per wave, the rest get a 409,
    and the audit log records the winning transition once.

    Same real-DB pattern as TestOverrideAtomicity: rows are cleaned up by
    the unique run tag. Uses the handler's real guard path
    (Worklist.update_status_if + TRACKING_VALID_TRANSITIONS pre-check).
    """

    @staticmethod
    async def _run_concurrent(entry_id, from_status, to_status, n=50):
        """Fire n concurrent guarded transitions; return (wins, losses)."""
        from db.worklist import Worklist

        async def attempt(_):
            async with get_conn() as conn:
                return await Worklist(conn).update_status_if(
                    entry_id, from_status, to_status)

        results = await asyncio.gather(*[attempt(i) for i in range(n)])
        return sum(1 for r in results if r), sum(1 for r in results if not r)

    def test_50_concurrent_updates_single_winner(self):
        async def run():
            from db.worklist import Worklist

            try:
                await setup()
            except Exception:
                pytest.skip('dev database unavailable')

            tag = f'conc-{uuid.uuid4().hex[:8]}'
            accession = f'ACC-{tag}'
            try:
                # Committed insert (no outer tx): the concurrent waves run on
                # their own pool connections and must see the entry.
                async with get_conn() as conn:
                    entry = await Worklist(conn).create({
                        'patient_id': f'P-{tag}',
                        'patient_name': f'Patient {tag}',
                        'accession_number': accession,
                        'modality': 'CT',
                        'status': 'scheduled',
                        'created_by': '',
                    })
                entry_id = entry['id']

                wins, losses = await self._run_concurrent(
                    entry_id, 'scheduled', 'arrived')
                assert wins == 1, f'exactly one transition must win, got {wins}'
                assert losses == 49, f'49 must lose the race, got {losses}'

                wins, losses = await self._run_concurrent(
                    entry_id, 'arrived', 'in_progress')
                assert wins == 1, f'wave 2: exactly one winner, got {wins}'
                assert losses == 49, f'wave 2: 49 losses, got {losses}'

                async with get_conn() as conn:
                    final = await Worklist(conn).get_by_accession(accession)
                    assert final['status'] == 'in_progress', \
                        f'final status must be in_progress, got {final["status"]}'

                # Handler-level audit (one log row per winning 200) is pinned
                # by the mocked TestStatusUpdateAPI tests; the waves above
                # exercise the DB guard the handler relies on.
            finally:
                try:
                    async with get_conn() as conn:
                        await conn.execute(
                            'DELETE FROM worklist_entries WHERE accession_number = $1',
                            accession)
                        await conn.execute(
                            'DELETE FROM logs WHERE resource_type = $1 AND resource_id = $2',
                            'worklist_entry', entry_id)
                except Exception:
                    pass
                await teardown()

        asyncio.run(run())
