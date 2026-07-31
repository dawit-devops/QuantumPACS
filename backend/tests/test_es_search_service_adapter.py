import pytest
from unittest.mock import AsyncMock

from services.search.es_search_adapter import EsSearchServiceAdapter


class TestEsSearchServiceAdapter:
    @pytest.fixture
    def es_module(self):
        m = AsyncMock()
        m.index_file = AsyncMock()
        m.search = AsyncMock(return_value={'data': [], 'total': 0})
        m.delete = AsyncMock()
        return m

    @pytest.fixture
    def svc(self, es_module):
        return EsSearchServiceAdapter(es_module=es_module)

    def test_is_search_service(self, svc):
        assert hasattr(svc, 'index_file')
        assert hasattr(svc, 'search')
        assert hasattr(svc, 'delete_from_index')

    async def test_index_file_calls_underlying(self, svc, es_module):
        result = await svc.index_file({'id': 1, 'meta': {}})
        assert result is True
        es_module.index_file.assert_called_once_with({'id': 1, 'meta': {}})

    async def test_index_file_returns_false_on_error(self, svc, es_module):
        es_module.index_file = AsyncMock(side_effect=ConnectionError)
        result = await svc.index_file({'id': 1})
        assert result is False

    async def test_search_returns_underlying_result(self, svc, es_module):
        expected = {'data': [{'id': 1}], 'total': 1}
        es_module.search = AsyncMock(return_value=expected)
        result = await svc.search({'query': 'chest'})
        assert result == expected

    async def test_delete_from_index_calls_underlying(self, svc, es_module):
        result = await svc.delete_from_index('123')
        assert result is True
        es_module.delete.assert_called_once_with('123')

    async def test_delete_from_index_returns_false_on_error(self, svc, es_module):
        es_module.delete = AsyncMock(side_effect=Exception('not found'))
        result = await svc.delete_from_index('123')
        assert result is False
