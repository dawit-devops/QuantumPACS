import asyncio
import json
import signal
from typing import Any, Optional

from config import config
from log import get_logger
from services.redis_streams import StreamConsumer, StreamProducer
from .handler import IngestionHandler

log = get_logger(__name__)

INGESTION_STREAM = config.get('ingestion_stream', 'events:ingestion')
INGESTION_GROUP = config.get('ingestion_group', 'ingestion-service')
INGESTION_CONSUMER = config.get('ingestion_consumer', 'worker-1')
POLL_COUNT = int(config.get('ingestion_poll_count', '10'))
POLL_BLOCK_MS = int(config.get('ingestion_poll_block_ms', '5000'))
MAX_RETRIES = int(config.get('ingestion_max_retries', '3'))


class IngestionWorker:
    def __init__(
        self,
        redis,
        handler: IngestionHandler,
        consumer: Optional[StreamConsumer] = None,
        producer: Optional[StreamProducer] = None,
        group: str = INGESTION_GROUP,
        consumer_name: str = INGESTION_CONSUMER,
        poll_count: int = POLL_COUNT,
        poll_block_ms: int = POLL_BLOCK_MS,
        max_retries: int = MAX_RETRIES,
    ):
        self.redis = redis
        self.handler = handler
        self.consumer = consumer or StreamConsumer(redis)
        self.producer = producer or StreamProducer(redis)
        self.group = group
        self.consumer_name = consumer_name
        self.poll_count = poll_count
        self.poll_block_ms = poll_block_ms
        self.max_retries = max_retries
        self._shutdown = asyncio.Event()

    async def start(self) -> None:
        log.info(
            'starting ingestion worker (group=%s, consumer=%s)',
            self.group, self.consumer_name,
        )
        await self.consumer.ensure_group(INGESTION_STREAM, self.group)
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGTERM, signal.SIGINT):
            try:
                loop.add_signal_handler(sig, self._shutdown.set)
            except NotImplementedError:
                pass

    async def run_once(self) -> int:
        messages = await self.consumer.poll(
            INGESTION_STREAM, self.group, self.consumer_name,
            count=self.poll_count, block=self.poll_block_ms,
        )
        for stream_name, msg_id, msg_data in messages:
            try:
                payload = _deserialize(msg_data)
                event_type = payload.get('event_type', '')
                data = payload.get('data', {})
                success = await self._process_with_retry(event_type, data, msg_id)
                if success:
                    await self.consumer.ack(INGESTION_STREAM, self.group, msg_id)
            except Exception:
                log.exception('failed to process message %s', msg_id)
        return len(messages)

    async def _process_with_retry(
        self, event_type: str, data: dict[str, Any], msg_id: str,
    ) -> bool:
        for attempt in range(1, self.max_retries + 1):
            success = await self.handler.handle(event_type, data)
            if success:
                return True
            if attempt < self.max_retries:
                log.warning(
                    'retry %d/%d for message %s (%s)',
                    attempt, self.max_retries, msg_id, event_type,
                )
                await asyncio.sleep(1 * attempt)
        log.error(
            'message %s failed after %d retries (%s)',
            msg_id, self.max_retries, event_type,
        )
        return False

    async def run(self) -> None:
        await self.start()
        log.info('ingestion worker entering poll loop')
        while not self._shutdown.is_set():
            try:
                processed = await self.run_once()
                if processed:
                    log.debug('processed %d messages', processed)
            except asyncio.CancelledError:
                break
            except Exception:
                log.exception('poll loop error')
                await asyncio.sleep(1)
        log.info('ingestion worker stopped')


def _deserialize(msg_data: dict[bytes, bytes]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for k, v in msg_data.items():
        key = k.decode('utf-8') if isinstance(k, bytes) else k
        val = v.decode('utf-8') if isinstance(v, bytes) else v
        try:
            result[key] = json.loads(val)
        except (json.JSONDecodeError, TypeError):
            result[key] = val
    return result