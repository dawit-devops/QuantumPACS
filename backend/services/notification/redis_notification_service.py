import asyncio
import json
from typing import Any

from api.redis_client import get_client
from services.interfaces import NotificationService


class RedisNotificationService(NotificationService):
    def __init__(self, redis_provider=None):
        self._redis_provider = redis_provider or get_client
        self._subscriptions: dict[str, asyncio.Queue] = {}

    async def _get_redis(self):
        if callable(self._redis_provider):
            return await self._redis_provider()
        return self._redis_provider

    async def broadcast(self, channel: str, message: dict[str, Any]) -> bool:
        r = await self._get_redis()
        if r is None:
            return False
        try:
            await r.publish(channel, json.dumps(message))
            return True
        except Exception:
            return False

    async def subscribe(self, channel: str, callback: Any) -> bool:
        r = await self._get_redis()
        if r is None:
            return False
        try:
            pubsub = r.pubsub()
            await pubsub.subscribe(channel)
            queue = asyncio.Queue()
            self._subscriptions[channel] = queue

            async def relay():
                async for msg in pubsub.listen():
                    if msg['type'] == 'message':
                        try:
                            data = json.loads(msg['data'])
                        except (TypeError, ValueError):
                            data = msg['data']
                        try:
                            await callback(data)
                        except Exception:
                            pass

            asyncio.create_task(relay())
            return True
        except Exception:
            return False

    async def unsubscribe(self, channel: str) -> bool:
        try:
            self._subscriptions.pop(channel, None)
            return True
        except Exception:
            return False
