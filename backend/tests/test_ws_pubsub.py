import json
import sys
import types
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.routing import WebSocketRoute
from starlette.testclient import TestClient

from api.auth import User
from api.ws import WebsocketHandler, local_clients


class _FakeAuth(BaseHTTPMiddleware):
    def __init__(self, app, user=None):
        super().__init__(app)
        self._user = user or User({'id': 1, 'permissions': []})

    async def dispatch(self, request, call_next):
        request.scope['user'] = self._user
        request.scope['auth'] = None
        return await call_next(request)


def _make_app(user=None):
    return Starlette(
        routes=[WebSocketRoute('/ws', endpoint=WebsocketHandler)],
        middleware=[Middleware(_FakeAuth, user=user)],
    )


_EXPECTED_CHANNEL = 'channel:file:pubsub-file-1'


def _setup_redis_mocks():
    rasyncio = types.ModuleType('redis.asyncio')
    rasyncio.Redis = MagicMock()
    sys.modules['redis'] = types.ModuleType('redis')
    sys.modules['redis.asyncio'] = rasyncio


def _reset_ws_globals():
    local_clients.clear()
    import api.ws
    api.ws._listener_task = None
    api.ws._cleanup_task = None
    api.ws._pubsub = None


class TestWebsocketPubSub:
    def setup_method(self):
        _setup_redis_mocks()
        _reset_ws_globals()

    def test_publish_to_channel(self):
        client = TestClient(_make_app())
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

        redis_cls = sys.modules['redis.asyncio'].Redis
        redis_instance = redis_cls.return_value
        assert redis_instance.publish.called
        channel, raw = redis_instance.publish.call_args[0]
        assert channel == _EXPECTED_CHANNEL
        payload = json.loads(raw)
        assert payload['type'] == 'send_state'
        assert payload['file'] == 'pubsub-file-1'
        assert payload['state']['window'] == 120
        assert redis_instance.aclose.called

    def test_fallback_to_local_when_redis_fails(self):
        rasyncio = sys.modules['redis.asyncio']
        rasyncio.Redis = MagicMock(side_effect=ConnectionError('no redis'))

        client = TestClient(_make_app())
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
        client = TestClient(_make_app())
        with client.websocket_connect('/ws') as ws:
            ws.send_json({'type': 'open', 'file': 'pubsub-file-3'})
            ws.receive_json()

            for i in range(3):
                ws.send_json({
                    'type': 'send_state',
                    'file': 'pubsub-file-3',
                    'state': {'counter': i},
                })

        redis_cls = sys.modules['redis.asyncio'].Redis
        redis_instance = redis_cls.return_value
        assert redis_instance.publish.call_count == 3
        for i, call_args in enumerate(redis_instance.publish.call_args_list):
            channel, raw = call_args[0]
            assert channel == 'channel:file:pubsub-file-3'
            payload = json.loads(raw)
            assert payload['state']['counter'] == i
