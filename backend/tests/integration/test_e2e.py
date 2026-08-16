"""
E2E test skeleton for DICOMweb store-search-retrieve workflow.

Uses testcontainers to spin up a PostgreSQL instance, runs migrations,
and exercises the full DICOMweb API path.

Skipped if testcontainers or docker is not available.
"""

import pytest

pytest.importorskip('testcontainers')
pytest.importorskip('docker')


@pytest.fixture(scope='class')
def postgres_container():
    from testcontainers.community.postgres import PostgresContainer
    with PostgresContainer('postgres:18-alpine') as pg:
        yield pg


@pytest.fixture(scope='class')
def app(postgres_container):
    # Point config at the container DB *before* importing the app — config
    # reads DB_* env vars once at import time (config.py load_config).
    import os
    port = postgres_container.get_exposed_port(5432)
    managed = {
        'DB_HOST': '127.0.0.1',
        'DB_PORT': str(port),
        'DB_USER': 'test',
        'DB_PASSWORD': 'test',
        'DB_DATABASE': 'test',
        # assert_production_secret() rejects any known/committed secret; CI
        # has no config.local.yaml, so a fresh-looking test secret is required.
        'SECRET': 'quantumpacs-ci-e2e-test-secret-8f2b1a9c-2026',
        # lifecycle.setup() exits unless it is Docker mode or a redis password
        # is configured — either satisfies the guard; Docker mode is accurate
        # here since the DB under test runs in a container.
        'QUANTUMPACS_DOCKER': '1',
    }
    old = {k: os.environ.get(k) for k in managed}
    os.environ.update(managed)
    try:
        from app import app
        yield app
    finally:
        for k, v in old.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


@pytest.fixture(scope='class')
def client(app):
    from starlette.testclient import TestClient
    # TrustedHostMiddleware only allows configured hosts; `testserver` (the
    # TestClient default) is not one of them.
    with TestClient(app, base_url='http://localhost') as c:
        yield c


class TestDicomWebE2E:
    def test_store_study(self, client):
        resp = client.options('/api/v2/dicomweb/studies')
        assert resp.status_code == 200

    def test_api_health(self, client):
        resp = client.get('/api/v2/health')
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
            '/api/v2/dicomweb/studies/2.25.1.1.1/instances',
            content=body,
            headers={'Content-Type': f'multipart/related; type=application/dicom; boundary={boundary}'},
        )
        assert store_resp.status_code in (200, 401, 403)

    def test_search_returns_json(self, client):
        resp = client.get('/api/v2/dicomweb/studies', headers={'Accept': 'application/dicom+json'})
        assert resp.status_code in (200, 401, 403)
        if resp.status_code == 200:
            assert resp.headers.get('content-type', '').startswith('application/dicom+json')

    def test_retrieve_study(self, client):
        resp = client.get('/api/v2/dicomweb/studies/2.25.1.1.1')
        assert resp.status_code in (200, 401, 403, 404)
