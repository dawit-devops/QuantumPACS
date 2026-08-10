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
        tenant_conns: Optional[list[tuple[str, Callable[[], Awaitable[Any]]]]] = None,
    ):
        """Bridges PostgreSQL NOTIFY events to the Redis ingestion stream.

        tenant_conns: `(slug, create_conn)` pairs for per-tenant databases.
        Tenant DBs run the same schema (incl. the notify_event trigger), so
        their file writes must be bridged too (HI-04). Each listener tags
        events with the tenant slug so downstream consumers can scope their
        work (e.g. per-tenant ES indexes).
        """
        self.redis = redis
        self._create_conn = create_conn
        self.stream = stream
        self.group = group
        self.tenant_conns = tenant_conns or []
        self._conn: Optional[Any] = None
        self._tenant_listeners: list[tuple[str, Any]] = []
        self._producer: Optional[StreamProducer] = None
        self._task: Optional[asyncio.Task] = None
        self._shutdown = asyncio.Event()
        self._extra_handlers: list[OnNotification] = []
        self._pending_tasks: set[asyncio.Task] = set()

    def add_handler(self, handler: OnNotification) -> None:
        self._extra_handlers.append(handler)

    async def start(self) -> None:
        self._producer = StreamProducer(self.redis)
        await self._producer.ensure_group(self.stream, self.group)
        self._conn = await self._create_conn()
        await self._conn.add_listener(EVENTS_CHANNEL, self._on_notification)
        for slug, factory in self.tenant_conns:
            # A failing tenant listener must not take the bridge down: log
            # and continue with the remaining tenants (HI-04).
            try:
                conn = await factory()
            except Exception:
                log.warning('tenant notify listener %s failed to connect', slug, exc_info=True)
                continue
            try:
                await conn.add_listener(EVENTS_CHANNEL, self._listener_for(slug))
                self._tenant_listeners.append((slug, conn))
                log.info('tenant notify listener started for %s', slug)
            except Exception:
                log.warning('tenant notify listener %s failed to attach', slug, exc_info=True)
                try:
                    await conn.close()
                except Exception:
                    pass
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
        if self._pending_tasks:
            await asyncio.gather(*self._pending_tasks, return_exceptions=True)
            self._pending_tasks.clear()
        for _slug, conn in self._tenant_listeners:
            try:
                await conn.close()
            except Exception:
                pass
        self._tenant_listeners = []
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

    def _listener_for(self, tenant_slug: str) -> OnNotification:
        def listener(conn: Any, pid: int, channel: str, payload: str) -> None:
            self._on_notification(conn, pid, channel, payload, tenant_slug=tenant_slug)
        return listener

    def _on_notification(
        self, conn: Any, pid: int, channel: str, payload: str, tenant_slug: Optional[str] = None,
    ) -> None:
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
            task = asyncio.create_task(self._publish_file_event(action, new_row, old_row, tenant_slug))
            self._pending_tasks.add(task)
            task.add_done_callback(self._pending_tasks.discard)

        for handler in self._extra_handlers:
            task = asyncio.create_task(handler(data))
            self._pending_tasks.add(task)
            task.add_done_callback(self._pending_tasks.discard)

    async def _publish_file_event(
        self, action: str, new_row: dict[str, Any], old_row: dict[str, Any],
        tenant_slug: Optional[str] = None,
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
        if tenant_slug:
            # Lets consumers scope the work to the tenant's store/index
            # (e.g. CR-01: search indexing must not land in the wrong
            # tenant's namespace).
            data['tenant'] = tenant_slug

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