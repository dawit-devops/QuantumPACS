from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from storage.storage import Storage


@pytest.fixture(autouse=True)
def _reset_storage_registry():
    saved = dict(Storage.storage_types)
    Storage.storages.clear()
    Storage._init_locks.clear()
    yield
    Storage.storages.clear()
    Storage._init_locks.clear()
    Storage.storage_types.update(saved)


class TestB2Storage:
    @pytest.fixture
    def replica(self):
        return {'id': 1, 'type': 'b2', 'location': 'us-west-001', 'meta': {'app_key_id': 'test-key-id', 'app_key': 'test-app-key'}}

    @pytest.fixture
    def storage(self, replica):
        with patch('storage.b2.B2Api'):
            from storage.b2 import B2Storage
            s = B2Storage(replica)
            s.api = MagicMock()
            s.api.authorize_account = MagicMock()
            yield s

    def test_name(self):
        from storage.b2 import B2Storage
        assert B2Storage.name == 'b2'

    def test_get_path(self, storage):
        path = storage.get_path({
            'patient_id': '100',
            'study_id': '200',
            'series_number': '300',
            'name': 'image.dcm',
        })
        assert path == '100/200/300/image.dcm'

    def test_get_path_empty_parts(self, storage):
        path = storage.get_path({
            'patient_id': '100',
            'study_id': '',
            'series_number': '',
            'name': 'image.dcm',
        })
        assert path == '100/empty/empty/image.dcm'

    async def test_copy_upload_local_file(self, storage):
        mock_bucket = MagicMock()
        mock_bucket.upload_local_file = MagicMock(return_value=MagicMock(id_='file-abc'))
        storage.api.get_bucket_by_name = MagicMock(return_value=mock_bucket)

        result = await storage.copy('/tmp/src.dcm', {
            'patient_id': '1', 'study_id': '2', 'series_number': '3', 'name': 'img.dcm', 'hash': 'abc123',
        })

        assert result['location'] == '1/2/3/img.dcm'
        assert result['meta']['id'] == 'file-abc'
        mock_bucket.upload_local_file.assert_called_once_with(
            local_file='/tmp/src.dcm', file_name='1/2/3/img.dcm', file_infos={'hash': 'abc123'},
        )

    async def test_copy_upload_bytes(self, storage):
        from io import BytesIO
        mock_bucket = MagicMock()
        mock_bucket.upload_bytes = MagicMock(return_value=MagicMock(id_='file-xyz'))
        storage.api.get_bucket_by_name = MagicMock(return_value=mock_bucket)

        buf = BytesIO(b'dicom data')
        result = await storage.copy(buf, {
            'patient_id': '1', 'study_id': '', 'series_number': '', 'name': 'img.dcm', 'hash': 'def456',
        })

        assert result['location'] == '1/empty/empty/img.dcm'
        mock_bucket.upload_bytes.assert_called_once()
        called_args = mock_bucket.upload_bytes.call_args
        assert called_args[1]['file_name'] == '1/empty/empty/img.dcm'

    async def test_fetch_returns_temporary_file(self, storage):
        mock_bucket = MagicMock()
        downloaded = MagicMock()
        downloaded.save = MagicMock()
        tmp = MagicMock()
        tmp.flush = MagicMock()
        tmp.seek = MagicMock()
        mock_bucket.download_file_by_name = MagicMock(return_value=downloaded)
        storage.api.get_bucket_by_name = MagicMock(return_value=mock_bucket)

        with patch('storage.b2.tempfile.NamedTemporaryFile', return_value=tmp):
            result = await storage.fetch({
                'patient_id': '1', 'study_id': '2', 'series_number': '3', 'name': 'img.dcm',
            })

        assert result == tmp
        tmp.flush.assert_called_once()
        tmp.seek.assert_called_once_with(0)

    async def test_delete(self, storage):
        mock_bucket = MagicMock()
        storage.api.get_bucket_by_name = MagicMock(return_value=mock_bucket)
        storage.api.delete_file_version = MagicMock()

        await storage.delete({
            'patient_id': '1', 'study_id': '2', 'series_number': '3', 'name': 'img.dcm',
            'replica_meta': {'id': 'b2-file-id'},
        })

        storage.api.delete_file_version.assert_called_once_with('b2-file-id', '1/2/3/img.dcm')

    async def test_send_state_redirect_on_success(self, storage):
        mock_bucket = MagicMock()
        mock_bucket.get_download_url = MagicMock(return_value='https://download.b2.com/file')
        mock_bucket.get_download_authorization = MagicMock(return_value='auth-token')
        storage.api.get_bucket_by_name = MagicMock(return_value=mock_bucket)

        result = await storage.serve({'location': '1/2/3/img.dcm'})

        assert result.status_code == 307
        assert 'https://download.b2.com/file' in str(result.headers.get('location'))

    async def test_send_state_streaming_on_auth_failure(self, storage):
        mock_bucket = MagicMock()
        mock_bucket.get_download_url = MagicMock(return_value='https://download.b2.com/file')
        mock_bucket.get_download_authorization = MagicMock(side_effect=Exception('auth failed'))
        storage.api.get_bucket_by_name = MagicMock(return_value=mock_bucket)
        storage.fetch = AsyncMock(return_value=MagicMock())

        result = await storage.serve({'location': '1/2/3/img.dcm'})

        assert result.status_code == 200
        storage.fetch.assert_called_once()

    async def test_init_authorizes_and_creates_bucket(self, storage):
        storage.api.authorize_account = MagicMock()
        storage.api.create_bucket = MagicMock()

        await storage.init()

        storage.api.authorize_account.assert_called_once_with('production', 'test-key-id', 'test-app-key')
        storage.api.create_bucket.assert_called_once()

    async def test_init_ignores_bucket_exists(self, storage):
        storage.api.authorize_account = MagicMock()
        storage.api.create_bucket = MagicMock(side_effect=Exception('Bucket name is already in use'))

        await storage.init()

        storage.api.create_bucket.assert_called_once()

    async def test_init_raises_on_unexpected_error(self, storage):
        storage.api.authorize_account = MagicMock()
        storage.api.create_bucket = MagicMock(side_effect=Exception('network error'))

        with pytest.raises(Exception, match='network error'):
            await storage.init()
