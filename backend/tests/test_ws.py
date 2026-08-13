import sys
import types
from unittest.mock import AsyncMock, MagicMock, patch

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
        self._user = user or User({'id': 1, 'permissions': ['FILE_READ']})

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
                        user=User({'id': 42, 'permissions': ['FILE_READ']}))
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
                        user=User({'id': 7, 'permissions': ['FILE_READ']}))
        app.state.ws_state = api.ws.WSState()
        client = TestClient(app)
        with client.websocket_connect('/ws') as ws:
            ws.send_json({'type': 'open', 'file': '1'})
            ws.receive_json()
            asyncio.run(api.ws.broadcast_to_user(7, {'type': 'notifications'}))
            assert ws.receive_json()['type'] == 'notifications'

    def test_open_requires_file_read_permission(self):
        """Subscribing to a file channel grants broadcast membership for that
        file's annotations — users without FILE_READ must get an error frame
        and must not be registered in the channel."""
        app = _make_app([WebSocketRoute('/ws', endpoint=WebsocketHandler)],
                        user=User({'id': 99, 'permissions': []}))
        app.state.ws_state = api.ws.WSState()
        client = TestClient(app)
        with client.websocket_connect('/ws') as ws:
            ws.send_json({'type': 'open', 'file': '5'})
            resp = ws.receive_json()
            assert resp['type'] == 'error'
            assert 'FILE_READ' in resp['message']
        assert '5' not in app.state.ws_state.local_clients
        assert 99 not in app.state.ws_state.user_clients

    def test_open_denied_when_no_user_on_scope(self):
        # No AuthenticationMiddleware → scope['user'] never set → the open
        # handler must deny instead of subscribing an anonymous socket.
        app = Starlette(routes=[WebSocketRoute('/ws', endpoint=WebsocketHandler)])
        api.ws.set_app(app)
        app.state.ws_state = api.ws.WSState()
        client = TestClient(app)
        with client.websocket_connect('/ws') as ws:
            ws.send_json({'type': 'open', 'file': '5'})
            resp = ws.receive_json()
            assert resp['type'] == 'error'
        assert '5' not in app.state.ws_state.local_clients

    def test_open_registers_tenant_qualified_channel(self):
        """N3: the broadcast registry must be keyed by the tenant-qualified
        channel — the same file id from different tenants must never share a
        channel."""
        app = _make_app([WebSocketRoute('/ws', endpoint=WebsocketHandler)],
                        user=User({'id': 5, 'permissions': ['FILE_READ'], 'tenant': 'ten-a'}))
        app.state.ws_state = api.ws.WSState()
        client = TestClient(app)
        with client.websocket_connect('/ws') as ws:
            ws.send_json({'type': 'open', 'file': '1'})
            resp = ws.receive_json()
            assert resp['type'] == 'send_state'
            # Assert while connected: on_disconnect removes the socket from
            # the registry, so membership checks after the `with` block
            # would trivially pass/fail on an empty map.
            assert 'channel:file:ten-a:1' in app.state.ws_state.local_clients
        assert 'channel:file:1' not in app.state.ws_state.local_clients

    def test_send_state_requires_file_read_permission(self):
        """NEW #2: publishing to a file channel is the write side of the
        'open' broadcast membership — a socket without FILE_READ gets an
        error frame and nothing is published."""
        app = _make_app([WebSocketRoute('/ws', endpoint=WebsocketHandler)],
                        user=User({'id': 99, 'permissions': []}))
        app.state.ws_state = api.ws.WSState()
        client = TestClient(app)
        with client.websocket_connect('/ws') as ws:
            ws.send_json({'type': 'send_state', 'file': '5', 'state': {'x': 1}})
            resp = ws.receive_json()
            assert resp['type'] == 'error'
            assert 'FILE_READ' in resp['message']
        assert 'channel:file::5' not in app.state.ws_state.local_clients

    def test_send_state_invalid_payload_no_keyerror(self):
        """NEW #2: missing file/state must yield an error frame, never a
        KeyError from direct dict access."""
        app = _make_app([WebSocketRoute('/ws', endpoint=WebsocketHandler)])
        app.state.ws_state = api.ws.WSState()
        client = TestClient(app)
        with client.websocket_connect('/ws') as ws:
            ws.send_json({'type': 'send_state'})
            resp = ws.receive_json()
            assert resp['type'] == 'error'

    def test_open_missing_file_no_keyerror(self):
        app = _make_app([WebSocketRoute('/ws', endpoint=WebsocketHandler)])
        app.state.ws_state = api.ws.WSState()
        client = TestClient(app)
        with client.websocket_connect('/ws') as ws:
            ws.send_json({'type': 'open'})
            resp = ws.receive_json()
            assert resp['type'] == 'error'

    def test_open_accepts_wadouri_image_url(self):
        """CornerstoneElement opens the channel with the wadouri image URL
        (`wadouri:{API_URL}/files/{id}/data`); the handler must normalize it
        to the file id for the bigint lookup instead of crashing with an
        asyncpg type error."""
        app = _make_app([WebSocketRoute('/ws', endpoint=WebsocketHandler)],
                        user=User({'id': 5, 'permissions': ['FILE_READ']}))
        app.state.ws_state = api.ws.WSState()
        client = TestClient(app)

        file_row = {'id': 65, 'deleted': False, 'tenant': None}
        fake_conn = MagicMock()
        fake_conn.__aenter__ = AsyncMock(return_value=fake_conn)
        fake_conn.__aexit__ = AsyncMock(return_value=False)
        with patch('api.ws.get_conn', return_value=fake_conn), \
             patch('api.ws.Files') as files_cls:
            files_cls.return_value.get_extra = AsyncMock(return_value=file_row)
            with client.websocket_connect('/ws') as ws:
                ws.send_json({
                    'type': 'open',
                    'file': 'wadouri:http://localhost:8080/api/files/65/data',
                })
                resp = ws.receive_json()
                assert resp['type'] == 'send_state'
                # The lookup ran on the parsed numeric id, never the URL
                # string. (Assert while connected — on_disconnect purges the
                # registry, same as the sibling channel tests.)
                files_cls.return_value.get_extra.assert_awaited_once_with(65)
                assert 'channel:file::65' in app.state.ws_state.local_clients

    def test_cross_tenant_file_ids_get_distinct_channels(self):
        """N3: same file id under two tenants must land in separate channel
        namespaces — per-tenant SERIAL ids collide otherwise."""
        app_a = _make_app([WebSocketRoute('/ws', endpoint=WebsocketHandler)],
                          user=User({'id': 1, 'permissions': ['FILE_READ'], 'tenant': 'ten-a'}))
        app_b = _make_app([WebSocketRoute('/ws', endpoint=WebsocketHandler)],
                          user=User({'id': 2, 'permissions': ['FILE_READ'], 'tenant': 'ten-b'}))
        shared = api.ws.WSState()
        app_a.state.ws_state = shared
        app_b.state.ws_state = shared
        api.ws.set_app(app_a)
        client_a = TestClient(app_a)
        with client_a.websocket_connect('/ws') as wa:
            wa.send_json({'type': 'open', 'file': '99'})
            assert wa.receive_json()['type'] == 'send_state'
            assert 'channel:file:ten-a:99' in shared.local_clients
        api.ws.set_app(app_b)
        client_b = TestClient(app_b)
        with client_b.websocket_connect('/ws') as wb:
            wb.send_json({'type': 'open', 'file': '99'})
            assert wb.receive_json()['type'] == 'send_state'
            assert 'channel:file:ten-b:99' in shared.local_clients
