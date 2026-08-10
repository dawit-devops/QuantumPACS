from unittest.mock import AsyncMock, MagicMock, patch

from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.routing import Route
from starlette.testclient import TestClient

from api.auth import User
from api.frontdesk import VisitsHandler


class _FakeAuth(BaseHTTPMiddleware):
    def __init__(self, app, user=None):
        super().__init__(app)
        self._user = user or User({'id': 1, 'permissions': ['REGISTRATION_READ']})

    async def dispatch(self, request, call_next):
        request.scope['user'] = self._user
        request.scope['auth'] = None
        return await call_next(request)


def _make_app(user=None):
    return Starlette(
        routes=[Route('/api/visits', endpoint=VisitsHandler)],
        middleware=[Middleware(_FakeAuth, user=user)],
    )


class TestVisitsPaginationClamp:
    """M-6: offset/limit on /visits must be clamped before reaching the SQL
    (negative/oversized values are interpolated into the query) and
    non-numeric values are a 400, not a 500."""

    def setup_method(self):
        self._conn = AsyncMock()
        self._conn.__aenter__.return_value = self._conn
        self._conn.__aexit__ = AsyncMock(return_value=None)
        self._fd = MagicMock()
        self._fd.list_visits = AsyncMock(return_value=([], 0))

    def _get(self, params):
        with (
            patch('api.frontdesk.get_conn', return_value=self._conn),
            patch('api.frontdesk.FrontDesk', return_value=self._fd),
        ):
            client = TestClient(_make_app())
            return client.get('/api/visits', params=params)

    def test_defaults_passthrough(self):
        resp = self._get({})
        assert resp.status_code == 200
        assert resp.json()['page'] == 1
        assert resp.json()['per_page'] == 20
        args = self._fd.list_visits.call_args.kwargs
        assert args['page'] == 1
        assert args['per_page'] == 20

    def test_oversized_per_page_clamped_to_200(self):
        resp = self._get({'per_page': '100000'})
        assert resp.status_code == 200
        assert resp.json()['per_page'] == 200
        assert self._fd.list_visits.call_args.kwargs['per_page'] == 200

    def test_zero_per_page_clamped_to_1(self):
        resp = self._get({'per_page': '0'})
        assert resp.status_code == 200
        assert resp.json()['per_page'] == 1

    def test_negative_per_page_clamped_to_1(self):
        resp = self._get({'per_page': '-3'})
        assert resp.status_code == 200
        assert resp.json()['per_page'] == 1

    def test_negative_page_clamped_to_1(self):
        resp = self._get({'page': '-5'})
        assert resp.status_code == 200
        assert resp.json()['page'] == 1

    def test_non_numeric_page_returns_400(self):
        resp = self._get({'page': 'abc'})
        assert resp.status_code == 400
        assert resp.json()['error']['code'] == 'VALIDATION_ERROR'
        self._fd.list_visits.assert_not_awaited()

    def test_non_numeric_per_page_returns_400(self):
        resp = self._get({'per_page': 'xyz'})
        assert resp.status_code == 400
        assert resp.json()['error']['code'] == 'VALIDATION_ERROR'
        self._fd.list_visits.assert_not_awaited()
