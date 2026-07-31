import sys
import types
from unittest.mock import MagicMock, patch

from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.routing import Route, WebSocketRoute
from starlette.testclient import TestClient

from api.auth import User

# Must set up sys.modules before api.ws import — but only for the import itself.
# api.ws imports starlette things at top level; redis imports happen inside functions.
# We set up redis mocks in setup_method via _setup_redis_mocks().

from api.ws import WSToken, WebsocketHandler, local_clients


class _FakeAuth(BaseHTTPMiddleware):
    def __init__(self, app, user=None):
        super().__init__(app)
        self._user = user or User({'id': 1, 'permissions': []})

    async def dispatch(self, request, call_next):
        request.scope['user'] = self._user
        request.scope['auth'] = None
        return await call_next(request)


def _make_app(routes, user=None):
    return Starlette(
        routes=routes,
        middleware=[Middleware(_FakeAuth, user=user)],
    )


def _setup_redis_mocks():
    rasyncio = types.ModuleType('redis.asyncio')
    rasyncio.Redis = MagicMock(side_effect=ConnectionError('no redis'))
    sys.modules['redis'] = types.ModuleType('redis')
    sys.modules['redis.asyncio'] = rasyncio


def _reset_ws_globals():
    local_clients.clear()
    import api.ws
    api.ws._listener_task = None
    api.ws._cleanup_task = None
    api.ws._pubsub = None


class TestWSToken:
    def _make_app(self, user=None):
        return _make_app([Route('/ws_token', endpoint=WSToken)], user)

    def test_generates_token(self):
        _reset_ws_globals()
        with patch('api.ws.gen_token') as mock_gen:
            mock_gen.return_value = 'ws-token-abc'
            client = TestClient(self._make_app())
            resp = client.get('/ws_token')
        assert resp.status_code == 200
        assert resp.json()['token'] == 'ws-token-abc'


class TestWebsocketHandler:
    def setup_method(self):
        _setup_redis_mocks()
        _reset_ws_globals()

    def _make_app(self, user=None):
        return _make_app([WebSocketRoute('/ws', endpoint=WebsocketHandler)], user)

    def test_connect_and_disconnect(self):
        client = TestClient(self._make_app())
        with client.websocket_connect('/ws') as ws:
            ws.send_json({'type': 'open', 'file': '1'})
            resp = ws.receive_json()
            assert resp['type'] == 'send_state'
            assert resp['file'] == '1'

    def test_send_state_without_redis(self):
        client = TestClient(self._make_app())
        with client.websocket_connect('/ws') as ws:
            ws.send_json({'type': 'open', 'file': '1'})
            ws.receive_json()
            ws.send_json({'type': 'send_state', 'file': '1', 'state': {'window': 80}})

    def test_disconnect_cleans_up_clients(self):
        client = TestClient(self._make_app())
        with client.websocket_connect('/ws') as ws:
            ws.send_json({'type': 'open', 'file': '1'})
            ws.receive_json()
        assert '1' not in local_clients
