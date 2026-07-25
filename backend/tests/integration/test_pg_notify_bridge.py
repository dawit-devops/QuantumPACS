import asyncio
import json
import pytest
import redis.asyncio as aioredis

from services.redis_streams import StreamConsumer
from services.pg_notify_bridge import PgNotifyBridge, INGESTION_STREAM

pytestmark = pytest.mark.asyncio


class FakePgConnection:
    def __init__(self):
        self.listeners: dict[str, list] = {}
        self.closed = False

    async def add_listener(self, channel, callback):
        self.listeners.setdefault(channel, []).append(callback)

    async def close(self):
        self.closed = True

    def simulate_notify(self, channel, payload):
        for cb in self.listeners.get(channel, []):
            cb(self, 0, channel, payload)


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
        await client.delete(INGESTION_STREAM)
    except Exception:
        pass
    try:
        await client.xgroup_destroy(INGESTION_STREAM, 'ingestion-service')
    except Exception:
        pass
    await client.flushdb()
    await client.aclose()


async def _dummy_conn():
    return FakePgConnection()


class TestPgNotifyBridge:
    async def test_start_ensures_redis_group(self, redis):
        bridge = PgNotifyBridge(redis=redis, create_conn=_dummy_conn)
        await bridge.start()
        groups = await redis.xinfo_groups(INGESTION_STREAM)
        assert any(
            g.get('name', g.get(b'name', b'')) == b'ingestion-service'
            for g in groups
        )
        await bridge.stop()

    async def _make_bridge(self, redis, conn=None):
        if conn is None:
            conn = FakePgConnection()
        async def make():
            return conn
        bridge = PgNotifyBridge(redis=redis, create_conn=make)
        return bridge, conn

    async def test_file_insert_publishes_to_ingestion_stream(self, redis):
        bridge, conn = await self._make_bridge(redis)
        await bridge.start()

        conn.simulate_notify('events', json.dumps({
            'table': 'files',
            'action': 'INSERT',
            'new': {
                'id': 42, 'name': 'test.dcm', 'hash': 'abc123',
                'patient_id': 1, 'study_id': 2, 'series_id': 3,
            },
            'old': {},
        }))
        await asyncio.sleep(0.2)

        consumer = StreamConsumer(redis)
        await consumer.ensure_group(INGESTION_STREAM, 'test-verify')
        messages = await consumer.poll(
            INGESTION_STREAM, 'test-verify', 'verifier', block=1000,
        )
        assert len(messages) >= 1
        msg_data = messages[0][2]
        decoded = {
            k.decode(): v.decode() if isinstance(v, bytes) else v
            for k, v in msg_data.items()
        }
        assert 'dicom:stored' in decoded.get('event_type', '')
        await bridge.stop()

    async def test_file_insert_event_data(self, redis):
        bridge, conn = await self._make_bridge(redis)
        await bridge.start()

        published = []
        original_publish = bridge._producer.publish
        async def tracking_publish(stream, data, maxlen=100000):
            published.append(data)
            return await original_publish(stream, data, maxlen=maxlen)
        bridge._producer.publish = tracking_publish

        conn.simulate_notify('events', json.dumps({
            'table': 'files',
            'action': 'INSERT',
            'new': {
                'id': 42, 'name': 'test.dcm', 'hash': 'abc123',
                'patient_id': 1, 'study_id': 2, 'series_id': 3,
            },
            'old': {},
        }))
        await asyncio.sleep(0.1)

        assert len(published) >= 1
        event = published[0]
        assert event['event_type'] == 'dicom:stored'
        assert event['data']['file_id'] == '42'
        assert event['data']['path'] == 'test.dcm'
        await bridge.stop()

    async def test_file_delete_publishes_dicom_delete(self, redis):
        bridge, conn = await self._make_bridge(redis)
        await bridge.start()

        published = []
        original_publish = bridge._producer.publish
        async def tracking_publish(stream, data, maxlen=100000):
            published.append(data)
            return await original_publish(stream, data, maxlen=maxlen)
        bridge._producer.publish = tracking_publish

        conn.simulate_notify('events', json.dumps({
            'table': 'files',
            'action': 'DELETE',
            'old': {'id': 99},
            'new': {},
        }))
        await asyncio.sleep(0.1)

        assert len(published) >= 1
        assert published[0]['event_type'] == 'dicom:delete'
        assert published[0]['data']['file_id'] == '99'
        await bridge.stop()

    async def test_other_table_notifications_are_ignored(self, redis):
        bridge, conn = await self._make_bridge(redis)
        await bridge.start()

        published = []
        original_publish = bridge._producer.publish
        async def tracking_publish(stream, data, maxlen=100000):
            published.append(data)
            return await original_publish(stream, data, maxlen=maxlen)
        bridge._producer.publish = tracking_publish

        conn.simulate_notify('events', json.dumps({
            'table': 'replicas',
            'action': 'INSERT',
            'new': {'id': 1, 'location': '/data'},
            'old': {},
        }))
        await asyncio.sleep(0.1)

        assert len(published) == 0
        await bridge.stop()

    async def test_extra_handler_is_called(self, redis):
        bridge, conn = await self._make_bridge(redis)
        extra_called = []
        async def extra_handler(data):
            extra_called.append(data)
        bridge.add_handler(extra_handler)
        await bridge.start()

        conn.simulate_notify('events', json.dumps({
            'table': 'files',
            'action': 'INSERT',
            'new': {'id': 1},
            'old': {},
        }))
        await asyncio.sleep(0.2)

        assert len(extra_called) >= 1
        assert extra_called[0]['table'] == 'files'
        await bridge.stop()

    async def test_stop_closes_pg_connection(self, redis):
        bridge, conn = await self._make_bridge(redis)
        await bridge.start()
        assert not conn.closed
        await bridge.stop()
        assert conn.closed

    async def test_invalid_json_is_ignored(self, redis):
        bridge, conn = await self._make_bridge(redis)
        await bridge.start()

        published = []
        original_publish = bridge._producer.publish
        async def tracking_publish(stream, data, maxlen=100000):
            published.append(data)
            return await original_publish(stream, data, maxlen=maxlen)
        bridge._producer.publish = tracking_publish

        conn.simulate_notify('events', '{invalid json')
        await asyncio.sleep(0.1)
        assert len(published) == 0
        await bridge.stop()