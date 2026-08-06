from io import BytesIO
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydicom.dataset import Dataset, FileDataset, FileMetaDataset


class _AsyncFileMock:
    def __init__(self, data):
        self._data = data

    async def read(self):
        return self._data

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

    def test_missing_object_uid_returns_400(self):
        user = User({'id': 1, 'permissions': ['DICOMWEB_READ']})
        client = TestClient(self._make_app(user))

        resp = client.get('/wado?requestType=WADO&studyUID=1.2.3.4.5.6')

        assert resp.status_code == 400
        assert 'studyUID' in resp.text

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
