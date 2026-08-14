import json
from contextlib import ExitStack
from unittest.mock import AsyncMock, MagicMock, patch

from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.routing import WebSocketRoute
from starlette.testclient import TestClient

from api.auth import User
from api.permissions import Permission
import api.ws
from api.ws import WebsocketHandler


def _patch_file_lookup(file_row=None):
    """The 'open' handler resolves the target file on the DB (M-5 tenant
    gate); unit tests stub the lookup so the pool is never touched."""
    if file_row is None:
        file_row = {'id': 1, 'deleted': False, 'tenant': None}
    fake_conn = MagicMock()
    fake_conn.__aenter__ = AsyncMock(return_value=fake_conn)
    fake_conn.__aexit__ = AsyncMock(return_value=False)
    files_cls = MagicMock()
    files_cls.return_value.get_extra = AsyncMock(return_value=file_row)
    return (
        patch('api.ws.get_conn', return_value=fake_conn),
        patch('api.ws.Files', files_cls),
    )


class _FakeAuth:
    """Pure ASGI middleware setting scope['user'].

    BaseHTTPMiddleware cannot be used here: starlette 1.x does not propagate
    its scope mutations to websocket endpoints, so the ws authz gate would
    see an anonymous user.
    """

    def __init__(self, app, user=None):
        self.app = app
        # Default user holds FILE_READ so channel open passes the ws authz gate.
        self.user = user or User({'id': 1, 'permissions': [Permission.FILE_READ]})

    async def __call__(self, scope, receive, send):
        if scope['type'] in ('http', 'websocket'):
            scope['user'] = self.user
            scope['auth'] = None
        await self.app(scope, receive, send)


def _make_app(user=None):
    app = Starlette(
        routes=[WebSocketRoute('/ws', endpoint=WebsocketHandler)],
        middleware=[Middleware(_FakeAuth, user=user)],
    )
    api.ws.set_app(app)
    app.state.ws_state = api.ws.WSState()
    return app


_EXPECTED_CHANNEL = 'channel:file::101'


def _setup_redis_mocks():
    mock_client = MagicMock()
    mock_client.publish = AsyncMock()
    mock_client.aclose = AsyncMock()
    patcher = patch('api.redis_client.get_client', new=AsyncMock(return_value=mock_client))
    patcher.start()
    return patcher, mock_client


def _reset_ws_state(app):
    app.state.ws_state = api.ws.WSState()


class TestWebsocketPubSub:
    def setup_method(self):
        self._redis_patcher, self._mock_client = _setup_redis_mocks()
        self._app = _make_app()

    def teardown_method(self):
        self._redis_patcher.stop()

    def test_publish_to_channel(self):
        with ExitStack() as stack:
            for p in _patch_file_lookup():
                stack.enter_context(p)
            client = TestClient(self._app)
            with client.websocket_connect('/ws') as ws:
                ws.send_json({'type': 'open', 'file': '101'})
                resp = ws.receive_json()
                assert resp['type'] == 'send_state'
                assert resp['file'] == '101'

                ws.send_json({
                    'type': 'send_state',
                    'file': '101',
                    'state': {'window': 120},
                })

        redis_instance = self._mock_client
        assert redis_instance.publish.called
        channel, raw = redis_instance.publish.call_args[0]
        assert channel == _EXPECTED_CHANNEL
        payload = json.loads(raw)
        assert payload['type'] == 'send_state'
        assert payload['file'] == '101'
        assert payload['state']['window'] == 120
        assert redis_instance.aclose.called

    def test_fallback_to_local_when_redis_fails(self):
        self._redis_patcher.stop()
        self._redis_patcher = patch(
            'api.redis_client.get_client',
            new=AsyncMock(side_effect=ConnectionError('no redis')),
        )
        self._redis_patcher.start()

        with ExitStack() as stack:
            for p in _patch_file_lookup():
                stack.enter_context(p)
            client = TestClient(self._app)
            with client.websocket_connect('/ws') as ws:
                ws.send_json({'type': 'open', 'file': '102'})
                resp = ws.receive_json()
                assert resp['type'] == 'send_state'

                ws.send_json({
                    'type': 'send_state',
                    'file': '102',
                    'state': {'zoom': 2},
                })

    def test_multiple_publishes_to_same_channel(self):
        with ExitStack() as stack:
            for p in _patch_file_lookup():
                stack.enter_context(p)
            client = TestClient(self._app)
            with client.websocket_connect('/ws') as ws:
                ws.send_json({'type': 'open', 'file': '103'})
                ws.receive_json()

                for i in range(3):
                    ws.send_json({
                        'type': 'send_state',
                        'file': '103',
                        'state': {'counter': i},
                    })

        redis_instance = self._mock_client
        assert redis_instance.publish.call_count == 3
        for i, call_args in enumerate(redis_instance.publish.call_args_list):
            channel, raw = call_args[0]
            assert channel == 'channel:file::103'
            payload = json.loads(raw)
            assert payload['state']['counter'] == i

    def test_publish_targets_tenant_qualified_channel(self):
        """N3: a send_state must publish to the sender's tenant-qualified
        channel, never the bare file channel."""
        self._app = _make_app(
            user=User({'id': 1, 'permissions': [Permission.FILE_READ], 'tenant': 'ten-a'}),
        )
        with ExitStack() as stack:
            for p in _patch_file_lookup():
                stack.enter_context(p)
            client = TestClient(self._app)
            with client.websocket_connect('/ws') as ws:
                ws.send_json({'type': 'open', 'file': '42'})
                assert ws.receive_json()['type'] == 'send_state'
                ws.send_json({'type': 'send_state', 'file': '42', 'state': {'zoom': 4}})
        channel, _ = self._mock_client.publish.call_args[0]
        assert channel == 'channel:file:ten-a:42'

    def test_cross_tenant_publish_never_leaks_to_other_tenant(self):
        """N3: sockets of two tenants on the same file id must end up on
        disjoint channels — tenant B publishing may only reach
        channel:file:ten-b:*, never ten-a's namespace."""
        self._app = _make_app(
            user=User({'id': 1, 'permissions': [Permission.FILE_READ], 'tenant': 'ten-a'}),
        )
        with ExitStack() as stack:
            for p in _patch_file_lookup():
                stack.enter_context(p)
            client = TestClient(self._app)
            with client.websocket_connect('/ws') as ws:
                ws.send_json({'type': 'open', 'file': '7'})
                assert ws.receive_json()['type'] == 'send_state'
                ws.send_json({'type': 'send_state', 'file': '7', 'state': {'x': 1}})
        channels = {call_args[0][0] for call_args in self._mock_client.publish.call_args_list}
        assert channels == {'channel:file:ten-a:7'}

    def test_send_state_without_file_read_not_published(self):
        """NEW #2: unauthorized send_state must not publish anything."""
        self._app = _make_app(
            user=User({'id': 9, 'permissions': [], 'tenant': 'ten-a'}),
        )
        client = TestClient(self._app)
        with client.websocket_connect('/ws') as ws:
            ws.send_json({'type': 'send_state', 'file': '7', 'state': {'x': 1}})
            resp = ws.receive_json()
            assert resp['type'] == 'error'
        assert not self._mock_client.publish.called
