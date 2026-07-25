import asyncio
import pytest
import redis.asyncio as aioredis

from services.redis_streams import StreamConsumer, StreamProducer
from services.stream_monitor import StreamMonitor

pytestmark = pytest.mark.asyncio

TEST_STREAM = 'events:monitor-test'
TEST_GROUP = 'monitor-group'


@pytest.fixture
async def redis():
    client = aioredis.Redis(
        host='localhost', port=6379, db=9,
        socket_connect_timeout=2, socket_timeout=2,
    )
    try:
        await client.ping()
    except Exception:
        pytest.skip('Redis not available')
    yield client
    try:
        await client.delete(TEST_STREAM)
    except Exception:
        pass
    await client.flushdb()
    await client.aclose()


class TestStreamMonitor:
    async def test_collect_reports_length_and_pending(self, redis):
        consumer = StreamConsumer(redis)
        await consumer.ensure_group(TEST_STREAM, TEST_GROUP)

        monitor = StreamMonitor(consumer)
        monitor.register(TEST_STREAM, TEST_GROUP)
        await monitor.collect()

        data = monitor.metrics()
        assert TEST_STREAM in data
        assert data[TEST_STREAM]['length'] == 0
        assert data[TEST_STREAM]['pending'] == 0

    async def test_collect_reflects_published_messages(self, redis):
        consumer = StreamConsumer(redis)
        producer = StreamProducer(redis)
        await consumer.ensure_group(TEST_STREAM, TEST_GROUP)
        await producer.publish(TEST_STREAM, {'event': 'test'})

        monitor = StreamMonitor(consumer)
        monitor.register(TEST_STREAM, TEST_GROUP)
        await monitor.collect()

        data = monitor.metrics()
        assert data[TEST_STREAM]['length'] >= 1

    async def test_collect_reflects_pending_messages(self, redis):
        consumer = StreamConsumer(redis)
        producer = StreamProducer(redis)
        await consumer.ensure_group(TEST_STREAM, TEST_GROUP)
        await producer.publish(TEST_STREAM, {'event': 'pending-test'})
        await consumer.poll(TEST_STREAM, TEST_GROUP, 'reader', count=10, block=2000)

        monitor = StreamMonitor(consumer)
        monitor.register(TEST_STREAM, TEST_GROUP)
        await monitor.collect()

        data = monitor.metrics()
        assert data[TEST_STREAM]['pending'] >= 1

    async def test_unregister_removes_stream(self, redis):
        consumer = StreamConsumer(redis)
        monitor = StreamMonitor(consumer)
        monitor.register(TEST_STREAM, TEST_GROUP)
        assert TEST_STREAM in monitor.metrics()
        monitor.unregister(TEST_STREAM)
        assert TEST_STREAM not in monitor.metrics()

    async def test_start_stop_loops(self, redis):
        consumer = StreamConsumer(redis)
        await consumer.ensure_group(TEST_STREAM, TEST_GROUP)

        monitor = StreamMonitor(consumer, poll_interval=0.1)
        monitor.register(TEST_STREAM, TEST_GROUP)
        await monitor.start()
        await asyncio.sleep(0.05)
        assert monitor._task is not None

        await monitor.stop()
        assert monitor._task is None