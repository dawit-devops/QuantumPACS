from unittest.mock import AsyncMock, patch

from starlette.applications import Starlette
from starlette.exceptions import HTTPException
from starlette.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.routing import Route
from starlette.testclient import TestClient

from api.auth import User
from api.validate import _ValidationException, validation_exception_handler


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
    from api.portal import (
        PortalFollowUpHandler,
        PortalFollowUpStatusHandler,
        PortalOrdersHandler,
        PortalPatientHandler,
        PortalPatientSearchHandler,
        PortalReportHandler,
        PortalScopeHandler,
    )
    return Starlette(
        routes=[
            Route('/portal/scope', endpoint=PortalScopeHandler),
            Route('/portal/scope/{id}', endpoint=PortalScopeHandler, methods=['DELETE']),
            Route('/portal/patients', endpoint=PortalPatientSearchHandler),
            Route('/portal/patients/{patient_id}', endpoint=PortalPatientHandler),
            Route(
                '/portal/patients/{patient_id}/reports/{report_id}',
                endpoint=PortalReportHandler,
            ),
            Route('/portal/patients/{patient_id}/orders', endpoint=PortalOrdersHandler),
            Route('/portal/follow-ups', endpoint=PortalFollowUpHandler),
            Route(
                '/portal/follow-ups/{id}',
                endpoint=PortalFollowUpStatusHandler,
                methods=['PUT'],
            ),
        ],
        middleware=[Middleware(_FakeAuth, user=user)],
        exception_handlers={
            HTTPException: _http_exception,
            _ValidationException: validation_exception_handler,
        },
    )


STAFF = User({'id': 1, 'permissions': ['PORTAL_READ', 'FOLLOW_UP_WRITE']})
READ_ONLY = User({'id': 2, 'permissions': ['PORTAL_READ']})
NO_PERMS = User({'id': 3, 'permissions': []})


def _scope_row(**over):
    row = {'id': 'scope-1', 'scope_type': 'ward'}
    row.update(over)
    return row


def _demo_row(**over):
    row = {
        'patient_id': 'MRN1', 'name': 'Jane^Doe',
        'birth_date': '19900101', 'sex': 'F',
    }
    row.update(over)
    return row


def _order_row(**over):
    row = {
        'id': 'exam-1', 'accession_number': 'ACC001', 'modality': 'CT',
        'requested_procedure_desc': 'CT Head', 'status': 'completed',
        'priority': 'routine', 'created_at': None, 'completed_at': None,
    }
    row.update(over)
    return row


def _report_row(**over):
    row = {
        'report_id': 'rep-1', 'exam_id': 'exam-1', 'accession_number': 'ACC001',
        'signed_at': None, 'signed_by': 'Dr. Radiologist',
    }
    row.update(over)
    return row


class TestPortalScope:
    def test_list_requires_portal_read(self):
        client = TestClient(_make_app(NO_PERMS))
        resp = client.get('/portal/scope')
        assert resp.status_code == 403

    def test_list_returns_scope_rows(self):
        client = TestClient(_make_app(STAFF))
        mock_conn = AsyncMock()
        mock_conn.fetch.return_value = [_scope_row(name='Jane^Doe')]
        with patch('api.portal.get_conn', return_value=mock_conn):
            resp = client.get('/portal/scope')
        assert resp.status_code == 200
        data = resp.json()['data']
        assert len(data) == 1
        assert data[0]['patient_id'] == 'MRN1'

    def test_create_requires_portal_read(self):
        client = TestClient(_make_app(NO_PERMS))
        resp = client.post('/portal/scope', json={'patient_id': 'MRN1'})
        assert resp.status_code == 403

    def test_create_success(self):
        client = TestClient(_make_app(STAFF))
        mock_conn = AsyncMock()
        mock_conn.fetchval.return_value = 1
        mock_conn.fetchrow.side_effect = [
            None,
            {'id': 'scope-1', 'scope_type': 'ward'},
        ]
        with patch('api.portal.get_conn', return_value=mock_conn):
            resp = client.post('/portal/scope', json={'patient_id': 'MRN1'})
        assert resp.status_code == 201
        data = resp.json()['data']
        assert data['id'] == 'scope-1'

    def test_create_duplicate_returns_existing(self):
        client = TestClient(_make_app(STAFF))
        mock_conn = AsyncMock()
        mock_conn.fetchval.return_value = 1
        mock_conn.fetchrow.return_value = {'id': 'scope-1', 'scope_type': 'ward'}
        with patch('api.portal.get_conn', return_value=mock_conn):
            resp = client.post('/portal/scope', json={'patient_id': 'MRN1'})
        assert resp.status_code == 200
        data = resp.json()['data']
        assert data['existing'] is True
        assert data['id'] == 'scope-1'

    def test_create_unknown_patient_not_found(self):
        client = TestClient(_make_app(STAFF))
        mock_conn = AsyncMock()
        mock_conn.fetchval.return_value = None
        with patch('api.portal.get_conn', return_value=mock_conn):
            resp = client.post('/portal/scope', json={'patient_id': 'NOPE'})
        assert resp.status_code == 404

    def test_delete_own_scope(self):
        client = TestClient(_make_app(STAFF))
        mock_conn = AsyncMock()
        mock_conn.fetchrow.return_value = {'id': 'scope-1', 'patient_id': 'MRN1'}
        with patch('api.portal.get_conn', return_value=mock_conn):
            resp = client.delete('/portal/scope/scope-1')
        assert resp.status_code == 200

    def test_delete_other_users_scope_not_found(self):
        client = TestClient(_make_app(STAFF))
        mock_conn = AsyncMock()
        mock_conn.fetchrow.return_value = None
        with patch('api.portal.get_conn', return_value=mock_conn):
            resp = client.delete('/portal/scope/scope-1')
        assert resp.status_code == 404


class TestPortalPatientSearch:
    def test_requires_portal_read(self):
        client = TestClient(_make_app(NO_PERMS))
        resp = client.get('/portal/patients?q=jo')
        assert resp.status_code == 403

    def test_short_query_returns_empty(self):
        client = TestClient(_make_app(STAFF))
        resp = client.get('/portal/patients?q=j')
        assert resp.status_code == 200
        assert resp.json()['data'] == []

    def test_returns_scoped_rows_only(self):
        client = TestClient(_make_app(STAFF))
        mock_conn = AsyncMock()
        mock_conn.fetch.return_value = [_demo_row()]
        with patch('api.portal.get_conn', return_value=mock_conn):
            resp = client.get('/portal/patients?q=Jane')
        assert resp.status_code == 200
        data = resp.json()['data']
        assert len(data) == 1
        assert data[0]['patient_id'] == 'MRN1'
        mock_conn.fetch.assert_awaited_once()


class TestPortalPatientView:
    def test_requires_portal_read(self):
        client = TestClient(_make_app(NO_PERMS))
        resp = client.get('/portal/patients/MRN1')
        assert resp.status_code == 403

    def test_scoped_view_returns_patient_orders_and_final_reports(self):
        client = TestClient(_make_app(STAFF))
        mock_conn = AsyncMock()
        mock_conn.fetchrow.side_effect = [_scope_row(), _demo_row()]
        mock_conn.fetch.side_effect = [
            [_order_row()],
            [_report_row()],
        ]
        with patch('api.portal.get_conn', return_value=mock_conn):
            resp = client.get('/portal/patients/MRN1')
        assert resp.status_code == 200
        data = resp.json()['data']
        assert data['patient']['name'] == 'Jane^Doe'
        assert data['orders'][0]['id'] == 'exam-1'
        assert data['reports'][0]['report_id'] == 'rep-1'

    def test_out_of_scope_returns_null_data(self):
        client = TestClient(_make_app(STAFF))
        mock_conn = AsyncMock()
        mock_conn.fetchrow.return_value = None
        with patch('api.portal.get_conn', return_value=mock_conn):
            resp = client.get('/portal/patients/MRN1')
        assert resp.status_code == 200
        assert resp.json()['data'] is None


class TestPortalReportView:
    def test_requires_portal_read(self):
        client = TestClient(_make_app(NO_PERMS))
        resp = client.get('/portal/patients/MRN1/reports/rep-1')
        assert resp.status_code == 403

    def test_non_final_report_never_returned(self):
        client = TestClient(_make_app(STAFF))
        mock_conn = AsyncMock()
        mock_conn.fetchrow.side_effect = [
            _scope_row(),
            {'report_id': 'rep-1', 'status': 'draft'},
        ]
        with patch('api.portal.get_conn', return_value=mock_conn):
            resp = client.get('/portal/patients/MRN1/reports/rep-1')
        assert resp.status_code == 404

    def test_final_report_returned(self):
        client = TestClient(_make_app(STAFF))
        final_row = {
            'report_id': 'rep-1', 'exam_id': 'exam-1', 'status': 'final',
            'accession_number': 'ACC001', 'findings': 'No acute findings',
            'impression': 'Normal', 'recommendations': 'None',
            'signed_by': 'Dr. Radiologist', 'signed_at': None,
        }
        mock_conn = AsyncMock()
        mock_conn.fetchrow.side_effect = [_scope_row(), final_row]
        with patch('api.portal.get_conn', return_value=mock_conn):
            resp = client.get('/portal/patients/MRN1/reports/rep-1')
        assert resp.status_code == 200
        data = resp.json()['data']
        assert data['findings'] == 'No acute findings'
        assert 'status' not in data

    def test_out_of_scope_returns_null_data(self):
        client = TestClient(_make_app(STAFF))
        mock_conn = AsyncMock()
        mock_conn.fetchrow.return_value = None
        with patch('api.portal.get_conn', return_value=mock_conn):
            resp = client.get('/portal/patients/MRN1/reports/rep-1')
        assert resp.status_code == 200
        assert resp.json()['data'] is None


class TestPortalOrders:
    def test_requires_portal_read(self):
        client = TestClient(_make_app(NO_PERMS))
        resp = client.get('/portal/patients/MRN1/orders')
        assert resp.status_code == 403

    def test_scoped_orders(self):
        client = TestClient(_make_app(STAFF))
        mock_conn = AsyncMock()
        mock_conn.fetchrow.return_value = _scope_row()
        mock_conn.fetch.return_value = [_order_row()]
        with patch('api.portal.get_conn', return_value=mock_conn):
            resp = client.get('/portal/patients/MRN1/orders')
        assert resp.status_code == 200
        data = resp.json()['data']
        assert len(data) == 1
        assert data[0]['accession_number'] == 'ACC001'

    def test_out_of_scope_orders_empty(self):
        client = TestClient(_make_app(STAFF))
        mock_conn = AsyncMock()
        mock_conn.fetchrow.return_value = None
        with patch('api.portal.get_conn', return_value=mock_conn):
            resp = client.get('/portal/patients/MRN1/orders')
        assert resp.status_code == 200
        assert resp.json()['data'] == []


class TestPortalFollowUps:
    def test_list_requires_portal_read(self):
        client = TestClient(_make_app(NO_PERMS))
        resp = client.get('/portal/follow-ups')
        assert resp.status_code == 403

    def test_list_returns_own_follow_ups(self):
        client = TestClient(_make_app(STAFF))
        mock_conn = AsyncMock()
        mock_conn.fetch.return_value = [{
            'id': 'fu-1', 'report_id': None, 'exam_id': 'exam-1',
            'patient_id': 'MRN1', 'reason': 'Repeat CT', 'status': 'submitted',
            'priority': 'stat', 'assigned_to': '', 'created_at': None,
            'updated_at': None, 'accession_number': 'ACC001',
        }]
        with patch('api.portal.get_conn', return_value=mock_conn):
            resp = client.get('/portal/follow-ups')
        assert resp.status_code == 200
        data = resp.json()['data']
        assert data[0]['accession_number'] == 'ACC001'

    def test_list_filters_by_status(self):
        client = TestClient(_make_app(STAFF))
        mock_conn = AsyncMock()
        mock_conn.fetch.return_value = []
        with patch('api.portal.get_conn', return_value=mock_conn):
            client.get('/portal/follow-ups?status=submitted')
        _, kwargs = mock_conn.fetch.call_args
        assert 'submitted' in kwargs['args']

    def test_create_requires_follow_up_write(self):
        client = TestClient(_make_app(READ_ONLY))
        resp = client.post('/portal/follow-ups', json={
            'patient_id': 'MRN1', 'reason': 'Repeat imaging',
        })
        assert resp.status_code == 403

    def test_create_returns_422_without_reason(self):
        client = TestClient(_make_app(STAFF))
        resp = client.post('/portal/follow-ups', json={'patient_id': 'MRN1'})
        assert resp.status_code == 422

    def test_create_success_notifies_radiologists(self):
        client = TestClient(_make_app(STAFF))
        mock_conn = AsyncMock()
        mock_conn.fetchrow.return_value = {'id': 'fu-1'}
        with patch('api.portal.get_conn', return_value=mock_conn):
            with patch('api.portal.notify_role') as mock_notify:
                resp = client.post('/portal/follow-ups', json={
                    'patient_id': 'MRN1',
                    'reason': 'New lesion on follow-up CT',
                    'priority': 'stat',
                })
        assert resp.status_code == 201
        assert resp.json()['data']['id'] == 'fu-1'
        mock_notify.assert_awaited_once()
        args = mock_notify.call_args.args
        assert args[1] == 'radiologist'
        assert 'stat' in args[4]

    def test_update_requires_portal_read(self):
        client = TestClient(_make_app(NO_PERMS))
        resp = client.put('/portal/follow-ups/fu-1', json={'status': 'cancelled'})
        assert resp.status_code == 403

    def test_update_own_follow_up_success(self):
        client = TestClient(_make_app(STAFF))
        mock_conn = AsyncMock()
        mock_conn.fetchrow.return_value = {'id': 'fu-1'}
        with patch('api.portal.get_conn', return_value=mock_conn):
            resp = client.put('/portal/follow-ups/fu-1', json={'status': 'cancelled'})
        assert resp.status_code == 200

    def test_update_other_users_follow_up_not_found(self):
        client = TestClient(_make_app(STAFF))
        mock_conn = AsyncMock()
        mock_conn.fetchrow.return_value = None
        with patch('api.portal.get_conn', return_value=mock_conn):
            resp = client.put('/portal/follow-ups/fu-1', json={'status': 'completed'})
        assert resp.status_code == 404
