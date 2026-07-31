import json
from unittest.mock import AsyncMock, MagicMock, patch

from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.routing import WebSocketRoute
from starlette.testclient import TestClient

from api.auth import User
import api.ws
from api.ws import WebsocketHandler


class _FakeAuth(BaseHTTPMiddleware):
    def __init__(self, app, user=None):
        super().__init__(app)
        self._user = user or User({'id': 1, 'permissions': []})

    async def dispatch(self, request, call_next):
        request.scope['user'] = self._user
        request.scope['auth'] = None
        return await call_next(request)


def _make_app(user=None):
    app = Starlette(
        routes=[WebSocketRoute('/ws', endpoint=WebsocketHandler)],
        middleware=[Middleware(_FakeAuth, user=user)],
    )
    api.ws.set_app(app)
    app.state.ws_state = api.ws.WSState()
    return app


_EXPECTED_CHANNEL = 'channel:file:pubsub-file-1'


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
        client = TestClient(self._app)
        with client.websocket_connect('/ws') as ws:
            ws.send_json({'type': 'open', 'file': 'pubsub-file-1'})
            resp = ws.receive_json()
            assert resp['type'] == 'send_state'
            assert resp['file'] == 'pubsub-file-1'

            ws.send_json({
                'type': 'send_state',
                'file': 'pubsub-file-1',
                'state': {'window': 120},
            })

        redis_instance = self._mock_client
        assert redis_instance.publish.called
        channel, raw = redis_instance.publish.call_args[0]
        assert channel == _EXPECTED_CHANNEL
        payload = json.loads(raw)
        assert payload['type'] == 'send_state'
        assert payload['file'] == 'pubsub-file-1'
        assert payload['state']['window'] == 120
        assert redis_instance.aclose.called

    def test_fallback_to_local_when_redis_fails(self):
        self._redis_patcher.stop()
        self._redis_patcher = patch(
            'api.redis_client.get_client',
            new=AsyncMock(side_effect=ConnectionError('no redis')),
        )
        self._redis_patcher.start()

        client = TestClient(self._app)
        with client.websocket_connect('/ws') as ws:
            ws.send_json({'type': 'open', 'file': 'pubsub-file-2'})
            resp = ws.receive_json()
            assert resp['type'] == 'send_state'

            ws.send_json({
                'type': 'send_state',
                'file': 'pubsub-file-2',
                'state': {'zoom': 2},
            })

    def test_multiple_publishes_to_same_channel(self):
        client = TestClient(self._app)
        with client.websocket_connect('/ws') as ws:
            ws.send_json({'type': 'open', 'file': 'pubsub-file-3'})
            ws.receive_json()

            for i in range(3):
                ws.send_json({
                    'type': 'send_state',
                    'file': 'pubsub-file-3',
                    'state': {'counter': i},
                })

        redis_instance = self._mock_client
        assert redis_instance.publish.call_count == 3
        for i, call_args in enumerate(redis_instance.publish.call_args_list):
            channel, raw = call_args[0]
            assert channel == 'channel:file:pubsub-file-3'
            payload = json.loads(raw)
            assert payload['state']['counter'] == i
