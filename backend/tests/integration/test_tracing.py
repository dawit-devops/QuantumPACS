from unittest.mock import AsyncMock, MagicMock, patch

import asyncio

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

import pytest


pytestmark = pytest.mark.asyncio


@pytest.fixture
async def redis():
    import redis.asyncio as aioredis
    client = aioredis.Redis(
        host='localhost', port=6379, db=9,
        socket_connect_timeout=2,
        socket_timeout=2,
    )
    try:
        await client.ping()
    except Exception:
        pytest.skip('Redis not available')
    yield client
    await client.flushdb()
    await client.aclose()
    await asyncio.sleep(0)


@pytest.fixture
async def stream_producer(redis):
    from services.redis_streams import StreamProducer
    return StreamProducer(redis)


@pytest.fixture
async def stream_consumer(redis):
    from services.redis_streams import StreamConsumer
    return StreamConsumer(redis)


@pytest.fixture
def span_exporter():
    import opentelemetry.trace as ot
    original_provider = ot._TRACER_PROVIDER
    original_done = ot._TRACER_PROVIDER_SET_ONCE._done
    ot._TRACER_PROVIDER_SET_ONCE._done = False

    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    trace.set_tracer_provider(provider)
    yield exporter

    ot._TRACER_PROVIDER_SET_ONCE._done = original_done
    ot._TRACER_PROVIDER = original_provider


class TestAsyncpgTracing:
    async def test_db_fetchval_produces_span(self, span_exporter):
        from api.tracing import traced_connection

        fake_conn = AsyncMock()
        fake_conn.fetchval = AsyncMock(return_value=1)
        fake_ctx = AsyncMock()
        fake_ctx.__aenter__ = AsyncMock(return_value=fake_conn)
        fake_ctx.__aexit__ = AsyncMock(return_value=None)
        fake_pool = MagicMock()
        fake_pool.acquire = MagicMock(return_value=fake_ctx)

        traced = traced_connection(fake_pool)
        async with traced.acquire() as conn:
            val = await conn.fetchval('SELECT 1')
        assert val == 1
        spans = span_exporter.get_finished_spans()
        query_spans = [s for s in spans if s.name == 'db.query']
        assert len(query_spans) >= 1
        assert query_spans[0].attributes.get('db.statement') == 'SELECT 1'


class TestRedisStreamTracing:
    async def test_redis_publish_produces_span(self, span_exporter, redis):
        from services.redis_streams import StreamProducer
        producer = StreamProducer(redis)
        msg_id = await producer.publish('events:trace', {'event': 'test'})
        assert msg_id is not None
        spans = span_exporter.get_finished_spans()
        publish_spans = [s for s in spans if s.name == 'redis.publish']
        assert len(publish_spans) == 1
        assert publish_spans[0].attributes.get('messaging.destination') == 'events:trace'

    async def test_redis_consume_produces_span(self, span_exporter, stream_producer, stream_consumer, redis):
        stream = 'events:trace_consume'
        group = 'trace-group'
        consumer = 'trace-worker'
        await stream_consumer.ensure_group(stream, group)
        await stream_producer.publish(stream, {'event': 'trace_test'})
        messages = await stream_consumer.poll(stream, group, consumer, block=2000)
        assert len(messages) == 1
        spans = span_exporter.get_finished_spans()
        consume_spans = [s for s in spans if s.name == 'redis.consume']
        assert len(consume_spans) >= 1