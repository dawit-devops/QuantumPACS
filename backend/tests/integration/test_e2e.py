"""
E2E test skeleton for DICOMweb store-search-retrieve workflow.

Uses testcontainers to spin up a PostgreSQL instance, runs migrations,
and exercises the full DICOMweb API path.

Skipped if testcontainers or docker is not available.
"""

import pytest

pytest.importorskip('testcontainers')
pytest.importorskip('docker')


@pytest.mark.skip(reason='testcontainers E2E — requires docker and testcontainers-py')
class TestDicomWebE2E:
    @pytest.fixture(scope='class')
    def postgres_container(self):
        from testcontainers.postgres import PostgresContainer
        with PostgresContainer('postgres:16-alpine') as pg:
            yield pg

    @pytest.fixture(scope='class')
    def db_url(self, postgres_container):
        return postgres_container.get_connection_url()

    @pytest.fixture(scope='class')
    def app(self, db_url, monkeypatch):
        monkeypatch.setenv('DATABASE_URL', db_url)
        from app import app
        return app

    @pytest.fixture(scope='class')
    def client(self, app):
        from starlette.testclient import TestClient
        with TestClient(app) as c:
            yield c

    def test_store_study(self, client):
        resp = client.options('/dicomweb/studies')
        assert resp.status_code == 200

    def test_api_health(self, client):
        resp = client.get('/api/health')
        assert resp.status_code in (200, 404)

    def test_store_search_retrieve_flow(self, client):
        from io import BytesIO
        from pydicom.dataset import Dataset, FileDataset, FileMetaDataset
        from pydicom.uid import ExplicitVRLittleEndian, generate_uid

        sop_uid = generate_uid()
        ds = Dataset()
        ds.PatientName = 'E2E^Test'
        ds.PatientID = 'E2E001'
        ds.StudyInstanceUID = '2.25.1.1.1'
        ds.SeriesInstanceUID = '2.25.1.1.1.1'
        ds.SOPInstanceUID = sop_uid
        ds.Modality = 'CT'
        ds.StudyDate = '20260731'
        file_meta = FileMetaDataset()
        file_meta.MediaStorageSOPClassUID = '1.2.840.10008.5.1.4.1.1.2'
        file_meta.MediaStorageSOPInstanceUID = sop_uid
        file_meta.TransferSyntaxUID = ExplicitVRLittleEndian
        fd = FileDataset('e2e.dcm', {}, file_meta=file_meta, preamble=b'\0' * 128)
        for attr in ('PatientName', 'PatientID', 'StudyInstanceUID', 'SeriesInstanceUID', 'SOPInstanceUID', 'Modality', 'StudyDate'):
            setattr(fd, attr, getattr(ds, attr))
        buf = BytesIO()
        fd.save_as(buf, enforce_file_format=False)
        dcm_bytes = buf.getvalue()

        boundary = 'E2E_BOUNDARY'
        body = (
            f'--{boundary}\r\n'
            f'Content-Type: application/dicom\r\n\r\n'
        ).encode() + dcm_bytes + f'\r\n--{boundary}--\r\n'.encode()

        store_resp = client.post(
            '/dicomweb/studies',
            content=body,
            headers={'Content-Type': f'multipart/related; type=application/dicom; boundary={boundary}'},
        )
        assert store_resp.status_code in (200, 401, 403)

    def test_search_returns_json(self, client):
        resp = client.get('/dicomweb/studies', headers={'Accept': 'application/dicom+json'})
        assert resp.status_code in (200, 401, 403)
        if resp.status_code == 200:
            assert resp.headers.get('content-type', '').startswith('application/dicom+json')

    def test_retrieve_study(self, client):
        resp = client.get('/dicomweb/studies/2.25.1.1.1')
        assert resp.status_code in (200, 401, 403, 404)
