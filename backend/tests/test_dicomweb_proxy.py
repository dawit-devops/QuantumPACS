"""Tests for the ADR-028 DICOMweb proxy (backend/api/dicomweb_proxy.py)."""
from unittest.mock import AsyncMock, patch

import pytest
from starlette.routing import Route
from starlette.testclient import TestClient

from api.dicomweb import DicomWebStudies, DicomWebWado, DicomWebWadoUri
from api.dicomweb_proxy import _strip_mount, _archive_path
from tests.conftest import _make_app


def test_strip_mount_v1_and_v2():
    assert _strip_mount('/api/dicomweb/studies') == '/dicomweb/studies'
    assert _strip_mount('/api/v2/dicomweb/studies') == '/dicomweb/studies'
    assert _strip_mount('/api/wado') == '/wado'
    assert _strip_mount('/dicomweb/studies') == '/dicomweb/studies'


@patch('api.dicomweb_proxy.config', {'dcm4chee_url': 'http://arc:8080/dcm4chee-arc', 'dcm4chee_ae': 'DCM4CHEE'})
def test_archive_path_mapping():
    assert _archive_path('/dicomweb/studies', 'DCM4CHEE') == \
        'http://arc:8080/dcm4chee-arc/aets/DCM4CHEE/rs/studies'
    assert _archive_path('/dicomweb/studies/1.2.3/series/4.5.6/instances/7.8.9', 'DCM4CHEE') == \
        'http://arc:8080/dcm4chee-arc/aets/DCM4CHEE/rs/studies/1.2.3/series/4.5.6/instances/7.8.9'
    assert _archive_path('/wado', 'DCM4CHEE') == \
        'http://arc:8080/dcm4chee-arc/aets/DCM4CHEE/wado'


@patch('api.dicomweb_proxy.config', {'dcm4chee_url': 'http://arc:8080/dcm4chee-arc', 'dcm4chee_ae': 'DCM4CHEE'})
def test_archive_path_stow_rs_mapping():
    # Study-scoped STOW-RS lives at /studies/{uid} on the archive (PS3.18
    # §10.5); the QP surface /studies/{uid}/instances must drop the segment.
    assert _archive_path('/dicomweb/studies/1.2.3/instances', 'DCM4CHEE', method='POST') == \
        'http://arc:8080/dcm4chee-arc/aets/DCM4CHEE/rs/studies/1.2.3'
    # Series/instance QIDO paths keep their /instances segment.
    assert _archive_path('/dicomweb/studies/1.2.3/series/4.5.6/instances', 'DCM4CHEE', method='POST') == \
        'http://arc:8080/dcm4chee-arc/aets/DCM4CHEE/rs/studies/1.2.3/series/4.5.6/instances'
    # L1: the rewrite is POST-only — a future GET QIDO-RS
    # /studies/{uid}/instances must NOT be rewritten into a study retrieve.
    assert _archive_path('/dicomweb/studies/1.2.3/instances', 'DCM4CHEE', method='GET') == \
        'http://arc:8080/dcm4chee-arc/aets/DCM4CHEE/rs/studies/1.2.3/instances'


def _fake_upstream(status_code=200, body=b'[{"00080005":{"vr":"CS","Value":["ISO_IR 100"]}}]',
                   content_type='application/dicom+json'):
    class _Headers:
        def __init__(self, mapping):
            self._m = mapping

        def get(self, name, default=None):
            return self._m.get(name.lower(), default)

    class _Resp:
        def __init__(self):
            self.status_code = status_code
            self.headers = _Headers({'content-type': content_type})

        async def aiter_bytes(self):
            yield body

        async def aclose(self):
            return None

    return _Resp()


def _make_proxy_app():
    from api.auth import User
    return _make_app([
        Route('/api/dicomweb/studies', endpoint=DicomWebStudies),
        Route('/api/dicomweb/studies/{study_uid}', endpoint=DicomWebWado),
        Route('/api/wado', endpoint=DicomWebWadoUri),
    ], user=User({'id': 1, 'permissions': ['DICOMWEB_READ']}))


@pytest.mark.anyio
async def test_proxy_forward_without_archive_running():
    """Proxy returns 502 when the archive is unreachable (config off → local path unaffected)."""

    client = TestClient(_make_proxy_app())
    with patch('api.dicomweb_proxy.proxy_enabled', return_value=True), \
         patch('api.dicomweb_proxy.config', {'dcm4chee_url': 'http://127.0.0.1:1/dcm4chee-arc',
                                              'dcm4chee_ae': 'DCM4CHEE',
                                              'dicom_proxy': 'true'}):
        resp = client.get('/api/dicomweb/studies?PatientName=*')
    assert resp.status_code in (502,)
    assert resp.json()['error']['code'] == 'ARCHIVE_UNAVAILABLE'


@pytest.mark.anyio
async def test_proxy_forwards_and_streams_response():
    """With proxy enabled, a QIDO call is forwarded and the upstream body streams back."""

    upstream = _fake_upstream()
    client = TestClient(_make_proxy_app())
    with patch('api.dicomweb_proxy.proxy_enabled', return_value=True), \
         patch('api.dicomweb_proxy.httpx.AsyncClient') as MockClient, \
         patch('api.dicomweb_proxy.config', {'dcm4chee_url': 'http://arc:8080/dcm4chee-arc',
                                              'dcm4chee_ae': 'DCM4CHEE',
                                              'dicom_proxy': 'true'}):
        mock_client = MockClient.return_value
        mock_send = AsyncMock(return_value=upstream)
        mock_client.send = mock_send
        mock_client.aclose = AsyncMock()
        mock_client.build_request = lambda *a, **k: None
        resp = client.get('/api/dicomweb/studies?PatientName=*')
    assert resp.status_code == 200
    assert resp.headers['content-type'] == 'application/dicom+json'
    assert 'ISO_IR 100' in resp.text


@pytest.mark.anyio
async def test_proxy_route_mismatch_404():

    client = TestClient(_make_proxy_app())
    # A path that exists on QP but has no archive equivalent must not crash
    # the local endpoint when proxy is enabled — and _archive_path raises
    # ValueError → 404.
    with patch('api.dicomweb_proxy.proxy_enabled', return_value=True), \
         patch('api.dicomweb_proxy.config', {'dcm4chee_url': 'http://arc:8080/dcm4chee-arc',
                                              'dcm4chee_ae': 'DCM4CHEE',
                                              'dicom_proxy': 'true'}):
        resp = client.get('/api/dicomweb/studies/1.2.3/archive')
    assert resp.status_code == 404