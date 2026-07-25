import json
from typing import Any, Optional
from log import get_logger

log = get_logger(__name__)


class StreamProducer:
    def __init__(self, redis):
        self.redis = redis

    async def ensure_group(self, stream: str, group: str) -> None:
        try:
            await self.redis.xgroup_create(stream, group, id='0', mkstream=True)
        except Exception as e:
            if 'BUSYGROUP' not in str(e):
                raise

    async def publish(
        self,
        stream: str,
        data: dict[str, Any],
        maxlen: int = 100000,
    ) -> str:
        data_bytes = {k: _serialize(v) for k, v in data.items()}
        msg_id = await self.redis.xadd(stream, data_bytes, maxlen=maxlen, approximate=True)
        return msg_id


class StreamConsumer:
    def __init__(self, redis):
        self.redis = redis

    async def ensure_group(self, stream: str, group: str) -> None:
        try:
            await self.redis.xgroup_create(stream, group, id='0', mkstream=True)
        except Exception as e:
            if 'BUSYGROUP' not in str(e):
                raise

    async def poll(
        self,
        stream: str,
        group: str,
        consumer: str,
        count: int = 10,
        block: int = 5000,
    ) -> list[tuple[str, str, dict[bytes, bytes]]]:
        result = await self.redis.xreadgroup(
            group, consumer, {stream: '>'}, count=count, block=block
        )
        messages: list[tuple[str, str, dict[bytes, bytes]]] = []
        for stream_name, entries in result:
            for msg_id, msg_data in entries:
                messages.append((
                    stream_name.decode() if isinstance(stream_name, bytes) else stream_name,
                    msg_id,
                    msg_data,
                ))
        return messages

    async def ack(self, stream: str, group: str, msg_id: str) -> None:
        await self.redis.xack(stream, group, msg_id)

    async def pending(self, stream: str, group: str) -> dict[str, Any]:
        return await self.redis.xpending(stream, group)

    async def pending_detail(
        self,
        stream: str,
        group: str,
        start: str = '-',
        end: str = '+',
        count: int = 10,
        consumer: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        if consumer:
            result = await self.redis.xpending_range(stream, group, start, end, count, consumer)
        else:
            result = await self.redis.xpending_range(stream, group, start, end, count)
        return result

    async def claim(
        self,
        stream: str,
        group: str,
        consumer: str,
        min_idle_time: int = 60000,
        count: int = 10,
    ) -> list[tuple[str, str, dict[bytes, bytes]]]:
        result = await self.redis.xautoclaim(stream, group, consumer, min_idle_time, count=count)
        messages: list[tuple[str, str, dict[bytes, bytes]]] = []
        for msg_id, msg_data in result[1]:
            messages.append((stream, msg_id, msg_data))
        return messages


def _serialize(v: Any) -> bytes:
    if isinstance(v, bytes):
        return v
    if isinstance(v, str):
        return v.encode('utf-8')
    return json.dumps(v, default=str).encode('utf-8')