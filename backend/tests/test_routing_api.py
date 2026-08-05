from unittest.mock import AsyncMock, patch

import pytest
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.routing import Route
from starlette.testclient import TestClient
from starlette.exceptions import HTTPException

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
    from api.routing import RoutingHandler, RoutingRuleHandler
    return Starlette(
        routes=[
            Route('/routing/rules', endpoint=RoutingHandler),
            Route('/routing/rules/{id}', endpoint=RoutingRuleHandler),
        ],
        middleware=[Middleware(_FakeAuth, user=user)],
        exception_handlers={
            HTTPException: _http_exception,
            _ValidationException: validation_exception_handler,
        },
    )


SAMPLE_RULE = {
    'id': 'a1b2c3d4-0000-4000-8000-000000000001',
    'name': 'CT to PACS',
    'description': 'Route CT studies',
    'conditions': '{"modality": {"eq": "CT"}}',
    'destination': 'pacs-1',
    'priority': 10,
    'enabled': True,
}


@pytest.fixture
def fake_conn():
    conn = AsyncMock()
    conn.__aenter__ = AsyncMock(return_value=conn)
    conn.__aexit__ = AsyncMock(return_value=None)
    return conn


class TestRoutingApi:
    @pytest.mark.asyncio
    async def test_list_rules(self, fake_conn):
        user = User({'id': 1, 'permissions': ['ROUTING_READ']})
        client = TestClient(_make_app(user=user))
        fake_rr = AsyncMock()
        fake_rr.list_paginated = AsyncMock(return_value=[SAMPLE_RULE])
        fake_rr.count = AsyncMock(return_value=1)
        with (
            patch('api.routing.get_conn', return_value=fake_conn),
            patch('api.routing.RoutingRule', return_value=fake_rr),
            patch('api.routing.AuditLog', return_value=AsyncMock()),
        ):
            resp = client.get('/routing/rules')
        assert resp.status_code == 200
        data = resp.json()
        assert data['data'][0]['name'] == 'CT to PACS'

    @pytest.mark.asyncio
    async def test_list_rules_forbidden(self):
        user = User({'id': 1, 'permissions': []})
        client = TestClient(_make_app(user=user))
        resp = client.get('/routing/rules')
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_create_rule(self, fake_conn):
        user = User({'id': 1, 'permissions': ['ROUTING_WRITE']})
        client = TestClient(_make_app(user=user))
        fake_rr = AsyncMock()
        fake_rr.create = AsyncMock(return_value={'id': SAMPLE_RULE['id']})
        fake_audit = AsyncMock()
        with (
            patch('api.routing.get_conn', return_value=fake_conn),
            patch('api.routing.RoutingRule', return_value=fake_rr),
            patch('api.routing.AuditLog', return_value=fake_audit),
        ):
            resp = client.post('/routing/rules', json={
                'name': 'CT to PACS',
                'destination': 'pacs-1',
                'conditions': {'modality': {'eq': 'CT'}},
                'priority': 10,
            })
        assert resp.status_code == 201
        data = resp.json()
        assert data['data']['id'] == SAMPLE_RULE['id']

    @pytest.mark.asyncio
    async def test_create_rule_validates_name(self):
        user = User({'id': 1, 'permissions': ['ROUTING_WRITE']})
        client = TestClient(_make_app(user=user))
        resp = client.post('/routing/rules', json={
            'name': '',
            'destination': 'pacs-1',
        })
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_get_rule_by_id(self, fake_conn):
        user = User({'id': 1, 'permissions': ['ROUTING_READ']})
        client = TestClient(_make_app(user=user))
        fake_rr = AsyncMock()
        fake_rr.get_by_id = AsyncMock(return_value=SAMPLE_RULE)
        fake_audit = AsyncMock()
        with (
            patch('api.routing.get_conn', return_value=fake_conn),
            patch('api.routing.RoutingRule', return_value=fake_rr),
            patch('api.routing.AuditLog', return_value=fake_audit),
        ):
            resp = client.get(f'/routing/rules/{SAMPLE_RULE["id"]}')
        assert resp.status_code == 200
        assert resp.json()['data']['name'] == 'CT to PACS'

    @pytest.mark.asyncio
    async def test_get_rule_not_found(self, fake_conn):
        user = User({'id': 1, 'permissions': ['ROUTING_READ']})
        client = TestClient(_make_app(user=user))
        fake_rr = AsyncMock()
        fake_rr.get_by_id = AsyncMock(return_value=None)
        fake_audit = AsyncMock()
        with (
            patch('api.routing.get_conn', return_value=fake_conn),
            patch('api.routing.RoutingRule', return_value=fake_rr),
            patch('api.routing.AuditLog', return_value=fake_audit),
        ):
            resp = client.get(f'/routing/rules/{SAMPLE_RULE["id"]}')
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_update_rule(self, fake_conn):
        user = User({'id': 1, 'permissions': ['ROUTING_WRITE']})
        client = TestClient(_make_app(user=user))
        fake_rr = AsyncMock()
        fake_rr.get_by_id = AsyncMock(return_value=SAMPLE_RULE)
        fake_rr.update = AsyncMock(return_value=True)
        fake_audit = AsyncMock()
        with (
            patch('api.routing.get_conn', return_value=fake_conn),
            patch('api.routing.RoutingRule', return_value=fake_rr),
            patch('api.routing.AuditLog', return_value=fake_audit),
        ):
            resp = client.put(f'/routing/rules/{SAMPLE_RULE["id"]}', json={
                'name': 'CT to PACS v2',
                'destination': 'pacs-2',
            })
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_update_rule_not_found(self, fake_conn):
        user = User({'id': 1, 'permissions': ['ROUTING_WRITE']})
        client = TestClient(_make_app(user=user))
        fake_rr = AsyncMock()
        fake_rr.get_by_id = AsyncMock(return_value=None)
        fake_audit = AsyncMock()
        with (
            patch('api.routing.get_conn', return_value=fake_conn),
            patch('api.routing.RoutingRule', return_value=fake_rr),
            patch('api.routing.AuditLog', return_value=fake_audit),
        ):
            resp = client.put(f'/routing/rules/{SAMPLE_RULE["id"]}', json={
                'name': 'CT to PACS v2',
                'destination': 'pacs-2',
            })
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_rule(self, fake_conn):
        user = User({'id': 1, 'permissions': ['ROUTING_WRITE']})
        client = TestClient(_make_app(user=user))
        fake_rr = AsyncMock()
        fake_rr.get_by_id = AsyncMock(return_value=SAMPLE_RULE)
        fake_rr.delete = AsyncMock()
        fake_audit = AsyncMock()
        with (
            patch('api.routing.get_conn', return_value=fake_conn),
            patch('api.routing.RoutingRule', return_value=fake_rr),
            patch('api.routing.AuditLog', return_value=fake_audit),
        ):
            resp = client.delete(f'/routing/rules/{SAMPLE_RULE["id"]}')
        assert resp.status_code == 204

    @pytest.mark.asyncio
    async def test_delete_rule_not_found(self, fake_conn):
        user = User({'id': 1, 'permissions': ['ROUTING_WRITE']})
        client = TestClient(_make_app(user=user))
        fake_rr = AsyncMock()
        fake_rr.get_by_id = AsyncMock(return_value=None)
        fake_audit = AsyncMock()
        with (
            patch('api.routing.get_conn', return_value=fake_conn),
            patch('api.routing.RoutingRule', return_value=fake_rr),
            patch('api.routing.AuditLog', return_value=fake_audit),
        ):
            resp = client.delete(f'/routing/rules/{SAMPLE_RULE["id"]}')
        assert resp.status_code == 404
