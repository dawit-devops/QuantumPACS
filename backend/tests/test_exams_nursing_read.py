"""§2.11/G3: NURSING_READ alone passes the exam list/detail READ gates so
the prep queue can deep-link into exam consoles. Writes stay EXAM_WRITE."""
from unittest.mock import AsyncMock, MagicMock, patch

from starlette.applications import Starlette
from starlette.exceptions import HTTPException
from starlette.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.routing import Route
from starlette.testclient import TestClient

from api.auth import User
from api.exams import ExamHandler, ExamsHandler
from api.validate import validation_exception_handler, _ValidationException


class _FakeAuth(BaseHTTPMiddleware):
    def __init__(self, app, user=None):
        super().__init__(app)
        self._user = user

    async def dispatch(self, request, call_next):
        request.scope['user'] = self._user
        request.scope['auth'] = None
        return await call_next(request)


def _http_exception(request, exc):
    from starlette.responses import JSONResponse

    return JSONResponse({'error': exc.detail}, status_code=exc.status_code)


def _make_app(routes, user):
    return Starlette(
        routes=routes,
        middleware=[Middleware(_FakeAuth, user=user)],
        exception_handlers={
            HTTPException: _http_exception,
            _ValidationException: validation_exception_handler,
        },
    )


def _conn_ctx():
    conn = MagicMock()
    # The handlers compose protocol seeding and patient lookups through raw
    # conn calls; keep them inert.
    conn.fetchval = AsyncMock(return_value=0)
    conn.fetch = AsyncMock(return_value=[])
    conn.fetchrow = AsyncMock(return_value=None)
    conn.execute = AsyncMock(return_value='OK')
    return patch(
        'api.exams.get_conn',
        return_value=MagicMock(
            __aenter__=AsyncMock(return_value=conn),
            __aexit__=AsyncMock(return_value=None),
        ),
    )


NURSE = lambda: User({'id': 2, 'permissions': ['NURSING_READ']})  # noqa: E731


def _patch_exams_cls(list_rows=None, exam_row=None):
    mock = MagicMock()
    mock.list_for_technologist = AsyncMock(return_value=list_rows or [])
    mock.get = AsyncMock(return_value=exam_row)
    return patch('api.exams.Exams', return_value=mock), mock


def _patch_detail_children():
    """ExamHandler.get composes acquisitions/safety/incidents/overrides/dose;
    stub them so the read-gate assertion stays focused."""
    acq = MagicMock()
    acq.list_for_exam = AsyncMock(return_value=[])
    acq.dose_totals = AsyncMock(return_value={'total_dlp': 0})
    patches = [
        patch('api.exams.Acquisitions', return_value=acq),
        patch('api.exams.SafetyChecks', return_value=MagicMock(
            list_for_exam=AsyncMock(return_value=[]))),
        patch('api.exams.Incidents', return_value=MagicMock(
            list_for_exam=AsyncMock(return_value=[]))),
        patch('api.exams.ProtocolOverrides', return_value=MagicMock(
            list_for_exam=AsyncMock(return_value=[]))),
    ]
    return patches


def test_nursing_read_lists_exams():
    p, exams = _patch_exams_cls(list_rows=[{'id': 'e-1'}])
    with p, _conn_ctx():
        client = TestClient(_make_app(
            [Route('/exams', endpoint=ExamsHandler)], NURSE(),
        ))
        resp = client.get('/exams')
    assert resp.status_code == 200
    assert resp.json()['data'] == [{'id': 'e-1'}]
    exams.list_for_technologist.assert_awaited_once()


def test_nursing_read_opens_exam_detail():
    p, _ = _patch_exams_cls(exam_row={'id': 'e-1', 'patient_id': 'P1'})
    children = _patch_detail_children()
    with p, children[0], children[1], children[2], children[3], _conn_ctx():
        client = TestClient(_make_app(
            [Route('/exams/{id}', endpoint=ExamHandler)], NURSE(),
        ))
        resp = client.get('/exams/e-1')
    assert resp.status_code == 200
    assert resp.json()['data']['patient_id'] == 'P1'


def test_exam_write_still_blocked_for_nursing_read_only():
    """POST /exams stays EXAM_WRITE — the relaxation is read-only."""
    p, _ = _patch_exams_cls()
    with p, _conn_ctx():
        client = TestClient(_make_app(
            [Route('/exams', endpoint=ExamsHandler)], NURSE(),
        ))
        resp = client.post('/exams', json={})
    assert resp.status_code == 403
