from unittest.mock import AsyncMock, MagicMock, mock_open, patch

from starlette.applications import Starlette
from starlette.exceptions import HTTPException
from starlette.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.routing import Route, Mount
from starlette.testclient import TestClient

from api.auth import User
from api.fhir_admin import (
    FhirAdminConfigHandler, FhirAdminClientsHandler, FhirAdminClientHandler,
    FhirAdminMetricsHandler, FhirAdminRecentRequestsHandler, FhirAdminTestHandler,
)
from api.hl7_admin import (
    Hl7MessagesHandler, Hl7MessageHandler,
    Hl7MetricsHandler, Hl7ConfigHandler, Hl7StatusHandler,
)
from api.dicomweb_admin import DicomWebAdminHandler, DicomWebMetricsHandler
from api.webhooks import WebhooksHandler, WebhookHandler, WebhookTestHandler
from api.validate import validation_exception_handler, _ValidationException


# ---------------------------------------------------------------------------
# Fake auth middleware
# ---------------------------------------------------------------------------

class _FakeAuth(BaseHTTPMiddleware):
    def __init__(self, app, user=None):
        super().__init__(app)
        self._user = user or User({'id': 1, 'permissions': ['SYSTEM_ADMIN', 'HL7_READ', 'HL7_WRITE', 'DICOMWEB_READ', 'ADMIN_READ']})

    async def dispatch(self, request, call_next):
        request.scope['user'] = self._user
        request.scope['auth'] = None
        return await call_next(request)


def _make_admin_user(permissions=None):
    perms = permissions or ['SYSTEM_ADMIN', 'HL7_READ', 'HL7_WRITE', 'DICOMWEB_READ']
    return User({'id': 1, 'permissions': perms})


def _http_exception(request, exc):
    from starlette.responses import JSONResponse
    return JSONResponse({'error': exc.detail}, status_code=exc.status_code)


# ---------------------------------------------------------------------------
# Mock DB helpers – same pattern as test_fhir.py
# ---------------------------------------------------------------------------

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


def _make_app(routes, user=None):
    return Starlette(
        routes=routes,
        middleware=[Middleware(_FakeAuth, user=user or _make_admin_user())],
        exception_handlers={
            HTTPException: _http_exception,
            _ValidationException: validation_exception_handler,
        },
    )


# ===========================================================================
# FHIR Admin Tests
# ===========================================================================

class TestFhirAdminConfig:
    def _make_app(self, user=None):
        return _make_app([Route('/fhir/admin/config', endpoint=FhirAdminConfigHandler)], user)

    def test_get_config(self):
        mock_conn = _mock_conn()
        mock_conn.fetch = AsyncMock(return_value=[
            {'key': 'enabled', 'value': 'true'},
            {'key': 'base_url', 'value': 'http://test/fhir'},
            {'key': 'publisher', 'value': 'Test'},
            {'key': 'max_search_results', 'value': '50'},
            {'key': 'log_retention_days', 'value': '30'},
        ])
        with _patch_get_conn('api.fhir_admin', mock_conn):
            client = TestClient(self._make_app())
            resp = client.get('/fhir/admin/config')
        assert resp.status_code == 200
        body = resp.json()
        assert body['enabled'] is True
        assert body['base_url'] == 'http://test/fhir'

    def test_put_config(self):
        mock_conn = _mock_conn()
        mock_conn.fetch = AsyncMock(return_value=[
            {'key': 'enabled', 'value': 'false'},
            {'key': 'base_url', 'value': 'http://updated/fhir'},
            {'key': 'publisher', 'value': 'Updated'},
            {'key': 'max_search_results', 'value': '100'},
            {'key': 'log_retention_days', 'value': '60'},
        ])
        with _patch_get_conn('api.fhir_admin', mock_conn):
            client = TestClient(self._make_app())
            resp = client.put('/fhir/admin/config', json={'enabled': False, 'publisher': 'Updated'})
        assert resp.status_code == 200
        assert resp.json()['enabled'] is False
        assert resp.json()['publisher'] == 'Updated'

    def test_put_config_no_changes_returns_400(self):
        mock_conn = _mock_conn()
        with _patch_get_conn('api.fhir_admin', mock_conn):
            client = TestClient(self._make_app())
            resp = client.put('/fhir/admin/config', json={})
        assert resp.status_code == 400

    def test_put_config_missing_permission(self):
        user = _make_admin_user(permissions=['LOG_READ'])
        client = TestClient(self._make_app(user=user))
        resp = client.get('/fhir/admin/config')
        assert resp.status_code == 403


class TestFhirAdminClients:
    def _make_app(self, user=None):
        return _make_app([
            Route('/fhir/admin/clients', endpoint=FhirAdminClientsHandler),
            Route('/fhir/admin/clients/{id}', endpoint=FhirAdminClientHandler),
        ], user)

    def test_list_clients(self):
        mock_conn = _mock_conn()
        mock_conn.fetch = AsyncMock(return_value=[
            {'id': 'c1', 'name': 'Test Client', 'client_id': 'qp_test', 'active': True,
             'grant_type': 'client_credentials', 'description': '', 'last_used': None,
             'created_at': '2026-07-29T00:00:00Z'},
        ])
        with _patch_get_conn('api.fhir_admin', mock_conn):
            client = TestClient(self._make_app())
            resp = client.get('/fhir/admin/clients')
        assert resp.status_code == 200
        assert len(resp.json()['clients']) == 1
        assert resp.json()['clients'][0]['name'] == 'Test Client'

    def test_create_client(self):
        mock_conn = _mock_conn()
        with _patch_get_conn('api.fhir_admin', mock_conn):
            client = TestClient(self._make_app())
            resp = client.post('/fhir/admin/clients', json={'name': 'New Client'})
        assert resp.status_code == 201
        assert resp.json()['id']
        assert resp.json()['client_secret'].startswith('qps_')

    def test_create_client_missing_name(self):
        mock_conn = _mock_conn()
        with _patch_get_conn('api.fhir_admin', mock_conn):
            client = TestClient(self._make_app())
            resp = client.post('/fhir/admin/clients', json={})
        assert resp.status_code == 422

    def test_get_single_client_found(self):
        mock_conn = _mock_conn()
        mock_conn.fetchrow = AsyncMock(return_value={
            'id': 'c1', 'name': 'Test Client', 'client_id': 'qp_test',
            'description': '', 'redirect_uris': '', 'grant_type': 'client_credentials',
            'active': True, 'last_used': None, 'created_at': '2026-07-29T00:00:00Z',
        })
        with _patch_get_conn('api.fhir_admin', mock_conn):
            client = TestClient(self._make_app())
            resp = client.get('/fhir/admin/clients/c1')
        assert resp.status_code == 200
        assert resp.json()['name'] == 'Test Client'

    def test_get_single_client_not_found(self):
        mock_conn = _mock_conn()
        mock_conn.fetchrow = AsyncMock(return_value=None)
        with _patch_get_conn('api.fhir_admin', mock_conn):
            client = TestClient(self._make_app())
            resp = client.get('/fhir/admin/clients/nonexistent')
        assert resp.status_code == 404

    def test_update_client(self):
        mock_conn = _mock_conn()
        mock_conn.fetchrow = AsyncMock(side_effect=[
            {'id': 'c1', 'name': 'Old'},
            {'id': 'c1', 'name': 'Updated'},
        ])
        with _patch_get_conn('api.fhir_admin', mock_conn):
            client = TestClient(self._make_app())
            resp = client.put('/fhir/admin/clients/c1', json={'name': 'Updated'})
        assert resp.status_code == 200
        assert resp.json()['name'] == 'Updated'

    def test_update_client_no_changes(self):
        mock_conn = _mock_conn()
        with _patch_get_conn('api.fhir_admin', mock_conn):
            client = TestClient(self._make_app())
            resp = client.put('/fhir/admin/clients/c1', json={})
        assert resp.status_code == 400

    def test_update_client_not_found(self):
        mock_conn = _mock_conn()
        mock_conn.fetchrow = AsyncMock(return_value=None)
        with _patch_get_conn('api.fhir_admin', mock_conn):
            client = TestClient(self._make_app())
            resp = client.put('/fhir/admin/clients/nonexistent', json={'name': 'X'})
        assert resp.status_code == 404

    def test_delete_client(self):
        mock_conn = _mock_conn()
        mock_conn.fetchrow = AsyncMock(return_value={'id': 'c1'})
        with _patch_get_conn('api.fhir_admin', mock_conn):
            client = TestClient(self._make_app())
            resp = client.delete('/fhir/admin/clients/c1')
        assert resp.status_code == 200
        assert resp.json()['ok'] is True

    def test_delete_client_not_found(self):
        mock_conn = _mock_conn()
        mock_conn.fetchrow = AsyncMock(return_value=None)
        with _patch_get_conn('api.fhir_admin', mock_conn):
            client = TestClient(self._make_app())
            resp = client.delete('/fhir/admin/clients/nonexistent')
        assert resp.status_code == 404


class TestFhirAdminMetrics:
    def _make_app(self, user=None):
        return _make_app([Route('/fhir/admin/metrics', endpoint=FhirAdminMetricsHandler)], user)

    def test_get_metrics(self):
        mock_conn = _mock_conn()
        mock_conn.fetch = AsyncMock(return_value=[
            {'resource_type': 'Patient', 'method': 'GET', 'count': 10},
        ])
        mock_conn.fetchrow = AsyncMock(return_value={'p50': 50, 'p95': 200, 'p99': 500})
        mock_conn.fetchval = AsyncMock(return_value=100)
        with _patch_get_conn('api.fhir_admin', mock_conn):
            client = TestClient(self._make_app())
            resp = client.get('/fhir/admin/metrics?period=24h')
        assert resp.status_code == 200
        body = resp.json()
        assert body['total_requests'] == 100
        assert len(body['volume']) == 1
        assert body['latency']['p50'] == 50


class TestFhirAdminRecentRequests:
    def _make_app(self, user=None):
        return _make_app([Route('/fhir/admin/requests', endpoint=FhirAdminRecentRequestsHandler)], user)

    def test_list_requests(self):
        mock_conn = _mock_conn()
        mock_conn.fetch = AsyncMock(return_value=[
            {'id': 'r1', 'method': 'GET', 'path': '/fhir/Patient', 'status_code': 200,
             'duration_ms': 45, 'resource_type': 'Patient', 'resource_id': 'p1',
             'caller': 'admin@test.com', 'created_at': '2026-07-29T00:00:00Z',
             'ip_address': '127.0.0.1', 'query_params': ''},
        ])
        mock_conn.fetchval = AsyncMock(return_value=1)
        with _patch_get_conn('api.fhir_admin', mock_conn):
            client = TestClient(self._make_app())
            resp = client.get('/fhir/admin/requests?limit=50&offset=0')
        assert resp.status_code == 200
        assert len(resp.json()['requests']) == 1
        assert resp.json()['total'] == 1


class TestFhirAdminTest:
    def _make_app(self, user=None):
        return _make_app([Route('/fhir/admin/test', endpoint=FhirAdminTestHandler)], user)

    def test_connection_test_timeout(self):
        mock_conn = _mock_conn()
        mock_conn.fetch = AsyncMock(return_value=[
            {'key': 'enabled', 'value': 'true'},
            {'key': 'base_url', 'value': 'http://localhost:18080/fhir'},
            {'key': 'publisher', 'value': 'Test'},
        ])
        with _patch_get_conn('api.fhir_admin', mock_conn):
            client = TestClient(self._make_app())
            resp = client.get('/fhir/admin/test')
        assert resp.status_code == 200
        assert resp.json()['reachable'] is False


# ===========================================================================
# HL7 Admin Tests
# ===========================================================================

class TestHl7Messages:
    def _make_app(self, user=None):
        return _make_app([
            Route('/hl7/admin/messages', endpoint=Hl7MessagesHandler),
            Route('/hl7/admin/messages/{id}', endpoint=Hl7MessageHandler),
        ], user)

    def test_list_messages(self):
        mock_conn = _mock_conn()
        mock_conn.fetch = AsyncMock(return_value=[
            {'id': 'm1', 'message_type': 'ADT', 'event_type': 'A01',
             'patient_id': 'P001', 'accession_number': '', 'sending_facility': 'HOSP',
             'parse_status': 'ok', 'error_message': '', 'created_at': '2026-07-29T00:00:00Z'},
        ])
        mock_conn.fetchval = AsyncMock(return_value=1)
        with _patch_get_conn('api.hl7_admin', mock_conn):
            client = TestClient(self._make_app())
            resp = client.get('/hl7/admin/messages?limit=50&offset=0')
        assert resp.status_code == 200
        assert len(resp.json()['messages']) == 1
        assert resp.json()['total'] == 1

    def test_list_messages_filters(self):
        mock_conn = _mock_conn()
        mock_conn.fetch = AsyncMock(return_value=[])
        mock_conn.fetchval = AsyncMock(return_value=0)
        with _patch_get_conn('api.hl7_admin', mock_conn):
            client = TestClient(self._make_app())
            resp = client.get('/hl7/admin/messages?message_type=ADT&parse_status=failed')
        assert resp.status_code == 200
        assert resp.json()['total'] == 0

    def test_get_message_detail(self):
        mock_conn = _mock_conn()
        mock_conn.fetchrow = AsyncMock(return_value={
            'id': 'm1', 'raw_content': 'MSH|...', 'message_type': 'ADT',
            'event_type': 'A01', 'patient_id': 'P001', 'accession_number': '',
            'sending_facility': 'HOSP', 'parsed_fields': '{"patient_name": "Smith"}',
            'parse_status': 'ok', 'error_message': '', 'created_at': '2026-07-29T00:00:00Z',
        })
        mock_conn.fetch = AsyncMock(return_value=[])
        with _patch_get_conn('api.hl7_admin', mock_conn):
            client = TestClient(self._make_app())
            resp = client.get('/hl7/admin/messages/m1')
        assert resp.status_code == 200
        assert resp.json()['message_type'] == 'ADT'
        assert resp.json()['parsed_fields'] == {'patient_name': 'Smith'}

    def test_get_message_not_found(self):
        mock_conn = _mock_conn()
        mock_conn.fetchrow = AsyncMock(return_value=None)
        with _patch_get_conn('api.hl7_admin', mock_conn):
            client = TestClient(self._make_app())
            resp = client.get('/hl7/admin/messages/nonexistent')
        assert resp.status_code == 404


class TestHl7Metrics:
    def _make_app(self, user=None):
        return _make_app([Route('/hl7/admin/metrics', endpoint=Hl7MetricsHandler)], user)

    def test_get_metrics(self):
        mock_conn = _mock_conn()
        mock_conn.fetchval = AsyncMock(return_value=42)
        mock_conn.fetch = AsyncMock(return_value=[
            {'message_type': 'ADT', 'event_type': 'A01', 'count': 30},
            {'message_type': 'ORM', 'event_type': 'O01', 'count': 12},
        ])
        with _patch_get_conn('api.hl7_admin', mock_conn):
            client = TestClient(self._make_app())
            resp = client.get('/hl7/admin/metrics?period=24h')
        assert resp.status_code == 200
        assert resp.json()['total'] == 42
        assert len(resp.json()['by_type']) == 2


class TestHl7Config:
    def _make_app(self, user=None):
        return _make_app([Route('/hl7/admin/config', endpoint=Hl7ConfigHandler)], user)

    def test_get_config(self):
        fake_cfg = {
            'hl7_mllp_port': '12579',
            'hl7_mllp_allowed_ips': '10.0.0.0/24,192.168.1.0/24',
        }
        with patch('api.hl7_admin.config', fake_cfg):
            client = TestClient(self._make_app())
            resp = client.get('/hl7/admin/config')
        assert resp.status_code == 200
        assert resp.json()['mllp_port'] == 12579
        assert len(resp.json()['allowed_ips']) == 2

    def test_put_config(self):
        fake_cfg = {
            'hl7_mllp_port': '12579',
            'hl7_mllp_allowed_ips': '10.0.0.0/24,192.168.1.0/24',
        }
        # open() is mocked so the handler never truncates the real
        # config.local.yaml (which holds the runtime secret) — the PUT
        # read/dump cycle must stay in-memory during tests.
        with patch('api.hl7_admin.config', fake_cfg), \
             patch('yaml.safe_load', return_value={}), \
             patch('builtins.open', mock_open()):
            client = TestClient(self._make_app())
            resp = client.put('/hl7/admin/config', json={'mllp_port': 12580, 'allowed_ips': ['10.0.0.0/24']})
        assert resp.status_code == 200
        assert 'hl7_mllp_port' in resp.json()['updated']


class TestHl7Status:
    def _make_app(self, user=None):
        return _make_app([Route('/hl7/admin/status', endpoint=Hl7StatusHandler)], user)

    def test_status_when_not_listening(self):
        fake_cfg = {'hl7_mllp_port': '12579', 'hl7_mllp_host': ''}
        with patch('api.hl7_admin.config', fake_cfg), \
             patch('socket.create_connection', side_effect=ConnectionRefusedError()):
            client = TestClient(self._make_app())
            resp = client.get('/hl7/admin/status')
        assert resp.status_code == 200
        assert resp.json()['listening'] is False
        assert resp.json()['port'] == 12579


# ===========================================================================
# DICOMweb Admin Tests
# ===========================================================================

class TestDicomWebAdmin:
    def _make_app(self, user=None):
        return _make_app([
            Route('/dicomweb/admin', endpoint=DicomWebAdminHandler),
            Route('/dicomweb/admin/metrics', endpoint=DicomWebMetricsHandler),
        ], user)

    def test_get_status(self):
        client = TestClient(self._make_app())
        resp = client.get('/dicomweb/admin')
        assert resp.status_code == 200
        body = resp.json()
        assert body['qido']['enabled'] is True
        assert body['wado']['enabled'] is True
        assert body['stow']['enabled'] is True
        assert len(body['modalities']) == 50
        assert len(body['missing_features']) > 0

    def test_get_metrics(self):
        mock_conn = _mock_conn()
        mock_conn.fetchval = AsyncMock(return_value=10)
        mock_conn.fetchrow = AsyncMock(
            return_value={'studies': 30, 'series': 45, 'files': 120}
        )
        mock_conn.fetch = AsyncMock(side_effect=[
            [{'modality': 'CT', 'count': 8}, {'modality': 'MR', 'count': 2}],
            [{'kind': 'qido', 'total': 5, 'errors': 1}],
        ])
        with _patch_get_conn('api.dicomweb_admin', mock_conn):
            client = TestClient(self._make_app())
            resp = client.get('/dicomweb/admin/metrics?period=7d')
        assert resp.status_code == 200
        body = resp.json()
        assert body['period'] == '7d'
        assert body['files_stored'] == 10
        assert body['studies_stored'] == 10
        assert body['failed_stores'] == 10
        assert body['storage_bytes'] == 10
        assert body['by_modality'] == [{'modality': 'CT', 'count': 8}, {'modality': 'MR', 'count': 2}]
        assert body['requests_by_kind'] == [{'kind': 'qido', 'total': 5, 'errors': 1}]
        assert body['requests_total'] == 5
        assert body['requests_failed'] == 1
        assert body['totals'] == {'studies': 30, 'series': 45, 'files': 120}

    def test_metrics_defaults_to_24h(self):
        mock_conn = _mock_conn()
        mock_conn.fetchval = AsyncMock(return_value=0)
        mock_conn.fetchrow = AsyncMock(
            return_value={'studies': 0, 'series': 0, 'files': 0}
        )
        mock_conn.fetch = AsyncMock(return_value=[])
        with _patch_get_conn('api.dicomweb_admin', mock_conn):
            client = TestClient(self._make_app())
            resp = client.get('/dicomweb/admin/metrics')
        assert resp.status_code == 200
        assert resp.json()['period'] == '24h'

    def test_missing_permission(self):
        user = _make_admin_user(permissions=['LOG_READ'])
        client = TestClient(self._make_app(user=user))
        resp = client.get('/dicomweb/admin')
        assert resp.status_code == 403


# ===========================================================================
# Webhook Tests
# ===========================================================================

class TestWebhooks:
    def _make_app(self, user=None):
        return _make_app([
            Route('/webhooks', endpoint=WebhooksHandler),
            Route('/webhooks/test', endpoint=WebhookTestHandler, methods=['POST']),
            Route('/webhooks/{id}', endpoint=WebhookHandler),
        ], user)

    def test_list_webhooks(self):
        mock_conn = _mock_conn()
        mock_conn.fetch = AsyncMock(return_value=[
            {'id': 'w1', 'name': 'Slack', 'url': 'https://hooks.example.com',
             'events': ['study.arrived'], 'active': True, 'retry_count': 3, 'timeout_ms': 5000,
             'last_triggered_at': None, 'last_status_code': None, 'last_error': None,
             'created_at': '2026-07-29T00:00:00Z'},
        ])
        with _patch_get_conn('api.webhooks', mock_conn):
            client = TestClient(self._make_app())
            resp = client.get('/webhooks')
        assert resp.status_code == 200
        assert len(resp.json()['webhooks']) == 1
        assert resp.json()['webhooks'][0]['name'] == 'Slack'
        assert len(resp.json()['available_events']) > 0

    def test_create_webhook(self):
        mock_conn = _mock_conn()
        mock_conn.fetchval = AsyncMock(return_value='wh-new-id')
        with _patch_get_conn('api.webhooks', mock_conn):
            mock_conn.fetchrow = AsyncMock(return_value={
                'id': 'wh-new-id', 'name': 'Test WH', 'url': 'https://example.com/hook',
                'events': ['study.arrived'], 'active': True, 'retry_count': 3, 'timeout_ms': 5000,
                'secret': '', 'last_triggered_at': None, 'last_status_code': None,
                'last_error': None, 'created_at': '2026-07-29T00:00:00Z',
            })
            client = TestClient(self._make_app())
            resp = client.post('/webhooks', json={
                'name': 'Test WH', 'url': 'https://example.com/hook',
                'events': ['study.arrived'],
            })
        assert resp.status_code == 201

    def test_create_webhook_validation_error(self):
        with _patch_get_conn('api.webhooks', _mock_conn()):
            client = TestClient(self._make_app())
            resp = client.post('/webhooks', json={'url': 'not-a-url'})
        assert resp.status_code == 422

    def test_get_webhook_found(self):
        mock_conn = _mock_conn()
        mock_conn.fetchrow = AsyncMock(return_value={
            'id': 'w1', 'name': 'Slack', 'url': 'https://hooks.example.com',
            'events': ['study.arrived'], 'active': True, 'retry_count': 3, 'timeout_ms': 5000,
            'secret': '', 'last_triggered_at': None, 'last_status_code': None,
            'last_error': None, 'created_at': '2026-07-29T00:00:00Z',
        })
        with _patch_get_conn('api.webhooks', mock_conn):
            client = TestClient(self._make_app())
            resp = client.get('/webhooks/w1')
        assert resp.status_code == 200
        assert resp.json()['name'] == 'Slack'

    def test_get_webhook_not_found(self):
        mock_conn = _mock_conn()
        mock_conn.fetchrow = AsyncMock(return_value=None)
        with _patch_get_conn('api.webhooks', mock_conn):
            client = TestClient(self._make_app())
            resp = client.get('/webhooks/nonexistent')
        assert resp.status_code == 404

    def test_update_webhook(self):
        mock_conn = _mock_conn()
        mock_conn.fetchrow = AsyncMock(side_effect=[
            {'id': 'w1', 'name': 'Old'},
            {'id': 'w1', 'name': 'Updated'},
        ])
        with _patch_get_conn('api.webhooks', mock_conn):
            client = TestClient(self._make_app())
            resp = client.put('/webhooks/w1', json={'name': 'Updated'})
        assert resp.status_code == 200
        assert resp.json()['name'] == 'Updated'

    def test_update_webhook_no_changes(self):
        mock_conn = _mock_conn()
        with _patch_get_conn('api.webhooks', mock_conn):
            client = TestClient(self._make_app())
            resp = client.put('/webhooks/w1', json={})
        assert resp.status_code == 400

    def test_update_webhook_not_found(self):
        mock_conn = _mock_conn()
        mock_conn.fetchrow = AsyncMock(return_value=None)
        with _patch_get_conn('api.webhooks', mock_conn):
            client = TestClient(self._make_app())
            resp = client.put('/webhooks/nonexistent', json={'name': 'X'})
        assert resp.status_code == 404

    def test_delete_webhook(self):
        mock_conn = _mock_conn()
        mock_conn.fetchrow = AsyncMock(return_value={'id': 'w1'})
        with _patch_get_conn('api.webhooks', mock_conn):
            client = TestClient(self._make_app())
            resp = client.delete('/webhooks/w1')
        assert resp.status_code == 200
        assert resp.json()['deleted'] is True

    def test_delete_webhook_not_found(self):
        mock_conn = _mock_conn()
        mock_conn.fetchrow = AsyncMock(return_value=None)
        with _patch_get_conn('api.webhooks', mock_conn):
            client = TestClient(self._make_app())
            resp = client.delete('/webhooks/nonexistent')
        assert resp.status_code == 404

    def test_webhook_missing_permission(self):
        user = _make_admin_user(permissions=['LOG_READ'])
        client = TestClient(self._make_app(user=user))
        resp = client.get('/webhooks')
        assert resp.status_code == 403

    def test_webhook_test_ping(self):
        client = TestClient(self._make_app())
        resp = client.post('/webhooks/test', json={'url': 'http://localhost:99999/nonexistent'})
        assert resp.status_code == 200
        assert resp.json()['success'] is False

    def test_webhook_test_no_url(self):
        client = TestClient(self._make_app())
        resp = client.post('/webhooks/test', json={})
        assert resp.status_code == 400

    def test_webhook_test_validation_url_required(self):
        client = TestClient(self._make_app())
        resp = client.post('/webhooks/test', json={'url': ''})
        assert resp.status_code == 400


# ===========================================================================
# Route Registration Tests
# ===========================================================================

class TestAdminRouteRegistration:
    def test_all_admin_routes_registered(self):
        with patch.dict('sys.modules', {'PIL': MagicMock()}):
            from api.routes import routes
        paths = set()

        def _walk(routes_list, prefix=''):
            for r in routes_list:
                if isinstance(r, Mount):
                    _walk(list(r.routes), prefix + r.path)
                elif hasattr(r, 'routes') and r.routes:
                    _walk(list(r.routes), prefix)
                elif isinstance(r, (Route,)):
                    methods = r.methods
                    if methods is None:
                        if hasattr(r.endpoint, 'get'): paths.add(f'GET {prefix}{r.path}')
                        if hasattr(r.endpoint, 'put'): paths.add(f'PUT {prefix}{r.path}')
                        if hasattr(r.endpoint, 'post'): paths.add(f'POST {prefix}{r.path}')
                        if hasattr(r.endpoint, 'delete'): paths.add(f'DELETE {prefix}{r.path}')
                        if hasattr(r.endpoint, 'patch'): paths.add(f'PATCH {prefix}{r.path}')
                    else:
                        for m in methods:
                            paths.add(f'{m} {prefix}{r.path}')

        _walk(routes)
        expected = [
            'GET /api/fhir/admin/config',
            'PUT /api/fhir/admin/config',
            'GET /api/fhir/admin/clients',
            'POST /api/fhir/admin/clients',
            'GET /api/fhir/admin/clients/{id}',
            'PUT /api/fhir/admin/clients/{id}',
            'DELETE /api/fhir/admin/clients/{id}',
            'GET /api/fhir/admin/metrics',
            'GET /api/fhir/admin/requests',
            'GET /api/fhir/admin/test',
            'GET /api/hl7/admin/messages',
            'GET /api/hl7/admin/messages/{id}',
            'GET /api/hl7/admin/metrics',
            'GET /api/hl7/admin/config',
            'PUT /api/hl7/admin/config',
            'GET /api/hl7/admin/status',
            'GET /api/dicomweb/admin',
            'GET /api/dicomweb/admin/metrics',
            'GET /api/webhooks',
            'POST /api/webhooks',
            'GET /api/webhooks/{id}',
            'PUT /api/webhooks/{id}',
            'DELETE /api/webhooks/{id}',
            'POST /api/webhooks/test',
        ]
        for ep in expected:
            assert ep in paths, f'{ep} not found in routes'
