import json
from typing import Any, Optional

from log import get_logger
from services.interfaces import (
    MetadataService,
    StorageService,
    SearchService,
)

log = get_logger(__name__)

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
        try:
            await handler(data)
            return True
        except Exception:
            log.exception('error processing event %s', event_type)
            return False

    async def _handle_dicom_stored(self, data: dict[str, Any]) -> None:
        file_path = data.get('path', '')
        file_bytes = data.get('bytes', b'')
        log.info('processing stored DICOM: %s', file_path)
        if self.metadata is not None:
            await self.metadata.add_file(data)
        if self.storage is not None:
            await self.storage.store(file_path, file_bytes)
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
            await self.storage.delete(file_id)