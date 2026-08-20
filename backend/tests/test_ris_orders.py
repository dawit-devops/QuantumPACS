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
        RisOrderHistoryHandler,
    )
    return Starlette(
        routes=[
            Route('/ris/orders', endpoint=RisOrdersHandler),
            Route('/ris/orders/{id}', endpoint=RisOrderHandler),
            Route('/ris/orders/{id}/status', endpoint=RisOrderStatusHandler),
            Route('/ris/orders/{id}/history', endpoint=RisOrderHistoryHandler),
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
        mock_conn.fetchval.return_value = 2
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


class TestOrderSearch:
    def test_list_returns_pagination_metadata(self):
        user = User({'id': 1, 'permissions': ['ORDER_READ']})
        client = TestClient(_make_app(user))
        mock_conn = AsyncMock()
        mock_conn.__aenter__.return_value = mock_conn
        mock_conn.fetch.return_value = [
            _order_row('ord-1', 'ORDERED'),
            _order_row('ord-2', 'SCHEDULED'),
        ]
        mock_conn.fetchval.return_value = 42
        with patch('api.ris_orders.get_conn', return_value=mock_conn):
            resp = client.get('/ris/orders?page=2&per_page=10')
        assert resp.status_code == 200
        payload = resp.json()['data']
        assert len(payload) == 2
        assert resp.json()['total'] == 42
        assert resp.json()['page'] == 2
        assert resp.json()['per_page'] == 10

    def test_list_passes_search_filters_to_repo(self):
        user = User({'id': 1, 'permissions': ['ORDER_READ']})
        client = TestClient(_make_app(user))
        mock_conn = AsyncMock()
        mock_conn.__aenter__.return_value = mock_conn
        mock_conn.fetch.return_value = []
        mock_conn.fetchval.return_value = 0
        with patch('api.ris_orders.get_conn', return_value=mock_conn):
            resp = client.get(
                '/ris/orders?search=jane&referring_md=Dr.+Smith'
                '&date_from=2026-08-01&date_to=2026-08-31')
        assert resp.status_code == 200
        call = mock_conn.fetch.call_args
        sql = str(call.args[0])
        assert '"patient_name" ILIKE' in sql or '"accession_number" ILIKE' in sql \
            or '"patient_id" ILIKE' in sql
        assert '"referring_physician"' in sql
        assert '"created_at">=' in sql and '"created_at"<=' in sql
        assert 'LIMIT' in sql

    def test_list_requires_order_read(self):
        user = User({'id': 1, 'permissions': []})
        resp = TestClient(_make_app(user)).get('/ris/orders')
        assert resp.status_code == 403


class TestOrderHistory:
    def test_history_requires_order_read(self):
        user = User({'id': 1, 'permissions': []})
        resp = TestClient(_make_app(user)).get('/ris/orders/ord-1/history')
        assert resp.status_code == 403

    def test_history_returns_order_timeline(self):
        user = User({'id': 1, 'permissions': ['ORDER_READ']})
        client = TestClient(_make_app(user))
        mock_conn = AsyncMock()
        mock_conn.__aenter__.return_value = mock_conn
        mock_conn.fetch.return_value = [
            {'id': 2, 'created': '2026-08-20 09:00:00+00',
             'event_type': 'ORDER_STATUS_TRANSITION', 'actor_name': 'system',
             'log': '{"event":"ORDER_STATUS_TRANSITION","actor":"sched-1"}',
             'tenant': 'default'},
            {'id': 1, 'created': '2026-08-20 08:00:00+00',
             'event_type': 'ORDER_CREATED', 'actor_name': 'tech-1',
             'log': '{"event":"ORDER_CREATED","actor":"tech-1"}',
             'tenant': 'default'},
        ]
        with patch('api.ris_orders.get_conn', return_value=mock_conn):
            resp = client.get('/ris/orders/ord-1/history')
        assert resp.status_code == 200
        events = resp.json()['data']
        assert len(events) == 2
        assert events[0]['event'] == 'ORDER_CREATED'
        assert events[0]['actor'] == 'tech-1'
        # Oldest first (timeline order): transition is the newest.
        assert events[-1]['event'] == 'ORDER_STATUS_TRANSITION'


    def test_history_exposes_structured_details(self):
        # B-3: the timeline must surface structured detail (from/to/reason,
        # overrode lists) — a stringified description loses the shape the
        # order-history UI renders.
        user = User({'id': 1, 'permissions': ['ORDER_READ']})
        client = TestClient(_make_app(user))
        mock_conn = AsyncMock()
        mock_conn.__aenter__.return_value = mock_conn
        mock_conn.fetch.return_value = [
            {'id': 3, 'created': '2026-08-20 10:00:00+00',
             'event_type': 'APPOINTMENT_RESCHEDULED', 'actor_name': 'sched-1',
             'log': '{"event":"APPOINTMENT_RESCHEDULED","actor":"sched-1",'
                    '"detail":{"from":"2026-08-20 09:00:00+00",'
                    '"to":"2026-08-20 10:00:00+00","reason":"patient request"}}',
             'tenant': 'default'},
            {'id': 2, 'created': '2026-08-20 09:00:00+00',
             'event_type': 'APPOINTMENT_BOOKED', 'actor_name': 'sched-1',
             'log': '{"event":"APPOINTMENT_BOOKED","actor":"sched-1",'
                    '"detail":{"resource_id":"res-1",'
                    '"start_time":"2026-08-20 09:00:00+00",'
                    '"end_time":"2026-08-20 09:30:00+00","reason":""}}',
             'tenant': 'default'},
            {'id': 1, 'created': '2026-08-20 08:00:00+00',
             'event_type': 'ORDER_CREATED', 'actor_name': 'tech-1',
             'log': '{"event":"ORDER_CREATED","actor":"tech-1","detail":{}}',
             'tenant': 'default'},
        ]
        with patch('api.ris_orders.get_conn', return_value=mock_conn):
            resp = client.get('/ris/orders/ord-1/history')
        assert resp.status_code == 200
        events = resp.json()['data']
        assert events[0]['event'] == 'ORDER_CREATED'
        assert events[1]['details'] == {
            'resource_id': 'res-1',
            'start_time': '2026-08-20 09:00:00+00',
            'end_time': '2026-08-20 09:30:00+00',
            'reason': '',
        }
        assert events[2]['details']['from'] == '2026-08-20 09:00:00+00'
        assert events[2]['details']['reason'] == 'patient request'



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


class TestReferringMdIdentityScope:
    """S-4: the referring-MD view (S4-05) is identity-scoped — a physician
    caller sees only orders attributed to their own identity. The free-text
    probe is ignored for physicians, so a logged-in MD cannot enumerate
    another physician's orders by name."""

    def _orders_client(self, user):
        mock_conn = AsyncMock()
        mock_conn.__aenter__.return_value = mock_conn
        mock_conn.fetch.return_value = []
        mock_conn.fetchval.return_value = 0
        with patch('api.ris_orders.get_conn', return_value=mock_conn), \
             patch('api.ris_orders.RisOrders') as repo_cls:
            repo = repo_cls.return_value
            repo.list = AsyncMock(return_value=[])
            repo.count = AsyncMock(return_value=0)
            client = TestClient(_make_app(user))
            resp = client.get(
                '/ris/orders?referring_md=Dr.+Other&search=jane')
            return resp, repo.list

    def test_physician_scope_ignores_probe_and_uses_own_identity(self):
        resp, list_call = self._orders_client(User({
            'id': 3, 'permissions': ['ORDER_READ'], 'role': 'physician',
            'username': 'dr.smith',
        }))
        assert resp.status_code == 200
        kw = list_call.await_args.kwargs
        assert kw.get('referring_md') == 'dr.smith', kw

    def test_staff_keeps_free_text_probe(self):
        resp, list_call = self._orders_client(User({
            'id': 4, 'permissions': ['ORDER_READ'], 'role': 'receptionist',
            'username': 'clerk1',
        }))
        assert resp.status_code == 200
        kw = list_call.await_args.kwargs
        assert kw.get('referring_md') == 'Dr. Other', kw
