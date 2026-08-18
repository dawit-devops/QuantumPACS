from contextlib import contextmanager
from unittest.mock import AsyncMock, patch

from starlette.applications import Starlette
from starlette.exceptions import HTTPException
from starlette.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.routing import Route
from starlette.testclient import TestClient

from api.auth import User
from api.validate import validation_exception_handler, _ValidationException

ORDER_READ_USER = User({'id': 7, 'permissions': ['ORDER_READ']})
NO_ORDER_USER = User({'id': 8, 'permissions': ['PATIENT_READ']})


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


def _make_app(user=None):
    from api.orders import OrdersHandler
    return Starlette(
        routes=[Route('/orders', endpoint=OrdersHandler)],
        middleware=[Middleware(_FakeAuth, user=user)],
        exception_handlers={
            HTTPException: _http_exception,
            _ValidationException: validation_exception_handler,
        },
    )


@contextmanager
def _conn(fetch=None):
    with patch('api.orders.get_conn') as conn_cls:
        conn = AsyncMock()
        conn.fetch = fetch or AsyncMock(return_value=[])
        conn_cls.return_value.__aenter__.return_value = conn
        yield conn


class TestOrdersHandler:
    def test_requires_order_read(self):
        """ORDER_READ gate: a non-holder is denied before any query runs."""
        client = TestClient(_make_app(NO_ORDER_USER))
        with _conn():
            resp = client.get('/orders')
        assert resp.status_code in (401, 403)

    def test_lists_orders_with_lifecycle_shape(self):
        """The coordination list returns order + patient + lifecycle fields so
        the frontend can render request → scheduled → performed → reported."""
        client = TestClient(_make_app(ORDER_READ_USER))
        row = {
            'id': 'o1', 'visit_id': 'v1', 'patient_id': 'SMOKE001',
            'patient_name': 'Smoke^Test', 'requested_procedure': 'CT Abdomen',
            'indication': 'RUQ pain', 'urgency': 'routine',
            'order_status': 'open', 'referring_physician': 'Dr Lee',
            'created_at': '2026-08-14 10:00:00+00:00',
            'wl_status': 'scheduled', 'scheduled_date': '2026-08-15',
            'modality': 'CT', 'exam_status': None, 'exam_id': None,
            'report_status': None, 'report_id': None,
        }
        with _conn(fetch=AsyncMock(return_value=[row])):
            resp = client.get('/orders')
        assert resp.status_code == 200
        data = resp.json()['data']
        assert len(data) == 1
        assert data[0]['patient_name'] == 'Smoke^Test'
        assert data[0]['order_status'] == 'open'
        assert data[0]['wl_status'] == 'scheduled'

    def test_empty_list_is_ok(self):
        """No orders yet → empty data array (frontend renders empty state)."""
        client = TestClient(_make_app(ORDER_READ_USER))
        with _conn():
            resp = client.get('/orders')
        assert resp.status_code == 200
        assert resp.json() == {'data': []}
