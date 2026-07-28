from typing import Any

from es import es as es_mod
from services.interfaces import SearchService


class EsSearchServiceAdapter(SearchService):
    def __init__(self, es_module=es_mod):
        self._es = es_module

    async def index_file(self, file_data: dict[str, Any]) -> bool:
        try:
            await self._es.index_file(file_data)
            return True
        except Exception:
            return False

    async def search(self, query: dict[str, Any]) -> dict[str, Any]:
        return await self._es.search(query)

    async def delete_from_index(self, file_id: str) -> bool:
        try:
            await self._es.delete(file_id)
            return True
        except Exception:
            return False
