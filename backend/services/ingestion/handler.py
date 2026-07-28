import json
from typing import Any, Optional

from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode

from log import get_logger
from services.interfaces import (
    MetadataService,
    StorageService,
    SearchService,
)

log = get_logger(__name__)
_tracer = trace.get_tracer('quantumpacs.ingestion')

EVENT_DICOM_STORED = 'dicom:stored'
EVENT_DICOM_REINDEX = 'dicom:reindex'
EVENT_DICOM_DELETE = 'dicom:delete'

SUPPORTED_EVENTS = {EVENT_DICOM_STORED, EVENT_DICOM_REINDEX, EVENT_DICOM_DELETE}


class IngestionHandler:
    def __init__(
        self,
        metadata: Optional[MetadataService] = None,
        storage: Optional[StorageService] = None,
        search: Optional[SearchService] = None,
    ):
        self.metadata = metadata
        self.storage = storage
        self.search = search

    async def handle(self, event_type: str, data: dict[str, Any]) -> bool:
        handler_name = f'_handle_{event_type.replace(":", "_")}'
        handler = getattr(self, handler_name, None)
        if handler is None:
            log.warning('unknown event type: %s', event_type)
            return False
        with _tracer.start_as_current_span(f'ingest.{event_type}') as span:
            span.set_attribute('messaging.event_type', event_type)
            try:
                await handler(data)
                span.set_status(Status(StatusCode.OK))
                return True
            except Exception as exc:
                span.record_exception(exc)
                span.set_status(Status(StatusCode.ERROR))
                log.exception('error processing event %s', event_type)
                return False

    async def _handle_dicom_stored(self, data: dict[str, Any]) -> None:
        file_path = data.get('path', '')
        file_bytes = data.get('bytes', b'')
        log.info('processing stored DICOM: %s', file_path)
        if self.metadata is not None:
            await self.metadata.add_file(data)
        if self.storage is not None:
            await self.storage.store(data, file_bytes)
        if self.search is not None:
            await self.search.index_file(data)

    async def _handle_dicom_reindex(self, data: dict[str, Any]) -> None:
        file_id = data.get('file_id', '')
        log.info('reindexing file: %s', file_id)
        if self.search is not None:
            await self.search.index_file(data)

    async def _handle_dicom_delete(self, data: dict[str, Any]) -> None:
        file_id = data.get('file_id', '')
        log.info('deleting file: %s', file_id)
        if self.search is not None:
            await self.search.delete_from_index(file_id)
        if self.storage is not None:
            await self.storage.delete(data)