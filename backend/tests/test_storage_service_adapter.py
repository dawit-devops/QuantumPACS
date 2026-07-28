import os
import pytest
from unittest.mock import AsyncMock, MagicMock

from services.storage.local_storage_adapter import StorageServiceAdapter
from services.interfaces import StorageService


class TestStorageServiceAdapter:
    @pytest.fixture
    def storage(self):
        s = AsyncMock()
        s.copy = AsyncMock(return_value={'location': '/tmp/test.dcm'})
        s.fetch = AsyncMock(return_value='/tmp/test.dcm')
        s.delete = AsyncMock()
        return s

    @pytest.fixture
    def svc(self, storage):
        return StorageServiceAdapter(storage)

    def test_is_storage_service(self, svc):
        assert hasattr(svc, 'store')
        assert hasattr(svc, 'fetch')
        assert hasattr(svc, 'delete')
        assert hasattr(svc, 'exists')

    async def test_store_calls_underlying_copy(self, svc, storage, tmp_path):
        data = b'some dicom data'
        result = await svc.store({'name': 'test.dcm'}, data)
        assert result is True
        storage.copy.assert_called_once()
        args = storage.copy.call_args
        assert args[0][1] == {'name': 'test.dcm'}

    async def test_fetch_returns_none_when_not_exists(self, svc, storage):
        storage.fetch = AsyncMock(return_value=None)
        result = await svc.fetch({'name': 'missing.dcm'})
        assert result is None

    async def test_fetch_returns_bytes(self, svc, storage, tmp_path):
        path = tmp_path / 'test.dcm'
        path.write_bytes(b'file content')
        storage.fetch = AsyncMock(return_value=str(path))
        result = await svc.fetch({'name': 'test.dcm'})
        assert result == b'file content'

    async def test_delete_calls_underlying_delete(self, svc, storage):
        result = await svc.delete({'name': 'test.dcm'})
        assert result is True
        storage.delete.assert_called_once()

    async def test_delete_returns_false_on_exception(self, svc, storage):
        storage.delete = AsyncMock(side_effect=FileNotFoundError)
        result = await svc.delete({'name': 'missing.dcm'})
        assert result is False

    async def test_exists_returns_false_when_path_is_none(self, svc, storage):
        storage.fetch = AsyncMock(return_value=None)
        result = await svc.exists({'name': 'missing.dcm'})
        assert result is False

    async def test_exists_returns_true_when_file_exists(self, svc, storage, tmp_path):
        path = tmp_path / 'test.dcm'
        path.write_bytes(b'x')
        storage.fetch = AsyncMock(return_value=str(path))
        result = await svc.exists({'name': 'test.dcm'})
        assert result is True

    async def test_exists_returns_false_when_path_does_not_exist(self, svc, storage):
        storage.fetch = AsyncMock(return_value='/nonexistent/path.dcm')
        result = await svc.exists({'name': 'test.dcm'})
        assert result is False
