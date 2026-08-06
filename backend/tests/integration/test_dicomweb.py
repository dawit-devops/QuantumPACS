from io import BytesIO
from unittest.mock import AsyncMock, MagicMock, patch

from pydicom.dataset import Dataset, FileDataset, FileMetaDataset
from pydicom.uid import ExplicitVRLittleEndian, generate_uid
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.routing import Route
from starlette.testclient import TestClient
from starlette.exceptions import HTTPException

from api.auth import User
from api.validate import validation_exception_handler, _ValidationException


class _AsyncFileMock:
    def __init__(self, data):
        self._data = data
        self._exhausted = False

    async def read(self, n=-1):
        if self._exhausted:
            return b''
        self._exhausted = True
        return self._data

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass


class _FakeAuth(BaseHTTPMiddleware):
    def __init__(self, app, user=None):
        super().__init__(app)
        self._user = user or User({'id': 1, 'permissions': []})

    async def dispatch(self, request, call_next):
        request.scope['user'] = self._user
        request.scope['auth'] = None
        return await call_next(request)


def _http_exception(request, exc):
    from starlette.responses import JSONResponse
    return JSONResponse(
        {'error': exc.detail if hasattr(exc, 'detail') else ''},
        status_code=exc.status_code,
    )


def _make_dicomweb_app(user=None):
    from api.dicomweb import DicomWebStudies, DicomWebWado, DicomWebWadoUri
    return Starlette(
        routes=[
            Route('/dicomweb/studies', endpoint=DicomWebStudies),
            Route('/dicomweb/studies/{study_uid}', endpoint=DicomWebWado),
            Route('/dicomweb/studies/{study_uid}/series', endpoint=DicomWebStudies),
            Route('/dicomweb/studies/{study_uid}/series/{series_uid}', endpoint=DicomWebWado),
            Route('/dicomweb/studies/{study_uid}/series/{series_uid}/instances', endpoint=DicomWebStudies),
            Route('/dicomweb/studies/{study_uid}/series/{series_uid}/instances/{instance_uid}', endpoint=DicomWebWado),
            Route('/wado', endpoint=DicomWebWadoUri),
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


class TestDicomWebQidoIntegration:
    def test_qido_studies_returns_json(self):
        user = User({'id': 1, 'permissions': ['DICOMWEB_READ']})
        client = TestClient(_make_dicomweb_app(user))
        conn = _FakeConn()
        conn.fetch = AsyncMock(return_value=[
            {'patient_id': 'P001', 'name': 'Test^Patient', 'birth_date': None,
             'sex': None, 'study_db_id': 1, 'study_id': 'ST1',
             'study_description': None, 'study_instance_uid': '1.2.3.4.5.6',
             'accession_number': 'ACC001'},
        ])
        conn.fetchval = AsyncMock(return_value=1)

        with patch('api.dicomweb.get_conn', return_value=conn):
            resp = client.get('/dicomweb/studies')

        assert resp.status_code == 200
        assert resp.headers['content-type'] == 'application/dicom+json'
        assert 'X-Total-Count' in resp.headers
        data = resp.json()
        assert len(data) == 1
        assert data[0]['0020000D']['Value'][0] == '1.2.3.4.5.6'

    def test_qido_studies_with_patient_id_filter(self):
        user = User({'id': 1, 'permissions': ['DICOMWEB_READ']})
        client = TestClient(_make_dicomweb_app(user))
        conn = _FakeConn()
        conn.fetch = AsyncMock(return_value=[])
        conn.fetchval = AsyncMock(return_value=0)

        with patch('api.dicomweb.get_conn', return_value=conn):
            resp = client.get('/dicomweb/studies?PatientID=P001')

        assert resp.status_code == 200
        assert resp.json() == []

    def test_qido_returns_403_without_permission(self):
        user = User({'id': 1, 'permissions': []})
        client = TestClient(_make_dicomweb_app(user))
        resp = client.get('/dicomweb/studies')
        assert resp.status_code == 403


class TestDicomWebStowIntegration:
    def test_stow_rejects_missing_permission(self):
        user = User({'id': 1, 'permissions': []})
        client = TestClient(_make_dicomweb_app(user))
        dcm_bytes = _make_mini_dicom()
        boundary = 'TEST_BOUNDARY'
        body = (
            f'--{boundary}\r\n'
            f'Content-Type: application/dicom\r\n\r\n'
        ).encode() + dcm_bytes + f'\r\n--{boundary}--\r\n'.encode()

        resp = client.post(
            '/dicomweb/studies',
            content=body,
            headers={'Content-Type': f'multipart/related; type=application/dicom; boundary={boundary}'},
        )

        assert resp.status_code == 403


class TestDicomWebWadoIntegration:
    def test_wado_rs_returns_instance(self):
        user = User({'id': 1, 'permissions': ['DICOMWEB_READ']})
        client = TestClient(_make_dicomweb_app(user))
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
                    resp = client.get('/dicomweb/studies/1.2.3.4.5.6/series/1.2.3.4.5.6.7/instances/1.2.3.4.5.6.7.8')

        assert resp.status_code == 200
        assert resp.headers['content-type'] == 'application/dicom'
        assert len(resp.content) > 0

    def test_wado_uri_returns_instance(self):
        user = User({'id': 1, 'permissions': ['DICOMWEB_READ']})
        client = TestClient(_make_dicomweb_app(user))
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
                        '/wado?requestType=WADO&studyUID=1.2.3.4.5.6&objectUID=1.2.3.4.5.6.7.8'
                    )

        assert resp.status_code == 200
        assert resp.headers['content-type'] == 'application/dicom'

    def test_wado_uri_returns_400_when_missing_request_type(self):
        user = User({'id': 1, 'permissions': ['DICOMWEB_READ']})
        client = TestClient(_make_dicomweb_app(user))
        resp = client.get('/wado?studyUID=1.2.3.4.5.6&objectUID=1.2.3.4.5.6.7.8')
        assert resp.status_code == 400
