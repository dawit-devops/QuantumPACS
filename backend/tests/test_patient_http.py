from unittest.mock import AsyncMock, MagicMock, patch

from starlette.applications import Starlette
from starlette.exceptions import HTTPException
from starlette.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.routing import Route
from starlette.testclient import TestClient

from api.auth import User
from api.patient import PatientHandler
from api.validate import validation_exception_handler, _ValidationException


class _FakeAuth(BaseHTTPMiddleware):
    def __init__(self, app, user=None):
        super().__init__(app)
        self._user = user or User({'id': 1, 'permissions': ['PATIENT_READ']})

    async def dispatch(self, request, call_next):
        request.scope['user'] = self._user
        request.scope['auth'] = None
        return await call_next(request)


def _mock_conn():
    conn = MagicMock()
    conn.fetch = AsyncMock(return_value=[])
    conn.fetchrow = AsyncMock(return_value=None)
    conn.fetchval = AsyncMock(return_value=0)
    conn.execute = AsyncMock(return_value=None)
    return conn


def _patch_get_conn(module, mock_conn):
    return patch(f'{module}.get_conn', return_value=MagicMock(
        __aenter__=AsyncMock(return_value=mock_conn),
        __aexit__=AsyncMock(return_value=None),
    ))


def _http_exception(request, exc):
    from starlette.responses import JSONResponse
    return JSONResponse({'error': exc.detail}, status_code=exc.status_code)


def _make_app(routes, user=None):
    return Starlette(
        routes=routes,
        middleware=[Middleware(_FakeAuth, user=user)],
        exception_handlers={
            HTTPException: _http_exception,
            _ValidationException: validation_exception_handler,
        },
    )


class TestPatientHandler:
    def _make_app(self, user=None):
        return _make_app([Route('/patients/{id}', endpoint=PatientHandler)], user)

    def test_get_found(self):
        mock_conn = _mock_conn()
        mock_conn.fetchrow = AsyncMock(return_value={
            'id': 1, 'patient_id': '1', 'name': 'Smith^John',
            'birth_date': '19800101', 'sex': 'M', 'study_count': 5,
        })
        with _patch_get_conn('api.patient', mock_conn):
            client = TestClient(self._make_app())
            resp = client.get('/patients/1')
        assert resp.status_code == 200

    def test_get_not_found(self):
        mock_conn = _mock_conn()
        mock_conn.fetchrow = AsyncMock(return_value=None)
        with _patch_get_conn('api.patient', mock_conn):
            client = TestClient(self._make_app())
            resp = client.get('/patients/999')
        assert resp.status_code == 404

    def test_get_non_numeric_id_is_404(self):
        # F5: an MRN routed at the numeric-id endpoint is a client error —
        # the handler must 404, not crash with ValueError → 500.
        client = TestClient(self._make_app())
        resp = client.get('/patients/E2E-CC-1786993844260')
        assert resp.status_code == 404

    def test_missing_permission(self):
        user = User({'id': 1, 'permissions': []})
        client = TestClient(self._make_app(user=user))
        resp = client.get('/patients/1')
        assert resp.status_code == 403
