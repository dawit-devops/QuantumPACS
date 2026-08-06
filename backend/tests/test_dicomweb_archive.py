from io import BytesIO
from unittest.mock import AsyncMock, MagicMock, patch
import zipfile

import pytest
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.routing import Route
from starlette.testclient import TestClient

from api.auth import User

from tests.test_dicomweb_wado import _FakeAuth


class _FakeConn:
    async def __aenter__(self):
        return self
    async def __aexit__(self, *args):
        pass


class TestDicomWebArchive:
    def _make_app(self, user=None):
        from api.dicomweb import DicomWebArchive
        return Starlette(
            routes=[
                Route('/dicomweb/studies/{study_uid}/archive', endpoint=DicomWebArchive),
                Route('/dicomweb/studies/{study_uid}/series/{series_uid}/archive', endpoint=DicomWebArchive),
            ],
            middleware=[Middleware(_FakeAuth, user=user)],
        )

    def _make_conn(self, series_uid=None):
        conn = _FakeConn()
        conn.fetchrow = AsyncMock(side_effect=[
            {'id': 1, 'type': 'local', 'location': '/data/files',
             'master': True, 'delay': 0, 'status': 'ok',
             'total': 100, 'meta': '{}'},
        ])
        rows = [
            {'id': 1, 'sop_instance_uid': '1.2.3.4.5.6.7.8',
             'sop_class_uid': '1.2.840.10008.5.1.4.1.1.2',
             'instance_number': '1', 'series_number': 1,
             'series_instance_uid': series_uid or '1.2.3.4.5.6.7',
             'meta': '{"patient_name": "Test^Patient"}'},
            {'id': 2, 'sop_instance_uid': '1.2.3.4.5.6.7.9',
             'sop_class_uid': '1.2.840.10008.5.1.4.1.1.2',
             'instance_number': '2', 'series_number': 1,
             'series_instance_uid': series_uid or '1.2.3.4.5.6.7',
             'meta': '{"patient_name": "Test^Patient"}'},
        ]
        conn.fetch = AsyncMock(return_value=rows)
        return conn

    def test_study_archive_streams_zip_named_by_uid(self, tmp_path):
        user = User({'id': 1, 'permissions': ['DICOMWEB_READ']})
        client = TestClient(self._make_app(user))
        conn = self._make_conn()
        dicom_file = tmp_path / 'instance.dcm'
        dicom_file.write_bytes(b'DICM fake bytes')

        mock_storage = MagicMock()
        mock_storage.fetch = AsyncMock(return_value=str(dicom_file))

        with patch('api.dicomweb.get_conn', return_value=conn):
            with patch('api.dicomweb.Storage.get', new=AsyncMock(return_value=mock_storage)):
                resp = client.get('/dicomweb/studies/1.2.3.4.5.6/archive')

        assert resp.status_code == 200
        assert resp.headers['content-type'] == 'application/zip'
        zf = zipfile.ZipFile(BytesIO(resp.content))
        names = zf.namelist()
        assert '1.2.3.4.5.6.7/1.2.3.4.5.6.7.8.dcm' in names
        assert '1.2.3.4.5.6.7/1.2.3.4.5.6.7.9.dcm' in names
        assert 'metadata.json' in names
        assert zf.read('1.2.3.4.5.6.7/1.2.3.4.5.6.7.8.dcm') == b'DICM fake bytes'
        zf.close()

    def test_series_archive_returns_404_when_empty(self):
        user = User({'id': 1, 'permissions': ['DICOMWEB_READ']})
        client = TestClient(self._make_app(user))
        conn = _FakeConn()
        conn.fetchrow = AsyncMock(side_effect=[
            {'id': 1, 'type': 'local', 'location': '/data/files',
             'master': True, 'delay': 0, 'status': 'ok',
             'total': 100, 'meta': '{}'},
        ])
        conn.fetch = AsyncMock(return_value=[])

        with patch('api.dicomweb.get_conn', return_value=conn):
            resp = client.get('/dicomweb/studies/1.2.3.4.5.6/series/9.9.9.9.9/archive')

        assert resp.status_code == 404
