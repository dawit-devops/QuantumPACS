import asyncio
import pytest
import redis.asyncio as aioredis

from services.ingestion import IngestionWorker, IngestionHandler
from services.redis_streams import StreamProducer

pytestmark = pytest.mark.asyncio

INGESTION_STREAM = 'events:ingestion'
INGESTION_GROUP = 'ingestion-service'
CONSUMER_NAME = 'test-consumer'


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
        await client.xgroup_destroy(INGESTION_STREAM, INGESTION_GROUP)
    except Exception:
        pass
    try:
        await client.delete(INGESTION_STREAM)
    except Exception:
        pass
    await client.flushdb()
    await client.aclose()
    await asyncio.sleep(0)


class TestIngestionWorkerIntegration:
    async def test_worker_starts_and_ensures_group(self, redis):
        worker = IngestionWorker(redis=redis, handler=IngestionHandler())
        await worker.start()
        groups = await redis.xinfo_groups(INGESTION_STREAM)
        assert any(
            g.get('name', g.get(b'name', b'')) == INGESTION_GROUP.encode()
            for g in groups
        )

    async def test_worker_processes_single_message(self, redis):
        producer = StreamProducer(redis)
        await producer.publish(INGESTION_STREAM, {
            'event_type': 'dicom:stored',
            'data': {'path': 'test.dcm'},
        })

        captured = []
        class TrackingHandler(IngestionHandler):
            async def handle(self, event_type, data):
                captured.append((event_type, data))
                return True

        worker = IngestionWorker(redis=redis, handler=TrackingHandler())
        await worker.start()
        count = await worker.run_once()
        assert count == 1
        assert len(captured) == 1
        assert captured[0][0] == 'dicom:stored'

    async def test_worker_acks_messages_after_success(self, redis):
        producer = StreamProducer(redis)
        await producer.publish(INGESTION_STREAM, {
            'event_type': 'dicom:stored',
            'data': {'path': 'ack-test.dcm'},
        })

        worker = IngestionWorker(
            redis=redis, handler=IngestionHandler(),
            consumer_name=CONSUMER_NAME,
        )
        await worker.start()
        await worker.run_once()
        pending = await redis.xpending(INGESTION_STREAM, INGESTION_GROUP)
        assert pending['pending'] == 0

    async def test_worker_retries_on_failure_then_does_not_ack(self, redis):
        producer = StreamProducer(redis)
        await producer.publish(INGESTION_STREAM, {
            'event_type': 'dicom:stored',
            'data': {'path': 'retry-test.dcm'},
        })

        call_count = 0
        class FailingHandler(IngestionHandler):
            async def handle(self, event_type, data):
                nonlocal call_count
                call_count += 1
                return False

        worker = IngestionWorker(
            redis=redis, handler=FailingHandler(),
            consumer_name=CONSUMER_NAME, max_retries=1,
        )
        await worker.start()
        await worker.run_once()
        pending = await redis.xpending(INGESTION_STREAM, INGESTION_GROUP)
        assert pending['pending'] > 0

    async def test_multiple_messages_processed(self, redis):
        producer = StreamProducer(redis)
        await producer.publish(INGESTION_STREAM, {
            'event_type': 'dicom:stored',
            'data': {'path': 'a.dcm'},
        })
        await producer.publish(INGESTION_STREAM, {
            'event_type': 'dicom:stored',
            'data': {'path': 'b.dcm'},
        })

        processed = []
        class TrackingHandler(IngestionHandler):
            async def handle(self, event_type, data):
                processed.append(data)
                return True

        worker = IngestionWorker(
            redis=redis, handler=TrackingHandler(),
            consumer_name=CONSUMER_NAME,
        )
        await worker.start()
        count = await worker.run_once()
        assert count == 2
        assert len(processed) == 2