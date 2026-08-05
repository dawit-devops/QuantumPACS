import asyncio
import pytest
import redis.asyncio as aioredis


pytestmark = pytest.mark.asyncio


@pytest.fixture
async def redis():
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


class TestStreamProducer:
    async def test_publish_returns_message_id(self, stream_producer, redis):
        msg_id = await stream_producer.publish('events:test', {'event': 'test_event', 'data': 'hello'})
        assert msg_id is not None
        msg_id_str = msg_id.decode() if isinstance(msg_id, bytes) else msg_id
        assert isinstance(msg_id_str, str)
        assert '-' in msg_id_str


class TestStreamConsumer:
    async def test_consume_published_message(self, stream_producer, stream_consumer, redis):
        stream = 'events:test_consume'
        group = 'test-group'
        consumer = 'test-worker'

        await stream_consumer.ensure_group(stream, group)
        await stream_producer.publish(stream, {'event': 'ingestion', 'study_uid': '1.2.3'})

        messages = await stream_consumer.poll(stream, group, consumer, block=2000)
        assert len(messages) == 1

        stream_name, msg_id, msg_data = messages[0]
        assert stream_name == stream
        assert msg_data[b'event'] == b'ingestion'
        assert msg_data[b'study_uid'] == b'1.2.3'

        await stream_consumer.ack(stream, group, msg_id)

    async def test_ack_removes_from_pending(self, stream_producer, stream_consumer, redis):
        stream = 'events:test_ack'
        group = 'test-group-ack'
        consumer = 'test-worker-ack'

        await stream_consumer.ensure_group(stream, group)
        await stream_producer.publish(stream, {'event': 'test'})

        messages = await stream_consumer.poll(stream, group, consumer, block=2000)
        assert len(messages) == 1
        _, msg_id, _ = messages[0]

        await stream_consumer.ack(stream, group, msg_id)

        pending = await stream_consumer.pending(stream, group)
        assert pending['pending'] == 0

    async def test_messages_persist_across_polls(self, stream_producer, stream_consumer, redis):
        stream = 'events:test_persist'
        group = 'test-group-persist'
        consumer = 'test-worker-persist'

        await stream_consumer.ensure_group(stream, group)
        await stream_producer.publish(stream, {'event': 'first'})
        await stream_producer.publish(stream, {'event': 'second'})

        messages = await stream_consumer.poll(stream, group, consumer, count=1, block=2000)
        assert len(messages) == 1
        assert messages[0][2][b'event'] == b'first'

        messages = await stream_consumer.poll(stream, group, consumer, count=1, block=2000)
        assert len(messages) == 1
        assert messages[0][2][b'event'] == b'second'