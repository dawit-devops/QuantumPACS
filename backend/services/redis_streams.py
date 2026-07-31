import json
from typing import Any, Optional

from opentelemetry import context as otel_context
from opentelemetry import propagate, trace
from opentelemetry.trace import Status, StatusCode
from redis.exceptions import TimeoutError as RedisTimeoutError

from log import get_logger

log = get_logger(__name__)


def _tracer():
    return trace.get_tracer('quantumpacs.redis')


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
        with _tracer().start_as_current_span('redis.publish') as span:
            span.set_attribute('messaging.destination', stream)
            span.set_attribute('messaging.system', 'redis')

            carrier: dict[str, str] = {}
            propagate.inject(carrier)
            for key, value in carrier.items():
                data[key] = value

            try:
                data_bytes = {k: _serialize(v) for k, v in data.items()}
                msg_id = await self.redis.xadd(
                    stream, data_bytes, maxlen=maxlen, approximate=True,
                )
                span.set_attribute('messaging.message_id', msg_id)
            except Exception as exc:
                span.record_exception(exc)
                span.set_status(Status(StatusCode.ERROR))
                raise
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
        with _tracer().start_as_current_span('redis.consume') as span:
            span.set_attribute('messaging.destination', stream)
            span.set_attribute('messaging.system', 'redis')
            span.set_attribute('messaging.consumer_id', consumer)
            span.set_attribute('messaging.consumer_group', group)
            try:
                result = await self.redis.xreadgroup(
                    group, consumer, {stream: '>'}, count=count, block=block
                )
            except RedisTimeoutError:
                # A blocking read timing out means "no messages arrived within
                # `block` ms" — the normal empty-poll outcome. redis-py maps
                # block to the client read timeout, which can race the server's
                # empty response; treat it as an empty batch, not an error.
                return []
            except Exception as exc:
                span.record_exception(exc)
                span.set_status(Status(StatusCode.ERROR))
                raise
            messages: list[tuple[str, str, dict[bytes, bytes]]] = []
            for stream_name, entries in result:
                for msg_id, msg_data in entries:
                    messages.append((
                        stream_name.decode() if isinstance(stream_name, bytes) else stream_name,
                        msg_id,
                        msg_data,
                    ))
            span.set_attribute('messaging.message_count', len(messages))

        for _stream, msg_id, msg_data in messages:
            carrier = _msg_data_to_carrier(msg_data)
            ctx = propagate.extract(carrier)
            otel_context.attach(ctx)
        return messages

    async def ack(self, stream: str, group: str, msg_id: str) -> None:
        try:
            await self.redis.xack(stream, group, msg_id)
        except Exception as exc:
            log.warning('Failed to ack message %s: %s', msg_id, exc)
            raise

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


def _msg_data_to_carrier(msg_data) -> dict[str, str]:
    carrier: dict[str, str] = {}
    for k, v in msg_data.items():
        if isinstance(k, bytes):
            key = k.decode('utf-8')
        else:
            key = k
        if isinstance(v, bytes):
            val = v.decode('utf-8')
        else:
            val = str(v) if v is not None else ''
        if key.startswith('trace') or key.startswith('baggage'):
            carrier[key] = val
    return carrier
