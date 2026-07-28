import os
import tempfile
from typing import Any, Optional

from services.interfaces import StorageService
from storage.storage import Storage


class StorageServiceAdapter(StorageService):
    def __init__(self, storage: Storage):
        self._storage = storage

    async def store(self, file_data: dict[str, Any], data: bytes) -> bool:
        with tempfile.NamedTemporaryFile(delete=False, suffix='.dcm') as tmp:
            tmp.write(data)
            tmp_path = tmp.name
        try:
            await self._storage.copy(tmp_path, file_data)
            return True
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    async def fetch(self, file_data: dict[str, Any]) -> Optional[bytes]:
        path = await self._storage.fetch(file_data)
        if path is None or not os.path.isfile(path):
            return None
        with open(path, 'rb') as f:
            return f.read()

    async def delete(self, file_data: dict[str, Any]) -> bool:
        try:
            await self._storage.delete(file_data)
            return True
        except Exception:
            return False

    async def exists(self, file_data: dict[str, Any]) -> bool:
        path = await self._storage.fetch(file_data)
        if path is None:
            return False
        return os.path.isfile(path)
