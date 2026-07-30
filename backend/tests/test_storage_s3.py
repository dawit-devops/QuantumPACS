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


class FakeResponse:
    def __init__(self, body):
        self._buffer = bytearray(body)

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass

    async def read(self, chunk_size=-1):
        if chunk_size == -1 or chunk_size >= len(self._buffer):
            data = bytes(self._buffer)
            self._buffer.clear()
        else:
            data = bytes(self._buffer[:chunk_size])
            self._buffer = self._buffer[chunk_size:]
        return data


class TestS3Storage:
    @pytest.fixture
    def replica(self):
        return {
            'id': 1, 'type': 's3', 'location': 'eu-central-1',
            'meta': {'access_key_id': 'AKIA-test', 'secret_access_key': 'secret-key'},
        }

    @pytest.fixture
    def mock_client(self):
        client = AsyncMock()
        client.create_bucket = AsyncMock()
        client.put_object = AsyncMock()
        client.get_object = AsyncMock()
        client.delete_object = AsyncMock()
        return client

    @pytest.fixture
    def storage(self, replica, mock_client):
        with patch('storage.s3.aiobotocore.session.get_session') as MockSession:
            session = MagicMock()
            session.create_client = AsyncMock(return_value=mock_client)
            MockSession.return_value = session
            from storage.s3 import S3Storage
            s = S3Storage(replica)
            s._client = mock_client
            yield s

    def test_name(self):
        from storage.s3 import S3Storage
        assert S3Storage.name == 's3'

    def test_get_key(self, storage):
        key = storage.get_key({
            'patient_id': '100', 'study_id': '200', 'series_number': '300', 'name': 'image.dcm',
        })
        assert key == '100/200/300/image.dcm'

    def test_get_key_empty_parts(self, storage):
        key = storage.get_key({
            'patient_id': '100', 'study_id': '', 'series_number': '', 'name': 'image.dcm',
        })
        assert key == '100/empty/empty/image.dcm'

    async def test_init_creates_bucket(self, storage, mock_client):
        await storage.init()
        mock_client.create_bucket.assert_called_once_with(
            Bucket='quantumpacs',
            CreateBucketConfiguration={'LocationConstraint': 'eu-central-1'},
        )

    async def test_init_ignores_bucket_owned(self, storage, mock_client):
        from botocore.exceptions import ClientError
        mock_client.create_bucket = AsyncMock(side_effect=ClientError(
            {'Error': {'Code': 'BucketAlreadyOwnedByYou', 'Message': 'Bucket already owned'}},
            'CreateBucket',
        ))
        await storage.init()

    async def test_init_raises_other_errors(self, storage, mock_client):
        mock_client.create_bucket = AsyncMock(side_effect=Exception('network failure'))
        with pytest.raises(Exception, match='network failure'):
            await storage.init()

    async def test_copy_from_local_file(self, storage, mock_client):
        with patch('builtins.open', MagicMock()) as mock_open:
            mock_open.return_value.__enter__.return_value.read.return_value = b'dicom data'
            result = await storage.copy('/tmp/src.dcm', {
                'patient_id': '1', 'study_id': '2', 'series_number': '3', 'name': 'img.dcm',
            })

        assert result['location'] == '1/2/3/img.dcm'
        mock_client.put_object.assert_called_once()

    async def test_copy_from_bytesio(self, storage, mock_client):
        from io import BytesIO
        buf = BytesIO(b'inline dicom data')
        result = await storage.copy(buf, {
            'patient_id': '1', 'study_id': '', 'series_number': '', 'name': 'img.dcm',
        })

        assert result['location'] == '1/empty/empty/img.dcm'
        mock_client.put_object.assert_called_once()
        args = mock_client.put_object.call_args
        assert args[1]['Key'] == '1/empty/empty/img.dcm'

    async def test_fetch_returns_temp_file(self, storage, mock_client):
        mock_client.get_object = AsyncMock(return_value={'Body': FakeResponse(b'dicom data')})

        with patch('storage.s3.tempfile.NamedTemporaryFile') as MockTmp:
            tmp = MagicMock()
            tmp.write = MagicMock()
            tmp.flush = MagicMock()
            tmp.seek = MagicMock()
            MockTmp.return_value = tmp
            result = await storage.fetch({
                'patient_id': '1', 'study_id': '2', 'series_number': '3', 'name': 'img.dcm',
            })

        assert result == tmp
        tmp.write.assert_called_with(b'dicom data')
        tmp.flush.assert_called_once()
        tmp.seek.assert_called_once_with(0)

    async def test_fetch_large_file_chunks(self, storage, mock_client):
        chunk1 = b'a' * 65536
        chunk2 = b'b' * 100
        mock_client.get_object = AsyncMock(return_value={'Body': FakeResponse(chunk1 + chunk2)})

        with patch('storage.s3.tempfile.NamedTemporaryFile') as MockTmp:
            tmp = MagicMock()
            tmp.write = MagicMock()
            tmp.flush = MagicMock()
            tmp.seek = MagicMock()
            MockTmp.return_value = tmp
            result = await storage.fetch({'patient_id': '1', 'study_id': '2', 'series_number': '3', 'name': 'large.dcm'})

        assert tmp.write.call_count == 2

    async def test_delete(self, storage, mock_client):
        await storage.delete({
            'patient_id': '1', 'study_id': '2', 'series_number': '3', 'name': 'img.dcm',
        })
        mock_client.delete_object.assert_called_once_with(Bucket='quantumpacs', Key='1/2/3/img.dcm')

    async def test_serve_generates_presigned_url(self, storage, mock_client):
        mock_client.generate_presigned_url = AsyncMock(return_value='https://s3.amazonaws.com/bucket/key?presigned')
        result = await storage.serve({'location': '1/2/3/img.dcm'})
        assert result.status_code == 307
        assert 'https://s3.amazonaws.com' in str(result.headers.get('location'))
