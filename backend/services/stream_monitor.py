import asyncio
import time
from typing import Any, Optional

from log import get_logger
from services.redis_streams import StreamConsumer

log = get_logger(__name__)


class StreamMonitor:
    def __init__(
        self,
        consumer: StreamConsumer,
        poll_interval: float = 15.0,
    ):
        self.consumer = consumer
        self.poll_interval = poll_interval
        self._task: Optional[asyncio.Task] = None
        self._shutdown = asyncio.Event()

        self.streams: dict[str, dict[str, Any]] = {}

    def register(self, stream: str, group: str) -> None:
        self.streams[stream] = {
            'group': group,
            'length': 0,
            'pending': 0,
            'last_checked': 0.0,
        }

    def unregister(self, stream: str) -> None:
        self.streams.pop(stream, None)

    def metrics(self) -> dict[str, Any]:
        return {
            name: {
                'group': info['group'],
                'length': info['length'],
                'pending': info['pending'],
            }
            for name, info in self.streams.items()
        }

    async def collect(self) -> None:
        from api.telemetry import redis_stream_lag_seconds
        redis = self.consumer.redis
        for stream, info in self.streams.items():
            try:
                info['length'] = await redis.xlen(stream)
                pending = await self.consumer.pending(stream, info['group'])
                info['pending'] = pending.get('pending', 0) if isinstance(pending, dict) else 0
                redis_stream_lag_seconds.labels(stream=stream, consumer_group=info['group']).set(info['pending'])
            except Exception:
                log.debug('failed to collect metrics for %s', stream)
            info['last_checked'] = time.monotonic()

    async def _loop(self) -> None:
        while not self._shutdown.is_set():
            await self.collect()
            try:
                await asyncio.wait_for(
                    self._shutdown.wait(),
                    timeout=self.poll_interval,
                )
                break
            except asyncio.TimeoutError:
                pass

    async def start(self) -> None:
        await self.collect()
        self._task = asyncio.create_task(self._loop())

    async def stop(self) -> None:
        self._shutdown.set()
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except (asyncio.CancelledError, Exception):
                pass
            self._task = None


__all__ = ['StreamMonitor']