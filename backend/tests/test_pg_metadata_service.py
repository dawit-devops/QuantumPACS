import pytest
from unittest.mock import AsyncMock

from services.interfaces import MetadataService
from services.metadata.pg_metadata import PgMetadataService


class FakeRecord(dict):
    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError:
            raise AttributeError(key)


class TestPgMetadataService:
    @pytest.fixture
    def conn(self):
        return AsyncMock()

    @pytest.fixture
    def conn_cm(self, conn):
        cm = AsyncMock()
        cm.__aenter__.return_value = conn
        return cm

    @pytest.fixture
    def svc(self, conn_cm):
        return PgMetadataService(conn_provider=lambda: conn_cm)

    def test_is_metadata_service(self, svc):
        assert hasattr(svc, 'get_patient')
        assert hasattr(svc, 'get_study')
        assert hasattr(svc, 'get_series')
        assert hasattr(svc, 'add_file')
        assert hasattr(svc, 'get_file')
        assert hasattr(svc, 'search_studies')

    async def test_get_patient_returns_none_when_not_found(self, svc, conn):
        conn.fetchrow.return_value = None
        result = await svc.get_patient('999')
        assert result is None

    async def test_get_patient_returns_patient_data(self, svc, conn):
        conn.fetchrow.return_value = FakeRecord(
            {'id': 1, 'patient_id': 'P001', 'name': 'Test^Patient'}
        )
        result = await svc.get_patient('P001')
        assert result is not None
        assert result['patient_id'] == 'P001'

    async def test_get_study_returns_none_when_not_found(self, svc, conn):
        conn.fetchrow.return_value = None
        result = await svc.get_study('UNKNOWN')
        assert result is None

    async def test_get_study_returns_study(self, svc, conn):
        conn.fetchrow.return_value = FakeRecord(
            {'id': 10, 'study_id': 'S001', 'description': 'CT CHEST'}
        )
        result = await svc.get_study('S001')
        assert result is not None
        assert result['study_id'] == 'S001'

    async def test_get_series_returns_none_when_not_found(self, svc, conn):
        conn.fetchrow.return_value = None
        result = await svc.get_series('UNKNOWN')
        assert result is None

    async def test_get_series_returns_series(self, svc, conn):
        conn.fetchrow.return_value = FakeRecord(
            {'id': 100, 'number': '1', 'modality': 'CT'}
        )
        result = await svc.get_series('1')
        assert result is not None
        assert result['number'] == '1'

    async def test_add_file_uses_insert(self, svc, conn):
        conn.fetchrow.return_value = FakeRecord({'id': 42})
        result = await svc.add_file({'name': 'IM0001.dcm', 'patient_id': 1})
        assert result == {'id': 42}

    async def test_get_file_returns_none_when_not_found(self, svc, conn):
        conn.fetchrow.return_value = None
        result = await svc.get_file('999')
        assert result is None

    async def test_get_file_returns_file(self, svc, conn):
        conn.fetchrow.return_value = FakeRecord(
            {'id': 1, 'name': 'IM0001.dcm', 'patient_id': 1}
        )
        result = await svc.get_file('1')
        assert result is not None
        assert result['id'] == 1

    async def test_search_studies_returns_results(self, svc, conn):
        conn.fetch.return_value = [
            FakeRecord({'id': 10, 'study_id': 'S001', 'description': 'CT CHEST'})
        ]
        result = await svc.search_studies({'query': 'chest', 'results': 10, 'page': 1})
        assert 'data' in result
        assert 'total' in result
