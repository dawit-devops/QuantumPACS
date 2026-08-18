"""S3-15 — Interface dashboard API tests.

GET /api/ris/interfaces (endpoints + status counts), /{id}/messages
(history), /{id}/metrics (counts, errors, latency), /exceptions (failed
queue). Repos are mocked; the handler wiring and response contracts are
what is under test.
"""

from unittest.mock import AsyncMock, patch

import pytest
from starlette.applications import Starlette
from starlette.exceptions import HTTPException
from starlette.middleware import Middleware
from starlette.routing import Route
from starlette.testclient import TestClient

from api.auth import User
from api.validate import validation_exception_handler, _ValidationException
from tests.test_ris_orders import _FakeAuth, _http_exception


def _conn_ctx():
    conn = AsyncMock()
    conn.__aenter__ = AsyncMock(return_value=conn)
    conn.__aexit__ = AsyncMock(return_value=False)
    return conn


def _endpoint_row(endpoint_id='11111111-1111-1111-1111-111111111111', name='HIS Order Feed'):
    return {
        'id': endpoint_id, 'tenant_id': 'default', 'name': name,
        'interface_type': 'HL7_ORM', 'protocol': 'HL7V2', 'config': {},
        'is_active': True, 'last_message_at': None,
        'message_count': 5, 'error_count': 1, 'created_at': None,
    }


def _message_row(msg_id='m-1', status='PROCESSED'):
    return {
        'id': msg_id, 'endpoint_id': '11111111-1111-1111-1111-111111111111', 'message_type': 'ORM',
        'trigger_event': 'O01', 'control_id': 'MSG004', 'status': status,
        'error_message': None, 'retry_count': 0,
        'created_at': None, 'processed_at': None,
    }


def _make_app(user=None):
    from api.hl7_admin import (
        RisInterfacesHandler, RisInterfaceMessagesHandler,
        RisInterfaceMetricsHandler, RisInterfaceExceptionsHandler,
        RisInterfaceExceptionRetryHandler,
    )
    return Starlette(
        routes=[
            Route('/ris/interfaces', endpoint=RisInterfacesHandler),
            Route('/ris/interfaces/{id}/messages', endpoint=RisInterfaceMessagesHandler),
            Route('/ris/interfaces/{id}/metrics', endpoint=RisInterfaceMetricsHandler),
            Route('/ris/interfaces/exceptions', endpoint=RisInterfaceExceptionsHandler),
            Route('/ris/interfaces/exceptions/{id}/retry', endpoint=RisInterfaceExceptionRetryHandler, methods=['POST']),
        ],
        middleware=[Middleware(_FakeAuth, user=user)],
        exception_handlers={
            HTTPException: _http_exception,
            _ValidationException: validation_exception_handler,
        },
    )


@pytest.fixture
def dashboard_patches():
    """Mock get_conn + the two RIS repo classes used by the handlers."""
    patchers = [
        patch('api.hl7_admin.get_conn'),
        patch('api.hl7_admin.RisInterfaceEndpoints'),
        patch('api.hl7_admin.RisHl7Messages'),
    ]
    started = [p.start() for p in patchers]
    yield {
        'get_conn': started[0],
        'RisInterfaceEndpoints': started[1],
        'RisHl7Messages': started[2],
    }
    for p in patchers:
        p.stop()


class TestInterfacesList:
    def test_list_interfaces_returns_endpoints_with_counts(self, dashboard_patches):
        endpoints = AsyncMock()
        endpoints.list.return_value = [_endpoint_row()]
        dashboard_patches['RisInterfaceEndpoints'].return_value = endpoints
        messages = AsyncMock()
        messages.count_by_endpoints.return_value = {
            '11111111-1111-1111-1111-111111111111': {'RECEIVED': 5, 'PROCESSED': 4, 'FAILED': 1},
        }
        dashboard_patches['RisHl7Messages'].return_value = messages

        client = TestClient(_make_app(User({'id': 1, 'permissions': ['HL7_READ']})))
        resp = client.get('/ris/interfaces')

        assert resp.status_code == 200
        body = resp.json()['data']
        assert body['total'] == 1
        assert body['interfaces'][0]['name'] == 'HIS Order Feed'
        assert body['interfaces'][0]['status_counts'] == {'PROCESSED': 4, 'FAILED': 1}
        endpoints.list.assert_awaited_once()

    def test_list_interfaces_requires_hl7_read(self, dashboard_patches):
        client = TestClient(_make_app(User({'id': 1, 'permissions': []})))
        resp = client.get('/ris/interfaces')
        assert resp.status_code == 403


class TestInterfaceMessages:
    def test_message_history_for_endpoint(self, dashboard_patches):
        endpoints = AsyncMock()
        endpoints.get.return_value = _endpoint_row()
        dashboard_patches['RisInterfaceEndpoints'].return_value = endpoints
        messages = AsyncMock()
        messages.list_by_endpoint.return_value = ([_message_row()], 1)
        dashboard_patches['RisHl7Messages'].return_value = messages

        client = TestClient(_make_app(User({'id': 1, 'permissions': ['HL7_READ']})))
        resp = client.get('/ris/interfaces/11111111-1111-1111-1111-111111111111/messages?limit=10&offset=20')

        assert resp.status_code == 200
        body = resp.json()['data']
        assert body['total'] == 1
        assert body['messages'][0]['control_id'] == 'MSG004'
        assert body['limit'] == 10
        assert body['offset'] == 20
        messages.list_by_endpoint.assert_awaited_once_with('11111111-1111-1111-1111-111111111111', limit=10, offset=20)

    def test_message_history_404_for_unknown_endpoint(self, dashboard_patches):
        endpoints = AsyncMock()
        endpoints.get.return_value = None
        dashboard_patches['RisInterfaceEndpoints'].return_value = endpoints

        client = TestClient(_make_app(User({'id': 1, 'permissions': ['HL7_READ']})))
        resp = client.get('/ris/interfaces/nope/messages')
        assert resp.status_code == 404


class TestInterfaceMetrics:
    def test_metrics_for_endpoint(self, dashboard_patches):
        endpoints = AsyncMock()
        endpoints.get.return_value = _endpoint_row()
        dashboard_patches['RisInterfaceEndpoints'].return_value = endpoints
        messages = AsyncMock()
        messages.metrics_by_endpoint.return_value = {
            'counts': {'RECEIVED': 10, 'PROCESSED': 9, 'FAILED': 1},
            'errors': 1,
            'avg_latency_ms': 12.5,
        }
        dashboard_patches['RisHl7Messages'].return_value = messages

        client = TestClient(_make_app(User({'id': 1, 'permissions': ['HL7_READ']})))
        resp = client.get('/ris/interfaces/11111111-1111-1111-1111-111111111111/metrics?period=1h')

        assert resp.status_code == 200
        body = resp.json()['data']
        assert body['endpoint_id'] == '11111111-1111-1111-1111-111111111111'
        assert body['period'] == '1h'
        assert body['counts']['FAILED'] == 1
        assert body['errors'] == 1
        assert body['avg_latency_ms'] == 12.5
        messages.metrics_by_endpoint.assert_awaited_once_with('11111111-1111-1111-1111-111111111111', '1 hour')

    def test_metrics_defaults_to_24h_period(self, dashboard_patches):
        endpoints = AsyncMock()
        endpoints.get.return_value = _endpoint_row()
        dashboard_patches['RisInterfaceEndpoints'].return_value = endpoints
        messages = AsyncMock()
        messages.metrics_by_endpoint.return_value = {'counts': {}, 'errors': 0, 'avg_latency_ms': None}
        dashboard_patches['RisHl7Messages'].return_value = messages

        client = TestClient(_make_app(User({'id': 1, 'permissions': ['HL7_READ']})))
        resp = client.get('/ris/interfaces/11111111-1111-1111-1111-111111111111/metrics')

        assert resp.status_code == 200
        assert resp.json()['data']['period'] == '24h'
        messages.metrics_by_endpoint.assert_awaited_once_with('11111111-1111-1111-1111-111111111111', '24 hours')


class TestInterfaceExceptions:
    def test_exception_queue(self, dashboard_patches):
        messages = AsyncMock()
        messages.list_failed.return_value = [
            {'id': 'm-9', 'retry_count': 1, 'raw_message': '...',
             'error_message': 'Unparseable message', 'created_at': None},
        ]
        dashboard_patches['RisHl7Messages'].return_value = messages

        client = TestClient(_make_app(User({'id': 1, 'permissions': ['HL7_READ']})))
        resp = client.get('/ris/interfaces/exceptions')

        assert resp.status_code == 200
        body = resp.json()['data']
        assert body['count'] == 1
        assert body['exceptions'][0]['error_message'] == 'Unparseable message'
        messages.list_failed.assert_awaited_once_with(50)


class TestInterfaceExceptionRetry:
    def test_retry_replays_message(self, dashboard_patches):
        engine = AsyncMock()
        engine.retry_message.return_value = True
        with patch('api.hl7_admin.Hl7InterfaceEngine', return_value=engine):
            client = TestClient(_make_app(User({'id': 1, 'permissions': ['HL7_WRITE']})))
            resp = client.post('/ris/interfaces/exceptions/aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa/retry')

        assert resp.status_code == 200
        assert resp.json()['data'] == {'message_id': 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', 'retried': True}
        engine.retry_message.assert_awaited_once_with('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa')

    def test_retry_unknown_message_404(self, dashboard_patches):
        engine = AsyncMock()
        engine.retry_message.return_value = False
        messages = AsyncMock()
        messages.get.return_value = None
        dashboard_patches['RisHl7Messages'].return_value = messages
        with patch('api.hl7_admin.Hl7InterfaceEngine', return_value=engine):
            client = TestClient(_make_app(User({'id': 1, 'permissions': ['HL7_WRITE']})))
            resp = client.post('/ris/interfaces/exceptions/aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa/retry')

        assert resp.status_code == 404
        messages.get.assert_awaited_once()

    def test_retry_over_budget_returns_retried_false(self, dashboard_patches):
        engine = AsyncMock()
        engine.retry_message.return_value = False
        messages = AsyncMock()
        messages.get.return_value = {'id': 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', 'status': 'FAILED', 'retry_count': 3}
        dashboard_patches['RisHl7Messages'].return_value = messages
        with patch('api.hl7_admin.Hl7InterfaceEngine', return_value=engine):
            client = TestClient(_make_app(User({'id': 1, 'permissions': ['HL7_WRITE']})))
            resp = client.post('/ris/interfaces/exceptions/aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa/retry')

        assert resp.status_code == 200
        assert resp.json()['data'] == {'message_id': 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', 'retried': False}

    def test_retry_requires_hl7_write(self, dashboard_patches):
        client = TestClient(_make_app(User({'id': 1, 'permissions': ['HL7_READ']})))
        resp = client.post('/ris/interfaces/exceptions/aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa/retry')
        assert resp.status_code == 403


class TestEndpointTouch:
    """Regression: Table.exec() takes no query params — touch used to pass
    the id positionally and crash every live message flow (S3-16 live smoke
    exposed it; the engine tests mock touch so it stayed invisible)."""

    @pytest.mark.asyncio
    async def test_touch_ok_increments_counters(self):
        from db.ris_hl7 import RisInterfaceEndpoints

        conn = AsyncMock()
        await RisInterfaceEndpoints(conn).touch('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa')

        sql = conn.execute.call_args.args[0]
        assert 'message_count = message_count + 1' in sql
        assert 'error_count' not in sql
        assert 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa' in sql

    @pytest.mark.asyncio
    async def test_touch_failed_increments_error_count(self):
        from db.ris_hl7 import RisInterfaceEndpoints

        conn = AsyncMock()
        await RisInterfaceEndpoints(conn).touch('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', 'failed')

        sql = conn.execute.call_args.args[0]
        assert 'message_count = message_count + 1' in sql
        assert 'error_count = error_count + 1' in sql


if __name__ == '__main__':
    pytest.main([__file__, '-v'])