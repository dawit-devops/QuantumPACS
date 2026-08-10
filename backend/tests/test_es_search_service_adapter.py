import pytest
from unittest.mock import AsyncMock, patch

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
        es_module.index_file.assert_called_once_with({'id': 1, 'meta': {}}, tenant_slug='')

    async def test_index_file_returns_false_on_error(self, svc, es_module):
        es_module.index_file = AsyncMock(side_effect=ConnectionError)
        result = await svc.index_file({'id': 1})
        assert result is False

    async def test_index_file_passes_tenant_slug(self, svc, es_module):
        result = await svc.index_file({'id': 2}, tenant_slug='acme')
        assert result is True
        es_module.index_file.assert_called_once_with({'id': 2}, tenant_slug='acme')

    async def test_search_returns_underlying_result(self, svc, es_module):
        expected = {'data': [{'id': 1}], 'total': 1}
        es_module.search = AsyncMock(return_value=expected)
        result = await svc.search({'query': 'chest'})
        assert result == expected

    async def test_delete_from_index_calls_underlying(self, svc, es_module):
        result = await svc.delete_from_index('123')
        assert result is True
        es_module.delete.assert_called_once_with('123', tenant_slug='')

    async def test_delete_from_index_returns_false_on_error(self, svc, es_module):
        es_module.delete = AsyncMock(side_effect=Exception('not found'))
        result = await svc.delete_from_index('123')
        assert result is False


class TestEsModuleTenantScoping:
    """CR-1: the ES module derives composite _ids and tenant term filters so
    the shared index never mixes tenants' documents."""

    def test_doc_id_is_composite_when_tenant(self):
        from es import es as es_mod
        assert es_mod._doc_id(5, 'acme') == 'acme:5'
        assert es_mod._doc_id(5, '') == '5'
        assert es_mod._doc_id(5) == '5'

    @pytest.mark.asyncio
    async def test_index_file_stamps_tenant_and_composite_id(self):
        from es import es as es_mod
        client = AsyncMock()
        client.index = AsyncMock()
        with patch('es.es.get_client', return_value=client):
            await es_mod.index_file(
                {'id': 5, 'patient_db_id': 2, 'study_db_id': 3,
                 'series_db_id': 4, 'meta': {'PatientID': 'P1'}},
                tenant_slug='acme')
        client.index.assert_awaited_once()
        kwargs = client.index.await_args.kwargs
        assert kwargs['id'] == 'acme:5'
        assert kwargs['document']['tenant'] == 'acme'
        assert kwargs['document']['PatientID'] == 'P1'

    @pytest.mark.asyncio
    async def test_index_file_bare_id_without_tenant(self):
        from es import es as es_mod
        client = AsyncMock()
        client.index = AsyncMock()
        with patch('es.es.get_client', return_value=client):
            await es_mod.index_file(
                {'id': 5, 'patient_db_id': 2, 'study_db_id': 3,
                 'series_db_id': 4, 'meta': {}})
        kwargs = client.index.await_args.kwargs
        assert kwargs['id'] == '5'
        assert 'tenant' not in kwargs['document']

    @pytest.mark.asyncio
    async def test_search_filters_by_tenant_when_slug(self):
        from es import es as es_mod
        client = AsyncMock()
        client.search = AsyncMock(return_value={
            'hits': {'total': {'value': 0}, 'hits': []}})
        with patch('es.es.get_client', return_value=client):
            await es_mod.search({'query': 'CT', 'results': 10, 'page': 1},
                                tenant_slug='acme')
        query = client.search.await_args.kwargs['query']
        assert query['bool']['filter'] == [
            {'term': {'tenant': 'acme'}}]

    @pytest.mark.asyncio
    async def test_search_has_no_tenant_filter_without_slug(self):
        from es import es as es_mod
        client = AsyncMock()
        client.search = AsyncMock(return_value={
            'hits': {'total': {'value': 0}, 'hits': []}})
        with patch('es.es.get_client', return_value=client):
            await es_mod.search({'query': 'CT', 'results': 10, 'page': 1})
        query = client.search.await_args.kwargs['query']
        assert 'bool' not in query
        assert 'filter' not in query
