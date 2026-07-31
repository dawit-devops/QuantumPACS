import asyncio
import importlib
import sys
import types
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.fixture
def _redis_env():
    saved = {k: sys.modules.get(k) for k in ('redis', 'redis.asyncio', 'api.redis_client')}
    for k in ('api.redis_client',):
        sys.modules.pop(k, None)
    yield
    for k, v in saved.items():
        if v is not None:
            sys.modules[k] = v
        else:
            sys.modules.pop(k, None)


def _setup_redis(redis_constructor):
    rasyncio = types.ModuleType('redis.asyncio')
    rasyncio.Redis = redis_constructor
    sys.modules['redis'] = types.ModuleType('redis')
    sys.modules['redis.asyncio'] = rasyncio


def _get_reloadee():
    import api.redis_client
    importlib.reload(api.redis_client)
    rc = api.redis_client
    rc._redis = None
    rc._redis_available = False
    return rc


class TestRedisClient:
    def test_get_client_when_available(self, _redis_env):
        mock_redis = AsyncMock(spec=['ping', 'aclose'])
        mock_redis.ping = AsyncMock(return_value=True)
        _setup_redis(MagicMock(return_value=mock_redis))
        rc = _get_reloadee()
        with patch('api.redis_client.config', {'redis_host': 'localhost', 'redis_port': '6379', 'redis_password': ''}):
            client = asyncio.run(rc.get_client())
        assert client is mock_redis
        mock_redis.ping.assert_called_once()

    def test_get_client_when_unavailable(self, _redis_env):
        _setup_redis(MagicMock(side_effect=ConnectionError('refused')))
        rc = _get_reloadee()
        with patch('api.redis_client.config', {'redis_host': 'localhost', 'redis_port': '6379', 'redis_password': ''}):
            client = asyncio.run(rc.get_client())
        assert client is None

    def test_get_client_returns_same_instance(self, _redis_env):
        mock_redis = AsyncMock(spec=['ping', 'aclose'])
        mock_redis.ping = AsyncMock(return_value=True)
        _setup_redis(MagicMock(return_value=mock_redis))
        rc = _get_reloadee()
        with patch('api.redis_client.config', {'redis_host': 'localhost', 'redis_port': '6379', 'redis_password': ''}):
            c1 = asyncio.run(rc.get_client())
            c2 = asyncio.run(rc.get_client())
        assert c2 is c1

    def test_is_available_defaults_false(self, _redis_env):
        rc = _get_reloadee()
        assert rc.is_available() is False

    def test_close_client_resets_state(self, _redis_env):
        mock_redis = AsyncMock(spec=['ping', 'aclose'])
        mock_redis.ping = AsyncMock(return_value=True)
        mock_redis.aclose = AsyncMock()
        _setup_redis(MagicMock(return_value=mock_redis))
        rc = _get_reloadee()
        with patch('api.redis_client.config', {'redis_host': 'localhost', 'redis_port': '6379', 'redis_password': ''}):
            asyncio.run(rc.get_client())
            assert rc.is_available() is True
            asyncio.run(rc.close_client())
        mock_redis.aclose.assert_called_once()
        assert rc.is_available() is False

    def test_close_client_idempotent(self, _redis_env):
        rc = _get_reloadee()
        asyncio.run(rc.close_client())
        assert rc.is_available() is False
