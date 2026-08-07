from io import BytesIO
from unittest.mock import AsyncMock, patch

import pytest
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
    from api.dicomweb import DicomWebStudies
    return Starlette(
        routes=[
            Route('/dicomweb/studies', endpoint=DicomWebStudies),
            Route('/dicomweb/studies/{study_uid}/series', endpoint=DicomWebStudies),
            Route('/dicomweb/studies/{study_uid}/series/{series_uid}/instances', endpoint=DicomWebStudies),
        ],
        middleware=[Middleware(_FakeAuth, user=user)],
        exception_handlers={
            HTTPException: _http_exception,
            _ValidationException: validation_exception_handler,
        },
    )


def _make_dicom_bytes(patient_id='P001', study_uid=None, modality='CT'):
    study_uid = study_uid or generate_uid()
    series_uid = generate_uid()
    sop_uid = generate_uid()

    ds = Dataset()
    ds.PatientName = 'Test^Patient'
    ds.PatientID = patient_id
    ds.StudyInstanceUID = study_uid
    ds.SeriesInstanceUID = series_uid
    ds.SOPInstanceUID = sop_uid
    ds.Modality = modality
    ds.StudyDate = '20260725'

    file_meta = FileMetaDataset()
    file_meta.MediaStorageSOPClassUID = '1.2.840.10008.5.1.4.1.1.2'
    file_meta.MediaStorageSOPInstanceUID = sop_uid
    file_meta.TransferSyntaxUID = ExplicitVRLittleEndian

    fd = FileDataset('test.dcm', {}, file_meta=file_meta, preamble=b'\0' * 128)
    fd.PatientName = ds.PatientName
    fd.PatientID = ds.PatientID
    fd.StudyInstanceUID = ds.StudyInstanceUID
    fd.SeriesInstanceUID = ds.SeriesInstanceUID
    fd.SOPInstanceUID = ds.SOPInstanceUID
    fd.Modality = modality
    fd.StudyDate = ds.StudyDate

    buf = BytesIO()
    fd.save_as(buf, enforce_file_format=False)
    return buf.getvalue()


def _multipart_body(dicom_parts):
    boundary = 'STOW_TEST_BOUNDARY'
    lines = []
    for part in dicom_parts:
        lines.append(f'--{boundary}')
        lines.append('Content-Type: application/dicom')
        lines.append('')
        if isinstance(part, bytes):
            lines.append(part.decode('latin-1'))
        else:
            lines.append(part)
    lines.append(f'--{boundary}--')
    body = '\r\n'.join(lines)
    return body.encode('latin-1'), boundary


class TestStowRs:
    @pytest.mark.asyncio
    async def test_stores_single_instance(self):
        user = User({'id': 1, 'permissions': ['DICOMWEB_READ', 'DICOMWEB_WRITE']})
        client = TestClient(_make_app(user))

        dcm_bytes = _make_dicom_bytes()
        body, boundary = _multipart_body([dcm_bytes])

        with patch('api.dicomweb.store_instance', new=AsyncMock(return_value=True)) as mock_store:
            resp = client.post(
                '/dicomweb/studies',
                content=body,
                headers={'Content-Type': f'multipart/related; type=application/dicom; boundary={boundary}'},
            )

        assert resp.status_code == 200
        assert resp.headers['content-type'] == 'application/dicom+json'
        report = resp.json()
        # STOW-RS success report (PS3.18): RetrieveURL + Referenced SOP Seq.
        assert '00081190' in report
        assert report['00081190']['vr'] == 'UR'
        assert '00081198' in report
        refs = report['00081198']['Value']
        assert len(refs) == 1
        assert refs[0]['00081155']['Value'][0].startswith('1.2.')
        assert '00081199' not in report
        mock_store.assert_called_once()

    @pytest.mark.asyncio
    async def test_returns_400_on_malformed_body(self):
        user = User({'id': 1, 'permissions': ['DICOMWEB_READ', 'DICOMWEB_WRITE']})
        client = TestClient(_make_app(user))

        body, boundary = _multipart_body([b'not a valid DICOM file at all'])

        resp = client.post(
            '/dicomweb/studies',
            content=body,
            headers={'Content-Type': f'multipart/related; type=application/dicom; boundary={boundary}'},
        )

        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_returns_400_when_sop_instance_uid_missing(self):
        user = User({'id': 1, 'permissions': ['DICOMWEB_READ', 'DICOMWEB_WRITE']})
        client = TestClient(_make_app(user))

        ds = Dataset()
        ds.PatientName = 'Test^Patient'
        ds.PatientID = 'P001'
        ds.StudyInstanceUID = generate_uid()
        ds.SeriesInstanceUID = generate_uid()
        ds.Modality = 'CT'
        file_meta = FileMetaDataset()
        file_meta.MediaStorageSOPClassUID = '1.2.840.10008.5.1.4.1.1.2'
        file_meta.MediaStorageSOPInstanceUID = generate_uid()
        file_meta.TransferSyntaxUID = ExplicitVRLittleEndian
        fd = FileDataset('no_sop.dcm', {}, file_meta=file_meta, preamble=b'\0' * 128)
        fd.PatientName = ds.PatientName
        fd.PatientID = ds.PatientID
        fd.StudyInstanceUID = ds.StudyInstanceUID
        fd.SeriesInstanceUID = ds.SeriesInstanceUID
        fd.Modality = ds.Modality
        buf = BytesIO()
        fd.save_as(buf, enforce_file_format=False)

        body, boundary = _multipart_body([buf.getvalue()])

        with patch('api.dicomweb.store_instance', new=AsyncMock()) as mock_store:
            resp = client.post(
                '/dicomweb/studies',
                content=body,
                headers={'Content-Type': f'multipart/related; type=application/dicom; boundary={boundary}'},
            )

        assert resp.status_code == 400
        mock_store.assert_not_called()

    def test_parse_multipart_accepts_lf_only_separators(self):
        from api.dicomweb import _parse_multipart_related

        boundary = 'LF_BOUNDARY'
        dcm = _make_dicom_bytes()
        body = (
            f'--{boundary}\n'
            'Content-Type: application/dicom\n\n'
        ).encode('latin-1') + dcm + b'\n--' + boundary.encode('latin-1') + b'--\n'

        parts = _parse_multipart_related(
            body,
            f'multipart/related; type=application/dicom; boundary={boundary}',
        )
        assert len(parts) == 1
        assert parts[0] == dcm

    @pytest.mark.asyncio
    async def test_requires_write_permission(self):
        user = User({'id': 1, 'permissions': ['DICOMWEB_READ']})
        client = TestClient(_make_app(user))

        dcm_bytes = _make_dicom_bytes()
        body, boundary = _multipart_body([dcm_bytes])

        resp = client.post(
            '/dicomweb/studies',
            content=body,
            headers={'Content-Type': f'multipart/related; type=application/dicom; boundary={boundary}'},
        )

        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_rejects_invalid_modality(self):
        user = User({'id': 1, 'permissions': ['DICOMWEB_READ', 'DICOMWEB_WRITE']})
        client = TestClient(_make_app(user))

        dcm_bytes = _make_dicom_bytes(modality='QQ')
        body, boundary = _multipart_body([dcm_bytes])

        mock_store = AsyncMock(return_value=True)
        with patch('api.dicomweb.store_instance', mock_store):
            resp = client.post(
                '/dicomweb/studies',
                content=body,
                headers={'Content-Type': f'multipart/related; type=application/dicom; boundary={boundary}'},
            )

        assert resp.status_code == 400
        mock_store.assert_not_called()

    @pytest.mark.asyncio
    async def test_returns_413_when_part_exceeds_cap(self):
        user = User({'id': 1, 'permissions': ['DICOMWEB_READ', 'DICOMWEB_WRITE']})
        client = TestClient(_make_app(user))

        boundary = 'STOW_CAP_BOUNDARY'
        body = (
            f'--{boundary}\r\n'
            'Content-Type: application/dicom\r\n\r\n'
        ).encode('latin-1') + b'X' * (2 * 1024 * 1024) + f'\r\n--{boundary}--\r\n'.encode('latin-1')

        with patch('config.config', {'max_stow_size_mb': '1'}):
            resp = client.post(
                '/dicomweb/studies',
                content=body,
                headers={'Content-Type': f'multipart/related; type=application/dicom; boundary={boundary}'},
            )

        assert resp.status_code == 413
        assert 'PAYLOAD_TOO_LARGE' in resp.text
