from typing import Any

from es import es as es_mod
from services.interfaces import SearchService


class EsSearchServiceAdapter(SearchService):
    def __init__(self, es_module=es_mod):
        self._es = es_module

    async def index_file(self, file_data: dict[str, Any], tenant_slug: str = '') -> bool:
        try:
            await self._es.index_file(file_data, tenant_slug=tenant_slug)
            return True
        except Exception:
            return False

    async def search(self, query: dict[str, Any], tenant_slug: str = '') -> dict[str, Any]:
        # CR-01: a tenant-scoped search must filter on the tenant keyword —
        # the shared index holds every tenant's documents. '' (main scope)
        # keeps the historical unfiltered behaviour.
        return await self._es.search(query, tenant_slug=tenant_slug)

    async def delete_from_index(self, file_id: str, tenant_slug: str = '') -> bool:
        try:
            await self._es.delete(file_id, tenant_slug=tenant_slug)
            return True
        except Exception:
            return False
