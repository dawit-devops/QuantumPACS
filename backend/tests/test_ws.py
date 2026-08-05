import sys
import types
from unittest.mock import MagicMock, patch

from starlette.applications import Starlette
from starlette.authentication import AuthCredentials, AuthenticationBackend
from starlette.middleware import Middleware
from starlette.middleware.authentication import AuthenticationMiddleware
from starlette.routing import Route, WebSocketRoute
from starlette.testclient import TestClient

from api.auth import User

# Must set up sys.modules before api.ws import — but only for the import itself.
# api.ws imports starlette things at top level; redis imports happen inside functions.
# We set up redis mocks in setup_method via _setup_redis_mocks().

import api.ws
from api.ws import WSToken, WebsocketHandler


class _DummyAuthBackend(AuthenticationBackend):
    def __init__(self, user=None):
        self._user = user or User({'id': 1, 'permissions': []})

    async def authenticate(self, conn):
        return AuthCredentials(['authenticated']), self._user


def _make_app(routes, user=None):
    app = Starlette(
        routes=routes,
        # AuthenticationMiddleware (unlike BaseHTTPMiddleware) runs for
        # websocket connections too, which is what populates scope['user']
        # for the per-user registry in on_connect.
        middleware=[Middleware(AuthenticationMiddleware, backend=_DummyAuthBackend(user))],
    )
    api.ws.set_app(app)
    app.state.ws_state = api.ws.WSState()
    return app


def _setup_redis_mocks():
    rasyncio = types.ModuleType('redis.asyncio')
    rasyncio.Redis = MagicMock(side_effect=ConnectionError('no redis'))
    sys.modules['redis'] = types.ModuleType('redis')
    sys.modules['redis.asyncio'] = rasyncio


def _reset_ws_state(app):
    app.state.ws_state = api.ws.WSState()


class TestWSToken:
    def _make_app(self, user=None):
        return _make_app([Route('/ws_token', endpoint=WSToken)], user)

    def test_generates_token(self):
        with patch('api.ws.gen_token') as mock_gen:
            mock_gen.return_value = 'ws-token-abc'
            client = TestClient(self._make_app())
            resp = client.get('/ws_token')
        assert resp.status_code == 200
        assert resp.json()['token'] == 'ws-token-abc'


class TestWebsocketHandler:
    def setup_method(self):
        _setup_redis_mocks()
        self._app = _make_app([WebSocketRoute('/ws', endpoint=WebsocketHandler)])

    def test_connect_and_disconnect(self):
        client = TestClient(self._app)
        with client.websocket_connect('/ws') as ws:
            ws.send_json({'type': 'open', 'file': '1'})
            resp = ws.receive_json()
            assert resp['type'] == 'send_state'
            assert resp['file'] == '1'

    def test_send_state_without_redis(self):
        client = TestClient(self._app)
        with client.websocket_connect('/ws') as ws:
            ws.send_json({'type': 'open', 'file': '1'})
            ws.receive_json()
            ws.send_json({'type': 'send_state', 'file': '1', 'state': {'window': 80}})

    def test_disconnect_cleans_up_clients(self):
        client = TestClient(self._app)
        with client.websocket_connect('/ws') as ws:
            ws.send_json({'type': 'open', 'file': '1'})
            ws.receive_json()
        assert '1' not in self._app.state.ws_state.local_clients

    def test_connect_registers_user_and_disconnect_unregisters(self):
        app = _make_app([WebSocketRoute('/ws', endpoint=WebsocketHandler)],
                        user=User({'id': 42, 'permissions': []}))
        app.state.ws_state = api.ws.WSState()
        client = TestClient(app)
        with client.websocket_connect('/ws') as ws:
            ws.send_json({'type': 'open', 'file': '1'})
            ws.receive_json()
            assert 42 in app.state.ws_state.user_clients
        assert 42 not in app.state.ws_state.user_clients

    def test_broadcast_to_user(self):
        import asyncio
        app = _make_app([WebSocketRoute('/ws', endpoint=WebsocketHandler)],
                        user=User({'id': 7, 'permissions': []}))
        app.state.ws_state = api.ws.WSState()
        client = TestClient(app)
        with client.websocket_connect('/ws') as ws:
            ws.send_json({'type': 'open', 'file': '1'})
            ws.receive_json()
            asyncio.run(api.ws.broadcast_to_user(7, {'type': 'notifications'}))
            assert ws.receive_json()['type'] == 'notifications'
