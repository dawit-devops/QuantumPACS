import pytest
from services.interfaces import (
    MetadataService, StorageService, ServiceRegistry,
)


class TestServiceRegistry:
    def test_register_and_get(self):
        registry = ServiceRegistry()

        metadata = FakeMetadataService()
        registry.register(MetadataService, metadata)
        result = registry.get(MetadataService)
        assert result is metadata

    def test_get_unregistered_raises(self):
        registry = ServiceRegistry()
        with pytest.raises(KeyError, match='No service registered for'):
            registry.get(MetadataService)

    def test_register_twice_overwrites(self):
        registry = ServiceRegistry()
        first = FakeMetadataService()
        second = FakeMetadataService()
        registry.register(MetadataService, first)
        registry.register(MetadataService, second)
        assert registry.get(MetadataService) is second

    def test_get_or_none_returns_none_for_unregistered(self):
        registry = ServiceRegistry()
        assert registry.get_or_none(MetadataService) is None

    def test_register_multiple_services(self):
        registry = ServiceRegistry()
        meta = FakeMetadataService()
        storage = FakeStorageService()
        registry.register(MetadataService, meta)
        registry.register(StorageService, storage)
        assert registry.get(MetadataService) is meta
        assert registry.get(StorageService) is storage

    def test_reset_clears_all(self):
        registry = ServiceRegistry()
        registry.register(MetadataService, FakeMetadataService())
        registry.reset()
        assert registry.get_or_none(MetadataService) is None


class TestServiceInterfaces:
    def test_metadata_service_interface(self):
        svc = FakeMetadataService()
        assert hasattr(svc, 'get_patient')
        assert hasattr(svc, 'get_study')
        assert hasattr(svc, 'get_series')
        assert hasattr(svc, 'add_file')
        assert hasattr(svc, 'get_file')

    def test_storage_service_interface(self):
        svc = FakeStorageService()
        assert hasattr(svc, 'store')
        assert hasattr(svc, 'fetch')
        assert hasattr(svc, 'delete')
        assert hasattr(svc, 'exists')

    def test_auth_service_interface(self):
        svc = FakeAuthService()
        assert hasattr(svc, 'authenticate')
        assert hasattr(svc, 'verify_token')
        assert hasattr(svc, 'authorize')
        assert hasattr(svc, 'get_user')

    def test_search_service_interface(self):
        svc = FakeSearchService()
        assert hasattr(svc, 'index_file')
        assert hasattr(svc, 'search')
        assert hasattr(svc, 'delete_from_index')

    def test_notification_service_interface(self):
        svc = FakeNotificationService()
        assert hasattr(svc, 'broadcast')
        assert hasattr(svc, 'subscribe')
        assert hasattr(svc, 'unsubscribe')


class FakeMetadataService:
    async def get_patient(self, patient_id):
        return {'id': patient_id}

    async def get_study(self, study_id):
        return {'id': study_id}

    async def get_series(self, series_id):
        return {'id': series_id}

    async def add_file(self, file_data):
        return {'id': 'file_1'}

    async def get_file(self, file_id):
        return {'id': file_id}


class FakeStorageService:
    async def store(self, path, data):
        return True

    async def fetch(self, path):
        return b'data'

    async def delete(self, path):
        return True

    async def exists(self, path):
        return True


class FakeAuthService:
    async def authenticate(self, username, password):
        return {'id': 1, 'role': 'admin'}

    async def verify_token(self, token):
        return {'id': 1, 'role': 'admin'}

    async def authorize(self, user, permission):
        return True

    async def get_user(self, user_id):
        return {'id': user_id}


class FakeSearchService:
    async def index_file(self, file_data):
        return True

    async def search(self, query):
        return {'data': [], 'total': 0}

    async def delete_from_index(self, file_id):
        return True


class FakeNotificationService:
    async def broadcast(self, channel, message):
        return True

    async def subscribe(self, channel, callback):
        return True

    async def unsubscribe(self, channel):
        return True