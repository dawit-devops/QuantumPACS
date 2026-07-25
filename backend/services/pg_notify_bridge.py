import asyncio
import json
from typing import Any, Optional, Callable, Awaitable

from log import get_logger
from services.redis_streams import StreamProducer

log = get_logger(__name__)

EVENTS_CHANNEL = 'events'
INGESTION_STREAM = 'events:ingestion'
INGESTION_CONSUMER_GROUP = 'ingestion-service'

OnNotification = Callable[[dict[str, Any]], Awaitable[None]]


class PgNotifyBridge:
    def __init__(
        self,
        redis,
        create_conn: Callable[[], Awaitable[Any]],
        stream: str = INGESTION_STREAM,
        group: str = INGESTION_CONSUMER_GROUP,
    ):
        self.redis = redis
        self._create_conn = create_conn
        self.stream = stream
        self.group = group
        self._conn: Optional[Any] = None
        self._producer: Optional[StreamProducer] = None
        self._task: Optional[asyncio.Task] = None
        self._shutdown = asyncio.Event()
        self._extra_handlers: list[OnNotification] = []

    def add_handler(self, handler: OnNotification) -> None:
        self._extra_handlers.append(handler)

    async def start(self) -> None:
        self._producer = StreamProducer(self.redis)
        await self._producer.ensure_group(self.stream, self.group)
        self._conn = await self._create_conn()
        await self._conn.add_listener(EVENTS_CHANNEL, self._on_notification)
        self._task = asyncio.create_task(self._run())

    async def stop(self) -> None:
        self._shutdown.set()
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except (asyncio.CancelledError, Exception):
                pass
            self._task = None
        if self._conn:
            try:
                await self._conn.close()
            except Exception:
                pass
            self._conn = None

    async def _run(self) -> None:
        while not self._shutdown.is_set():
            try:
                await asyncio.sleep(1)
            except asyncio.CancelledError:
                break

    def _on_notification(self, conn: Any, pid: int, channel: str, payload: str) -> None:
        try:
            data = json.loads(payload)
        except json.JSONDecodeError:
            log.warning('invalid notify payload: %s', payload)
            return
        table = data.get('table', '')
        action = data.get('action', '')
        new_row = data.get('new', {})
        old_row = data.get('old', {})

        if table == 'files':
            asyncio.ensure_future(self._publish_file_event(action, new_row, old_row))

        for handler in self._extra_handlers:
            asyncio.ensure_future(handler(data))

    async def _publish_file_event(
        self, action: str, new_row: dict[str, Any], old_row: dict[str, Any],
    ) -> None:
        if action == 'INSERT':
            event_type = 'dicom:stored'
        elif action == 'DELETE':
            event_type = 'dicom:delete'
        else:
            event_type = 'dicom:reindex'

        file_id = new_row.get('id') if action != 'DELETE' else old_row.get('id')

        data: dict[str, Any] = {'file_id': str(file_id)} if file_id else {}
        if action == 'INSERT':
            data['path'] = new_row.get('name', '')
            data['hash'] = new_row.get('hash', '')
            data['patient_id'] = str(new_row.get('patient_id', ''))
            data['study_id'] = str(new_row.get('study_id', ''))
            data['series_id'] = str(new_row.get('series_id', ''))

        try:
            msg_id = await self._producer.publish(
                self.stream,
                {'event_type': event_type, 'data': data},
            )
            log.debug(
                'bridged %s event for file %s -> %s (msg: %s)',
                action, file_id, self.stream, msg_id,
            )
        except Exception:
            log.exception('failed to publish file event to Redis stream')


__all__ = ['PgNotifyBridge']