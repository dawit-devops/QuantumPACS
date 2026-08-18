from unittest.mock import AsyncMock, patch

from starlette.applications import Starlette
from starlette.exceptions import HTTPException
from starlette.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.routing import Route
from starlette.testclient import TestClient

from api.auth import User
from api.validate import validation_exception_handler, _ValidationException


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
    from api.ris_orders import (
        RisOrdersHandler, RisOrderHandler, RisOrderStatusHandler,
    )
    return Starlette(
        routes=[
            Route('/ris/orders', endpoint=RisOrdersHandler),
            Route('/ris/orders/{id}', endpoint=RisOrderHandler),
            Route('/ris/orders/{id}/status', endpoint=RisOrderStatusHandler),
        ],
        middleware=[Middleware(_FakeAuth, user=user)],
        exception_handlers={
            HTTPException: _http_exception,
            _ValidationException: validation_exception_handler,
        },
    )


def _order_row(order_id='ord-1', status='ORDERED', accession='ACC-001'):
    return {
        'id': order_id, 'tenant_id': 'default', 'accession_number': accession,
        'patient_id': 'MRN-001', 'patient_name': 'Jane Doe',
        'patient_dob': None, 'referring_physician': 'Dr. Smith',
        'clinical_indication': 'Chest pain', 'priority': 'ROUTINE',
        'status': status, 'prior_auth_status': 'NOT_REQUIRED',
        'created_by': '1', 'created_at': None, 'updated_at': None,
    }


def _procedure_row(order_id='ord-1'):
    return {
        'id': 'proc-1', 'order_id': order_id, 'tenant_id': 'default',
        'procedure_code': 'CTCHEST', 'procedure_name': 'CT Chest',
        'modality': 'CT', 'body_part': 'Chest', 'laterality': None,
        'contrast': False, 'cpt_code': None, 'icd10_code': None,
        'status': 'ORDERED', 'created_at': None,
    }


def _order_payload(**overrides):
    payload = {
        'accession_number': 'ACC-001',
        'patient_id': 'MRN-001',
        'patient_name': 'Jane Doe',
        'patient_dob': '1980-01-01',
        'referring_physician': 'Dr. Smith',
        'clinical_indication': 'Chest pain',
        'priority': 'ROUTINE',
        'procedures': [
            {'procedure_code': 'CTCHEST', 'procedure_name': 'CT Chest',
             'modality': 'CT', 'body_part': 'Chest', 'contrast': False},
        ],
    }
    payload.update(overrides)
    return payload


def _UniqueViolation():
    from asyncpg.exceptions import UniqueViolationError
    err = UniqueViolationError(
        'duplicate key value violates unique constraint "uq_ris_order_accession"')
    for _ in range(3):
        yield err


class TestOrderCreate:
    def test_create_requires_order_write(self):
        user = User({'id': 1, 'permissions': []})
        client = TestClient(_make_app(user))
        resp = client.post('/ris/orders', json=_order_payload())
        assert resp.status_code == 403

    def test_duplicate_accession_returns_409(self):
        user = User({'id': 1, 'permissions': ['ORDER_WRITE']})
        client = TestClient(_make_app(user))
        mock_conn = AsyncMock()
        mock_conn.__aenter__.return_value = mock_conn
        mock_conn.fetchrow.side_effect = _UniqueViolation()
        with patch('api.ris_orders.get_conn', return_value=mock_conn):
            resp = client.post('/ris/orders', json=_order_payload())
        assert resp.status_code == 409
        assert resp.json()['error']['code'] == 'CONFLICT'

    def test_create_order_returns_201_with_procedures(self):
        user = User({'id': 1, 'permissions': ['ORDER_WRITE']})
        client = TestClient(_make_app(user))
        mock_conn = AsyncMock()
        mock_conn.__aenter__.return_value = mock_conn
        mock_conn.fetchrow.side_effect = [
            _order_row(),      # inserted order (returning id)
            _order_row(),      # fetched order
            _procedure_row(),  # inserted procedure (returning id)
            _procedure_row(),  # fetched procedure
        ]
        with patch('api.ris_orders.get_conn', return_value=mock_conn):
            resp = client.post('/ris/orders', json=_order_payload())
        assert resp.status_code == 201
        data = resp.json()['data']
        assert data['order']['status'] == 'ORDERED'
        assert data['order']['accession_number'] == 'ACC-001'
        assert data['order']['priority'] == 'ROUTINE'
        assert data['procedures'][0]['procedure_code'] == 'CTCHEST'


class TestOrderList:
    def test_list_requires_order_read(self):
        user = User({'id': 1, 'permissions': []})
        client = TestClient(_make_app(user))
        resp = client.get('/ris/orders')
        assert resp.status_code == 403

    def test_list_passes_filters_and_pagination(self):
        user = User({'id': 1, 'permissions': ['ORDER_READ']})
        client = TestClient(_make_app(user))
        mock_conn = AsyncMock()
        mock_conn.__aenter__.return_value = mock_conn
        mock_conn.fetch.return_value = [
            _order_row('ord-1', 'ORDERED'),
            _order_row('ord-2', 'SCHEDULED'),
        ]
        with patch('api.ris_orders.get_conn', return_value=mock_conn):
            resp = client.get('/ris/orders?status=ORDERED&patient_id=MRN-001&limit=10&offset=20')
        assert resp.status_code == 200
        assert len(resp.json()['data']) == 2
        assert resp.json()['data'][0]['accession_number'] == 'ACC-001'


class TestOrderDetail:
    def test_detail_requires_order_read(self):
        user = User({'id': 1, 'permissions': []})
        client = TestClient(_make_app(user))
        resp = client.get('/ris/orders/ord-1')
        assert resp.status_code == 403

    def test_detail_not_found(self):
        user = User({'id': 1, 'permissions': ['ORDER_READ']})
        client = TestClient(_make_app(user))
        mock_conn = AsyncMock()
        mock_conn.__aenter__.return_value = mock_conn
        mock_conn.fetchrow.return_value = None
        with patch('api.ris_orders.get_conn', return_value=mock_conn):
            resp = client.get('/ris/orders/missing')
        assert resp.status_code == 404

    def test_detail_returns_order_with_procedures(self):
        user = User({'id': 1, 'permissions': ['ORDER_READ']})
        client = TestClient(_make_app(user))
        mock_conn = AsyncMock()
        mock_conn.__aenter__.return_value = mock_conn
        mock_conn.fetchrow.return_value = _order_row()
        mock_conn.fetch.return_value = [_procedure_row()]
        with patch('api.ris_orders.get_conn', return_value=mock_conn):
            resp = client.get('/ris/orders/ord-1')
        assert resp.status_code == 200
        data = resp.json()['data']
        assert data['order']['id'] == 'ord-1'
        assert data['procedures'][0]['procedure_code'] == 'CTCHEST'


class TestOrderStatusTransition:
    def test_transition_requires_order_write(self):
        user = User({'id': 1, 'permissions': []})
        client = TestClient(_make_app(user))
        resp = client.put('/ris/orders/ord-1/status', json={'status': 'SCHEDULED'})
        assert resp.status_code == 403

    def test_valid_transition_returns_updated_order(self):
        user = User({'id': 1, 'permissions': ['ORDER_WRITE']})
        client = TestClient(_make_app(user))
        mock_conn = AsyncMock()
        mock_conn.__aenter__.return_value = mock_conn
        mock_conn.fetchrow.side_effect = [
            _order_row(status='ORDERED'),   # read current
            {'id': 'ord-1'},                # update returning id
            _order_row(status='SCHEDULED'), # updated order
        ]
        mock_conn.fetch.return_value = [_procedure_row()]
        with patch('api.ris_orders.get_conn', return_value=mock_conn):
            resp = client.put('/ris/orders/ord-1/status', json={
                'status': 'SCHEDULED', 'reason': 'booked',
            })
        assert resp.status_code == 200
        assert resp.json()['data']['order']['status'] == 'SCHEDULED'
        assert mock_conn.execute.await_count == 1  # audit

    def test_illegal_transition_returns_422(self):
        user = User({'id': 1, 'permissions': ['ORDER_WRITE']})
        client = TestClient(_make_app(user))
        mock_conn = AsyncMock()
        mock_conn.__aenter__.return_value = mock_conn
        mock_conn.fetchrow.side_effect = [
            _order_row(status='ORDERED'),  # read current
        ]
        with patch('api.ris_orders.get_conn', return_value=mock_conn):
            resp = client.put('/ris/orders/ord-1/status', json={'status': 'SIGNED'})
        assert resp.status_code == 422
        assert resp.json()['error']['code'] == 'INVALID_TRANSITION'
        assert mock_conn.execute.await_count == 0  # nothing audited

    def test_transition_missing_order_returns_404(self):
        user = User({'id': 1, 'permissions': ['ORDER_WRITE']})
        client = TestClient(_make_app(user))
        mock_conn = AsyncMock()
        mock_conn.__aenter__.return_value = mock_conn
        mock_conn.fetchrow.return_value = None
        with patch('api.ris_orders.get_conn', return_value=mock_conn):
            resp = client.put('/ris/orders/missing/status', json={'status': 'SCHEDULED'})
        assert resp.status_code == 404

    def test_invalid_status_value_returns_validation_error(self):
        user = User({'id': 1, 'permissions': ['ORDER_WRITE']})
        client = TestClient(_make_app(user))
        resp = client.put('/ris/orders/ord-1/status', json={'status': 'NOPE'})
        assert resp.status_code == 422