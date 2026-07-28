import pytest
from unittest.mock import AsyncMock

from services.ingestion.handler import IngestionHandler, EVENT_DICOM_STORED


class FakeMetadata:
    def __init__(self):
        self.added = []
    async def add_file(self, data):
        self.added.append(data)
        return {'id': 'f1'}
    async def get_patient(self, pid): return None
    async def get_study(self, sid): return None
    async def get_series(self, sid): return None
    async def get_file(self, fid): return None
    async def search_studies(self, q): return {'data': [], 'total': 0}


class FakeStorage:
    def __init__(self):
        self.stored = []
    async def store(self, file_data, data):
        self.stored.append((file_data, data))
        return True
    async def fetch(self, file_data): return None
    async def delete(self, file_data): return True
    async def exists(self, file_data): return True


class FakeSearch:
    def __init__(self):
        self.indexed = []
    async def index_file(self, data):
        self.indexed.append(data)
        return True
    async def search(self, q): return {'data': [], 'total': 0}
    async def delete_from_index(self, fid): return True


class TestIngestionPipelineWiring:
    async def test_handler_routes_stored_event_to_all_three_services(self):
        meta = FakeMetadata()
        storage = FakeStorage()
        search = FakeSearch()
        handler = IngestionHandler(metadata=meta, storage=storage, search=search)

        data = {'path': '/tmp/test.dcm', 'bytes': b'pixel', 'patient_id': 'P1'}
        success = await handler.handle(EVENT_DICOM_STORED, data)

        assert success is True
        assert meta.added == [data]
        assert storage.stored == [(data, b'pixel')]
        assert search.indexed == [data]

    async def test_handler_invokes_registered_metadata(self):
        meta = FakeMetadata()
        handler = IngestionHandler(metadata=meta)
        data = {'path': 'x.dcm', 'patient_id': 'P1'}
        success = await handler.handle(EVENT_DICOM_STORED, data)
        assert success is True
        assert meta.added == [data]

    async def test_handler_invokes_registered_storage(self):
        storage = FakeStorage()
        handler = IngestionHandler(storage=storage)
        data = {'path': 'x.dcm', 'name': 'x.dcm'}
        success = await handler.handle(EVENT_DICOM_STORED, data)
        assert success is True
        assert len(storage.stored) == 1

    async def test_handler_invokes_registered_search(self):
        search = FakeSearch()
        handler = IngestionHandler(search=search)
        data = {'path': 'x.dcm', 'patient_id': 'P1'}
        success = await handler.handle(EVENT_DICOM_STORED, data)
        assert success is True
        assert search.indexed == [data]

    async def test_lifecycle_accepts_services_parameter(self):
        import inspect
        from lifecycle import setup
        sig = inspect.signature(setup)
        assert 'services' in sig.parameters

    async def test_lifecycle_runs_without_services_when_redis_unavailable(self):
        import lifecycle
        from unittest.mock import MagicMock

        monkey = pytest.MonkeyPatch()
        try:
            monkey.setattr(
                'lifecycle.db.conn.setup', AsyncMock(),
            )
            monkey.setattr(
                'lifecycle.es.setup', AsyncMock(),
            )
            monkey.setattr(
                'lifecycle._get_redis_for_test', AsyncMock(return_value=None),
                raising=False,
            )
            monkey.setattr(
                'lifecycle.redis_available', lambda: False,
            )
            monkey.setattr('lifecycle._start_dicom', lambda: None)
            monkey.setattr('lifecycle._start_mllp', AsyncMock())

            class FakeRegistry:
                def get_or_none(self, key):
                    return None

            await lifecycle.setup(services=FakeRegistry())
        finally:
            monkey.undo()
