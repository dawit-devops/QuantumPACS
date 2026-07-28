import asyncio
import json
import pytest
from unittest.mock import AsyncMock, MagicMock

from services.notification.redis_notification_service import RedisNotificationService
from services.interfaces import NotificationService


class TestRedisNotificationService:
    @pytest.fixture
    def redis_mock(self):
        return AsyncMock()

    @pytest.fixture
    def svc(self, redis_mock):
        return RedisNotificationService(redis_provider=lambda: _async_return(redis_mock))

    def test_is_notification_service(self, svc):
        assert hasattr(svc, 'broadcast')
        assert hasattr(svc, 'subscribe')
        assert hasattr(svc, 'unsubscribe')

    async def test_broadcast_returns_false_when_redis_unavailable(self):
        svc = RedisNotificationService(redis_provider=lambda: _async_return(None))
        result = await svc.broadcast('test', {'msg': 'hello'})
        assert result is False

    async def test_broadcast_publishes_message(self, svc, redis_mock):
        result = await svc.broadcast('test-channel', {'msg': 'hello'})
        assert result is True
        redis_mock.publish.assert_called_once_with('test-channel', json.dumps({'msg': 'hello'}))

    async def test_broadcast_returns_false_on_exception(self, svc, redis_mock):
        redis_mock.publish = AsyncMock(side_effect=ConnectionError)
        result = await svc.broadcast('test', {'msg': 'hello'})
        assert result is False

    async def test_subscribe_returns_false_when_redis_unavailable(self):
        svc = RedisNotificationService(redis_provider=lambda: _async_return(None))
        callback = AsyncMock()
        result = await svc.subscribe('test-channel', callback)
        assert result is False

    async def test_subscribe_calls_pubsub_subscribe(self, svc, redis_mock):
        pubsub = AsyncMock()
        redis_mock.pubsub = MagicMock(return_value=pubsub)
        callback = AsyncMock()
        result = await svc.subscribe('test-channel', callback)
        assert result is True
        pubsub.subscribe.assert_called_once_with('test-channel')

    async def test_unsubscribe_returns_true(self, svc):
        result = await svc.unsubscribe('test-channel')
        assert result is True


async def _async_return(value):
    return value
