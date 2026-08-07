from io import BytesIO
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydicom.dataset import Dataset, FileDataset, FileMetaDataset


class _AsyncFileMock:
    def __init__(self, data):
        self._data = data
        self._offset = 0

    async def read(self, n=-1):
        if self._offset >= len(self._data):
            return b''
        chunk = self._data[self._offset:]
        if n and n > 0:
            chunk = chunk[:n]
        self._offset += len(chunk)
        return chunk

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass
from pydicom.uid import ExplicitVRLittleEndian, generate_uid
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.routing import Route
from starlette.testclient import TestClient
from starlette.exceptions import HTTPException

from api.auth import User
from api.validate import validation_exception_handler, _ValidationException


def _http_exception(request, exc):
    from starlette.responses import JSONResponse
    return JSONResponse(
        {'error': exc.detail if hasattr(exc, 'detail') else ''},
        status_code=exc.status_code,
    )


class _FakeAuth(BaseHTTPMiddleware):
    def __init__(self, app, user=None):
        super().__init__(app)
        self._user = user or User({'id': 1, 'permissions': []})

    async def dispatch(self, request, call_next):
        request.scope['user'] = self._user
        request.scope['auth'] = None
        return await call_next(request)


def _make_app(user=None):
    from api.dicomweb import DicomWebWado
    return Starlette(
        routes=[
            Route('/dicomweb/studies/{study_uid}', endpoint=DicomWebWado),
            Route('/dicomweb/studies/{study_uid}/series/{series_uid}/instances/{instance_uid}', endpoint=DicomWebWado),
        ],
        middleware=[Middleware(_FakeAuth, user=user)],
        exception_handlers={
            HTTPException: _http_exception,
            _ValidationException: validation_exception_handler,
        },
    )


def _make_mini_dicom(sop_uid=None):
    sop_uid = sop_uid or generate_uid()
    ds = Dataset()
    ds.PatientName = 'Test^Patient'
    ds.PatientID = 'P001'
    ds.StudyInstanceUID = '1.2.3.4.5.6'
    ds.SeriesInstanceUID = '1.2.3.4.5.6.7'
    ds.SOPInstanceUID = sop_uid
    ds.Modality = 'CT'
    ds.StudyDate = '20260725'
    file_meta = FileMetaDataset()
    file_meta.MediaStorageSOPClassUID = '1.2.840.10008.5.1.4.1.1.2'
    file_meta.MediaStorageSOPInstanceUID = sop_uid
    file_meta.TransferSyntaxUID = ExplicitVRLittleEndian
    fd = FileDataset('test.dcm', {}, file_meta=file_meta, preamble=b'\0' * 128)
    for attr in ('PatientName', 'PatientID', 'StudyInstanceUID', 'SeriesInstanceUID', 'SOPInstanceUID', 'Modality', 'StudyDate'):
        setattr(fd, attr, getattr(ds, attr))
    buf = BytesIO()
    fd.save_as(buf, enforce_file_format=False)
    return buf.getvalue()


class _FakeConn:
    async def __aenter__(self):
        return self
    async def __aexit__(self, *args):
        pass


class TestWadoInstance:
    @pytest.mark.asyncio
    async def test_returns_single_instance(self):
        user = User({'id': 1, 'permissions': ['DICOMWEB_READ']})
        client = TestClient(_make_app(user))

        dcm_bytes = _make_mini_dicom()
        conn = _FakeConn()
        conn.fetchrow = AsyncMock(side_effect=[
            # first call: Replica.master() → SELECT * FROM replicas
            {'id': 1, 'type': 'local', 'location': '/data/files',
             'master': True, 'delay': 0, 'status': 'ok',
             'total': 100, 'meta': '{}'},
            # second call: _retrieve_instance query for instance UID
            {'id': 42, 'location': '/tmp/test.dcm', 'name': 'test.dcm',
             'patient_id': 1, 'study_id': 1, 'series_id': 1,
             'meta': '{}', 'replica_meta': '{}'},
        ])

        mock_storage = MagicMock()
        mock_storage.fetch = AsyncMock(return_value='/tmp/test.dcm')

        with patch('api.dicomweb.get_conn', return_value=conn):
            with patch('api.dicomweb.Storage.get', new=AsyncMock(return_value=mock_storage)):
                with patch('aiofiles.open', return_value=_AsyncFileMock(dcm_bytes)):
                    resp = client.get('/dicomweb/studies/1.2.3.4.5.6/series/1.2.3.4.5.6.7/instances/1.2.3.4.5.6.7.8')

        assert resp.status_code == 200
        assert resp.headers['content-type'] == 'application/dicom'
        assert len(resp.content) > 0


class TestWadoDeleted:
    @pytest.mark.asyncio
    async def test_instance_retrieve_excludes_deleted_files(self):
        user = User({'id': 1, 'permissions': ['DICOMWEB_READ']})
        client = TestClient(_make_app(user))

        conn = _FakeConn()
        conn.fetchrow = AsyncMock(side_effect=[
            {'id': 1, 'type': 'local', 'location': '/data/files',
             'master': True, 'delay': 0, 'status': 'ok',
             'total': 100, 'meta': '{}'},
            None,  # deleted file → no row returned
        ])

        with patch('api.dicomweb.get_conn', return_value=conn):
            resp = client.get('/dicomweb/studies/1.2.3.4.5.6/series/1.2.3.4.5.6.7/instances/1.2.3.4.5.6.7.8')

        assert resp.status_code == 404
        sql = conn.fetchrow.call_args_list[1][0][0]
        assert 'f.deleted = false' in sql


class TestWadoUri:
    def _make_conn(self, instance_uid='1.2.3.4.5.6.7.8'):
        conn = _FakeConn()
        conn.fetchrow = AsyncMock(side_effect=[
            {'id': 1, 'type': 'local', 'location': '/data/files',
             'master': True, 'delay': 0, 'status': 'ok',
             'total': 100, 'meta': '{}'},
            {'id': 42, 'location': '/tmp/test.dcm', 'name': 'test.dcm',
             'patient_id': 1, 'study_id': 1, 'series_id': 1,
             'meta': '{}', 'replica_meta': '{}'},
        ])
        return conn

    def _make_app(self, user=None):
        from api.dicomweb import DicomWebWadoUri
        return Starlette(
            routes=[Route('/wado', endpoint=DicomWebWadoUri)],
            middleware=[Middleware(_FakeAuth, user=user)],
            exception_handlers={
                HTTPException: _http_exception,
                _ValidationException: validation_exception_handler,
            },
        )

    def test_returns_single_instance(self):
        user = User({'id': 1, 'permissions': ['DICOMWEB_READ']})
        client = TestClient(self._make_app(user))
        dcm_bytes = _make_mini_dicom()
        conn = self._make_conn()
        mock_storage = MagicMock()
        mock_storage.fetch = AsyncMock(return_value='/tmp/test.dcm')

        with patch('api.dicomweb.get_conn', return_value=conn):
            with patch('api.dicomweb.Storage.get', new=AsyncMock(return_value=mock_storage)):
                with patch('aiofiles.open', return_value=_AsyncFileMock(dcm_bytes)):
                    resp = client.get(
                        '/wado?requestType=WADO&studyUID=1.2.3.4.5.6&objectUID=1.2.3.4.5.6.7.8'
                    )

        assert resp.status_code == 200
        assert resp.headers['content-type'] == 'application/dicom'
        assert len(resp.content) > 0

    def test_missing_requestType_returns_400(self):
        user = User({'id': 1, 'permissions': ['DICOMWEB_READ']})
        client = TestClient(self._make_app(user))

        resp = client.get('/wado?studyUID=1.2.3.4.5.6&objectUID=1.2.3.4.5.6.7.8')

        assert resp.status_code == 400
        assert 'requestType' in resp.text

    def test_missing_all_uids_returns_400(self):
        user = User({'id': 1, 'permissions': ['DICOMWEB_READ']})
        client = TestClient(self._make_app(user))

        resp = client.get('/wado?requestType=WADO')

        assert resp.status_code == 400
        assert 'studyUID' in resp.text

    def test_study_level_returns_multipart(self):
        user = User({'id': 1, 'permissions': ['DICOMWEB_READ']})
        client = TestClient(self._make_app(user))
        dcm_bytes = _make_mini_dicom()

        conn = _FakeConn()
        conn.fetchrow = AsyncMock(return_value={
            'id': 1, 'type': 'local', 'location': '/data/files',
            'master': True, 'delay': 0, 'status': 'ok',
            'total': 100, 'meta': '{}',
        })
        conn.fetch = AsyncMock(return_value=[
            {'id': 42, 'location': '/tmp/test.dcm', 'name': 'test.dcm',
             'patient_id': 1, 'study_id': 1, 'series_id': 1,
             'meta': '{}', 'replica_meta': '{}'},
        ])

        mock_storage = MagicMock()
        mock_storage.fetch = AsyncMock(return_value='/tmp/test.dcm')

        with patch('api.dicomweb.get_conn', return_value=conn):
            with patch('api.dicomweb.Storage.get', new=AsyncMock(return_value=mock_storage)):
                with patch('aiofiles.open', return_value=_AsyncFileMock(dcm_bytes)):
                    resp = client.get('/wado?requestType=WADO&studyUID=1.2.3.4.5.6')

        assert resp.status_code == 200
        assert resp.headers['content-type'].startswith('multipart/related')
        assert b'WADO_BOUNDARY' in resp.content

    def test_object_uid_cross_checked_against_study_uid(self):
        user = User({'id': 1, 'permissions': ['DICOMWEB_READ']})
        client = TestClient(self._make_app(user))

        conn = _FakeConn()
        conn.fetchrow = AsyncMock(side_effect=[
            {'id': 1, 'type': 'local', 'location': '/data/files',
             'master': True, 'delay': 0, 'status': 'ok',
             'total': 100, 'meta': '{}'},
            None,
        ])

        with patch('api.dicomweb.get_conn', return_value=conn):
            resp = client.get(
                '/wado?requestType=WADO&studyUID=1.2.3.4.5.6&objectUID=9.9.9.9.9.9.9.9'
            )

        assert resp.status_code == 400
        assert 'STUDY_UID_MISMATCH' in resp.text

    def test_requires_dicomweb_read_permission(self):
        user = User({'id': 1, 'permissions': []})
        client = TestClient(self._make_app(user))

        resp = client.get('/wado?requestType=WADO&studyUID=1.2.3.4.5.6&objectUID=1.2.3.4.5.6.7.8')

        assert resp.status_code == 403

    def test_returns_single_instance_when_both_object_and_series_uid(self):
        user = User({'id': 1, 'permissions': ['DICOMWEB_READ']})
        client = TestClient(self._make_app(user))
        dcm_bytes = _make_mini_dicom()

        conn = _FakeConn()
        conn.fetchrow = AsyncMock(return_value={
            'id': 42, 'location': '/tmp/test.dcm', 'name': 'test.dcm',
            'patient_id': 1, 'study_id': 1, 'series_id': 1,
            'meta': '{}', 'replica_meta': '{}',
        })
        conn.fetch = AsyncMock(return_value=[
            {'id': 42, 'location': '/tmp/test.dcm', 'name': 'test.dcm',
             'patient_id': 1, 'study_id': 1, 'series_id': 1,
             'meta': '{}', 'replica_meta': '{}'},
        ])

        mock_storage = MagicMock()
        mock_storage.fetch = AsyncMock(return_value='/tmp/test.dcm')

        with patch('api.dicomweb.get_conn', return_value=conn):
            with patch('api.dicomweb.Storage.get', new=AsyncMock(return_value=mock_storage)):
                with patch('aiofiles.open', return_value=_AsyncFileMock(dcm_bytes)):
                    resp = client.get(
                        '/wado?requestType=WADO&studyUID=1.2.3.4.5.6'
                        '&seriesUID=1.2.3.4.5.6.7&objectUID=1.2.3.4.5.6.7.8'
                    )

        assert resp.status_code == 200
        assert resp.headers['content-type'] == 'application/dicom'
        conn.fetch.assert_not_called()


class TestWadoMultipart:
    def test_instance_accept_multipart_returns_multipart_related(self):
        user = User({'id': 1, 'permissions': ['DICOMWEB_READ']})
        client = TestClient(_make_app(user))

        dcm_bytes = _make_mini_dicom()
        conn = _FakeConn()
        conn.fetchrow = AsyncMock(side_effect=[
            {'id': 1, 'type': 'local', 'location': '/data/files',
             'master': True, 'delay': 0, 'status': 'ok',
             'total': 100, 'meta': '{}'},
            {'id': 42, 'location': '/tmp/test.dcm', 'name': 'test.dcm',
             'patient_id': 1, 'study_id': 1, 'series_id': 1,
             'meta': '{}', 'replica_meta': '{}'},
        ])

        mock_storage = MagicMock()
        mock_storage.fetch = AsyncMock(return_value='/tmp/test.dcm')

        with patch('api.dicomweb.get_conn', return_value=conn):
            with patch('api.dicomweb.Storage.get', new=AsyncMock(return_value=mock_storage)):
                with patch('aiofiles.open', return_value=_AsyncFileMock(dcm_bytes)):
                    resp = client.get(
                        '/dicomweb/studies/1.2.3.4.5.6/series/1.2.3.4.5.6.7/instances/1.2.3.4.5.6.7.8',
                        headers={'Accept': 'multipart/related; type="application/dicom"'},
                    )

        assert resp.status_code == 200
        assert resp.headers['content-type'].startswith('multipart/related')
        assert 'WADO_BOUNDARY' in resp.headers['content-type']
        assert b'WADO_BOUNDARY' in resp.content
        assert dcm_bytes in resp.content

    def test_metadata_takes_precedence_over_multipart(self):
        user = User({'id': 1, 'permissions': ['DICOMWEB_READ']})
        client = TestClient(_make_app(user))

        conn = _FakeConn()
        conn.fetchrow = AsyncMock(side_effect=[
            {'id': 1, 'type': 'local', 'location': '/data/files',
             'master': True, 'delay': 0, 'status': 'ok',
             'total': 100, 'meta': '{}'},
            {'id': 42, 'location': '/tmp/test.dcm', 'name': 'test.dcm',
             'patient_id': 1, 'study_id': 1, 'series_id': 1,
             'meta': '{"sop_instance_uid": "1.2.3.4.5.6.7.8"}',
             'replica_meta': '{}'},
        ])

        with patch('api.dicomweb.get_conn', return_value=conn):
            resp = client.get(
                '/dicomweb/studies/1.2.3.4.5.6/series/1.2.3.4.5.6.7/instances/1.2.3.4.5.6.7.8',
                headers={'Accept': 'multipart/related; type="application/dicom", application/dicom+json'},
            )

        assert resp.status_code == 200
        assert resp.headers['content-type'] == 'application/dicom+json'


class TestWadoMetadata:
    def _make_conn(self):
        conn = _FakeConn()
        conn.fetchrow = AsyncMock(side_effect=[
            {'id': 1, 'type': 'local', 'location': '/data/files',
             'master': True, 'delay': 0, 'status': 'ok',
             'total': 100, 'meta': '{}'},
            {'id': 42, 'location': '/tmp/test.dcm', 'name': 'test.dcm',
             'patient_id': 1, 'study_id': 1, 'series_id': 1,
             'meta': '{"sop_instance_uid": "1.2.3.4.5.6.7.8", "patient_name": "Test^Patient"}',
             'replica_meta': '{}'},
        ])
        return conn

    def test_accept_dicom_json_returns_metadata(self):
        user = User({'id': 1, 'permissions': ['DICOMWEB_READ']})
        client = TestClient(_make_app(user))
        conn = self._make_conn()

        with patch('api.dicomweb.get_conn', return_value=conn):
            resp = client.get(
                '/dicomweb/studies/1.2.3.4.5.6/series/1.2.3.4.5.6.7/instances/1.2.3.4.5.6.7.8',
                headers={'Accept': 'application/dicom+json'},
            )

        assert resp.status_code == 200
        assert resp.headers['content-type'] == 'application/dicom+json'
        payload = resp.json()
        assert isinstance(payload, list) and len(payload) == 1
        assert payload[0]['00080018']['vr'] == 'UI'
        assert payload[0]['00080018']['Value'] == ['1.2.3.4.5.6.7.8']

    def test_transfer_syntax_star_returns_dicom(self):
        user = User({'id': 1, 'permissions': ['DICOMWEB_READ']})
        client = TestClient(_make_app(user))
        dcm_bytes = _make_mini_dicom()
        conn = self._make_conn()
        mock_storage = MagicMock()
        mock_storage.fetch = AsyncMock(return_value='/tmp/test.dcm')

        with patch('api.dicomweb.get_conn', return_value=conn):
            with patch('api.dicomweb.Storage.get', new=AsyncMock(return_value=mock_storage)):
                with patch('aiofiles.open', return_value=_AsyncFileMock(dcm_bytes)):
                    resp = client.get(
                        '/dicomweb/studies/1.2.3.4.5.6/series/1.2.3.4.5.6.7/instances/1.2.3.4.5.6.7.8?transferSyntax=*'
                    )

        assert resp.status_code == 200
        assert resp.headers['content-type'] == 'application/dicom'

    def test_unsupported_transfer_syntax_returns_406(self):
        user = User({'id': 1, 'permissions': ['DICOMWEB_READ']})
        client = TestClient(_make_app(user))

        resp = client.get(
            '/dicomweb/studies/1.2.3.4.5.6/series/1.2.3.4.5.6.7/instances/1.2.3.4.5.6.7.8?transferSyntax=1.2.840.10008.1.2'
        )

        assert resp.status_code == 406
        assert 'NOT_ACCEPTABLE' in resp.text


class TestWadoDelete:
    @pytest.mark.asyncio
    async def test_delete_instance_soft_deletes_and_audits(self):
        user = User({'id': 1, 'permissions': ['DICOMWEB_READ', 'DICOMWEB_WRITE']})
        client = TestClient(_make_app(user))

        conn = _FakeConn()
        conn.execute = AsyncMock(return_value='UPDATE 1')

        with patch('api.dicomweb.get_conn', return_value=conn):
            with patch('api.dicomweb.AuditLog') as mock_audit:
                mock_audit.return_value.log_event = AsyncMock()
                resp = client.delete(
                    '/dicomweb/studies/1.2.3.4.5.6/series/1.2.3.4.5.6.7/instances/1.2.3.4.5.6.7.8'
                )

        assert resp.status_code == 204
        sql = conn.execute.call_args_list[0][0][0]
        assert 'sop_instance_uid' in sql
        assert 'deleted = true' in sql
        mock_audit.return_value.log_event.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_delete_study_soft_deletes_all_instances(self):
        user = User({'id': 1, 'permissions': ['DICOMWEB_READ', 'DICOMWEB_WRITE']})
        client = TestClient(_make_app(user))

        conn = _FakeConn()
        conn.execute = AsyncMock(return_value='UPDATE 3')

        with patch('api.dicomweb.get_conn', return_value=conn):
            with patch('api.dicomweb.AuditLog') as mock_audit:
                mock_audit.return_value.log_event = AsyncMock()
                resp = client.delete('/dicomweb/studies/1.2.3.4.5.6')

        assert resp.status_code == 204
        sql = conn.execute.call_args_list[0][0][0]
        assert 'study_instance_uid' in sql
        assert 'deleted = true' in sql
        mock_audit.return_value.log_event.assert_awaited_once()


def _make_pixel_dicom(sop_uid=None, multiframes=1, rows=8, cols=8, value=100):
    """Minimal DICOM with real Pixel Data; frames filled with value+i so
    frame extraction is verifiable (frame i is all value+i)."""
    import numpy as np

    sop_uid = sop_uid or generate_uid()
    ds = Dataset()
    ds.PatientName = 'Test^Patient'
    ds.PatientID = 'P001'
    ds.StudyInstanceUID = '1.2.3.4.5.6'
    ds.SeriesInstanceUID = '1.2.3.4.5.6.7'
    ds.SOPInstanceUID = sop_uid
    ds.Modality = 'CT'
    ds.StudyDate = '20260725'
    ds.SOPClassUID = '1.2.840.10008.5.1.4.1.1.2'
    ds.Rows = rows
    ds.Columns = cols
    ds.SamplesPerPixel = 1
    ds.PhotometricInterpretation = 'MONOCHROME2'
    ds.BitsAllocated = 16
    ds.BitsStored = 16
    ds.HighBit = 15
    ds.PixelRepresentation = 0
    if multiframes > 1:
        ds.NumberOfFrames = str(multiframes)
    frames = [np.full((rows, cols), value + i, dtype=np.uint16) for i in range(multiframes)]
    pixels = np.concatenate(frames) if multiframes > 1 else frames[0]
    ds.PixelData = pixels.tobytes()
    file_meta = FileMetaDataset()
    file_meta.MediaStorageSOPClassUID = ds.SOPClassUID
    file_meta.MediaStorageSOPInstanceUID = sop_uid
    file_meta.TransferSyntaxUID = ExplicitVRLittleEndian
    fd = FileDataset('test.dcm', ds, file_meta=file_meta, preamble=b'\0' * 128)
    buf = BytesIO()
    fd.save_as(buf, enforce_file_format=False)
    return buf.getvalue()


class TestWadoFrames:
    def _make_app(self, user=None):
        from api.dicomweb import DicomWebWadoFrames
        return Starlette(
            routes=[
                Route(
                    '/dicomweb/studies/{study_uid}/series/{series_uid}/instances/{instance_uid}/frames/{frame_number}',
                    endpoint=DicomWebWadoFrames,
                ),
            ],
            middleware=[Middleware(_FakeAuth, user=user)],
            exception_handlers={
                HTTPException: _http_exception,
                _ValidationException: validation_exception_handler,
            },
        )

    def _make_conn(self, found=True):
        conn = _FakeConn()
        conn.fetchrow = AsyncMock(side_effect=[
            {'id': 1, 'type': 'local', 'location': '/data/files',
             'master': True, 'delay': 0, 'status': 'ok',
             'total': 100, 'meta': '{}'},
            {'id': 42, 'location': '/tmp/test.dcm', 'name': 'test.dcm',
             'meta': '{}', 'replica_meta': '{}', 'patient_id': 'P001',
             'study_id': 5, 'series_number': 1}
            if found else None,
        ])
        return conn

    def _get(self, client, conn, dcm_bytes, frame='1', tmp_path=None):
        target = tmp_path / 'frame_test.dcm'
        target.write_bytes(dcm_bytes)
        mock_storage = MagicMock()
        mock_storage.fetch = AsyncMock(return_value=str(target))
        with patch('api.dicomweb.get_conn', return_value=conn):
            with patch('api.dicomweb.Storage.get', new=AsyncMock(return_value=mock_storage)):
                return client.get(
                    '/dicomweb/studies/1.2.3.4.5.6/series/1.2.3.4.5.6.7/instances/1.2.3.4.5.6.7.8/frames/' + frame
                )

    @pytest.mark.asyncio
    async def test_returns_single_frame_as_octet_stream(self, tmp_path):
        user = User({'id': 1, 'permissions': ['DICOMWEB_READ']})
        client = TestClient(self._make_app(user))
        dcm_bytes = _make_pixel_dicom(rows=4, cols=4, value=7)

        resp = self._get(client, self._make_conn(), dcm_bytes, '1', tmp_path)

        assert resp.status_code == 200
        assert resp.headers['content-type'] == 'application/octet-stream'
        import numpy as np
        assert np.frombuffer(resp.content, dtype=np.uint16).tolist() == [7] * 16

    @pytest.mark.asyncio
    async def test_multiframe_frame_indexing(self, tmp_path):
        user = User({'id': 1, 'permissions': ['DICOMWEB_READ']})
        client = TestClient(self._make_app(user))
        dcm_bytes = _make_pixel_dicom(multiframes=3, rows=4, cols=4, value=1)

        resp = self._get(client, self._make_conn(), dcm_bytes, '2', tmp_path)

        assert resp.status_code == 200
        import numpy as np
        assert np.frombuffer(resp.content, dtype=np.uint16).tolist() == [2] * 16

    @pytest.mark.asyncio
    async def test_frame_out_of_range_404(self, tmp_path):
        user = User({'id': 1, 'permissions': ['DICOMWEB_READ']})
        client = TestClient(self._make_app(user))
        dcm_bytes = _make_pixel_dicom(rows=4, cols=4, value=1)

        resp = self._get(client, self._make_conn(), dcm_bytes, '2', tmp_path)

        assert resp.status_code == 404
        assert 'FRAME_OUT_OF_RANGE' in resp.text

    @pytest.mark.asyncio
    async def test_frame_zero_is_out_of_range(self, tmp_path):
        user = User({'id': 1, 'permissions': ['DICOMWEB_READ']})
        client = TestClient(self._make_app(user))
        dcm_bytes = _make_pixel_dicom(rows=4, cols=4, value=1)

        resp = self._get(client, self._make_conn(), dcm_bytes, '0', tmp_path)

        assert resp.status_code == 404
        assert 'FRAME_OUT_OF_RANGE' in resp.text

    @pytest.mark.asyncio
    async def test_non_integer_frame_400(self, tmp_path):
        user = User({'id': 1, 'permissions': ['DICOMWEB_READ']})
        client = TestClient(self._make_app(user))
        dcm_bytes = _make_pixel_dicom(rows=4, cols=4, value=1)

        resp = self._get(client, self._make_conn(), dcm_bytes, 'abc', tmp_path)

        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_missing_instance_404(self, tmp_path):
        user = User({'id': 1, 'permissions': ['DICOMWEB_READ']})
        client = TestClient(self._make_app(user))
        dcm_bytes = _make_pixel_dicom(rows=4, cols=4, value=1)

        resp = self._get(client, self._make_conn(found=False), dcm_bytes, '1', tmp_path)

        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_requires_dicomweb_read_permission(self, tmp_path):
        user = User({'id': 1, 'permissions': []})
        client = TestClient(self._make_app(user))
        dcm_bytes = _make_pixel_dicom(rows=4, cols=4, value=1)

        resp = self._get(client, self._make_conn(), dcm_bytes, '1', tmp_path)

        assert resp.status_code == 403
