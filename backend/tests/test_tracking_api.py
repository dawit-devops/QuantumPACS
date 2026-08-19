"""Tests for the tracking board API (S6-13), KPI strip (S6-14),
status timeline (S6-16), and status update (S6-15) endpoints.

RED: these tests describe the public API behavior. The implementation
does not exist yet.
"""
from unittest.mock import AsyncMock, patch, MagicMock

import pytest
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.routing import Route
from starlette.testclient import TestClient
from starlette.exceptions import HTTPException

from api.auth import User
from api.validate import validation_exception_handler, _ValidationException


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


# ---------------------------------------------------------------------------
# S6-14: KPI strip API tests
# ---------------------------------------------------------------------------

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
        # fetchval returns counts in order: volume, in_progress, awaiting, overdue, stat
        mock_conn.fetchval = AsyncMock(side_effect=[42, 5, 8, 2, 3])
        with patch('api.worklist.get_conn', return_value=mock_conn):
            resp = client.get('/ris/tracking/kpi')
        assert resp.status_code == 200
        data = resp.json()
        assert data['volume'] == 42
        assert data['in_progress'] == 5
        assert data['awaiting_read'] == 8
        assert data['overdue'] == 2
        assert data['stat_count'] == 3


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
        mock_conn.execute = AsyncMock()
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
