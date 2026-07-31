
from services.ingestion.handler import (
    IngestionHandler,
    EVENT_DICOM_STORED,
    EVENT_DICOM_REINDEX,
    EVENT_DICOM_DELETE,
)


class FakeMetadataService:
    def __init__(self):
        self.added = []
        self.searched = []

    async def get_patient(self, patient_id): return None
    async def get_study(self, study_id): return None
    async def get_series(self, series_id): return None
    async def add_file(self, file_data):
        self.added.append(file_data)
        return {'id': 'f1'}
    async def get_file(self, file_id): return None
    async def search_studies(self, query):
        self.searched.append(query)
        return {'data': [], 'total': 0}


class FakeStorageService:
    def __init__(self):
        self.stored = []
        self.deleted = []

    async def store(self, file_data, data):
        self.stored.append((file_data, data))
        return True
    async def fetch(self, file_data): return None
    async def delete(self, file_data):
        self.deleted.append(file_data)
        return True
    async def exists(self, file_data): return True


class FakeSearchService:
    def __init__(self):
        self.indexed = []
        self.deleted_ids = []

    async def index_file(self, file_data):
        self.indexed.append(file_data)
        return True
    async def search(self, query): return {'data': [], 'total': 0}
    async def delete_from_index(self, file_id):
        self.deleted_ids.append(file_id)
        return True



class TestIngestionHandler:
    async def test_unknown_event_returns_false(self):
        handler = IngestionHandler()
        success = await handler.handle('unknown:event', {})
        assert success is False

    async def test_dicom_stored_calls_all_services(self):
        meta = FakeMetadataService()
        storage = FakeStorageService()
        search = FakeSearchService()
        handler = IngestionHandler(metadata=meta, storage=storage, search=search)

        data = {'path': '/tmp/test.dcm', 'bytes': b'pixel', 'patient_id': 'P1'}
        success = await handler.handle(EVENT_DICOM_STORED, data)
        assert success is True
        assert len(meta.added) == 1
        assert meta.added[0] == data
        assert len(storage.stored) == 1
        assert storage.stored[0] == (data, b'pixel')
        assert len(search.indexed) == 1
        assert search.indexed[0] == data

    async def test_dicom_stored_works_without_optional_services(self):
        handler = IngestionHandler(metadata=FakeMetadataService())
        success = await handler.handle(EVENT_DICOM_STORED, {'path': 'test.dcm'})
        assert success is True

    async def test_dicom_reindex_calls_search_only(self):
        search = FakeSearchService()
        handler = IngestionHandler(search=search)
        data = {'file_id': 'f123'}
        success = await handler.handle(EVENT_DICOM_REINDEX, data)
        assert success is True
        assert len(search.indexed) == 1
        assert len(search.deleted_ids) == 0

    async def test_dicom_delete_calls_search_and_storage(self):
        storage = FakeStorageService()
        search = FakeSearchService()
        handler = IngestionHandler(storage=storage, search=search)
        data = {'file_id': 'f999'}
        success = await handler.handle(EVENT_DICOM_DELETE, data)
        assert success is True
        assert search.deleted_ids == ['f999']
        assert storage.deleted == [{'file_id': 'f999'}]

    async def test_handler_logs_and_returns_false_on_error(self, caplog):
        class BrokenMeta:
            async def add_file(self, data):
                raise RuntimeError('db connection lost')
            async def get_patient(self, pid): return None
            async def get_study(self, sid): return None
            async def get_series(self, sid): return None
            async def get_file(self, fid): return None
            async def search_studies(self, q): return {'data': [], 'total': 0}

        handler = IngestionHandler(metadata=BrokenMeta())
        success = await handler.handle(EVENT_DICOM_STORED, {'path': 'test.dcm'})
        assert success is False
        assert 'error processing event' in caplog.text