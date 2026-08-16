"""Tests for the ADR-028 Weasis launch endpoint (backend/api/weasis.py)."""
from unittest.mock import AsyncMock, Mock, patch

import pytest
from starlette.routing import Route
from starlette.testclient import TestClient

from api.auth import User
from api.weasis import WeasisLaunch, WeasisStatus, _launch_url
from tests.conftest import _make_app


def test_launch_url_single_study():
    assert _launch_url(['1.2.3']) == \
        'http://localhost:8082/weasis-pacs-connector/weasis?studyUID=1.2.3&cdb'


def test_launch_url_patient():
    assert _launch_url([], patient_id='P001') == \
        'http://localhost:8082/weasis-pacs-connector/weasis?patientID=P001&cdb'


def test_launch_url_multi_study_and_custom_base():
    with patch('api.weasis.config', {'weasis_launch_url': 'http://arc:8082/wpc'}):
        assert _launch_url(['1.2.3', '4.5.6']) == \
            'http://arc:8082/wpc/weasis?studyUID=1.2.3&studyUID=4.5.6&cdb'


def _make_client():
    return TestClient(_make_app(
        [Route('/api/weasis/launch', endpoint=WeasisLaunch)],
        user=User({'id': 1, 'permissions': ['DICOMWEB_READ']}),
    ))


@pytest.mark.anyio
async def test_launch_disabled_when_flag_off():
    client = _make_client()
    with patch('api.weasis.config', {'weasis_enabled': 'false'}):
        resp = client.get('/api/weasis/launch?studyUID=1.2.3')
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_launch_requires_study_or_patient():
    client = _make_client()
    with patch('api.weasis.config', {'weasis_enabled': 'true'}):
        resp = client.get('/api/weasis/launch')
    assert resp.status_code == 400


@pytest.mark.anyio
async def test_launch_authorizes_against_files_table():
    client = _make_client()
    with patch('api.weasis.config', {'weasis_enabled': 'true',
                                     'weasis_launch_url': 'http://arc:8082/wpc'}), \
         patch('api.weasis.get_conn') as mock_conn:
        conn = AsyncMock()
        conn.__aenter__.return_value = conn
        conn.fetchval.return_value = True
        mock_conn.return_value = conn

        resp = client.get('/api/weasis/launch?studyUID=1.2.3', follow_redirects=False)

    assert resp.status_code == 302
    assert resp.headers['location'] == 'http://arc:8082/wpc/weasis?studyUID=1.2.3&cdb'
    conn.fetchval.assert_awaited_once()


@pytest.mark.anyio
async def test_launch_study_not_found():
    client = _make_client()
    with patch('api.weasis.config', {'weasis_enabled': 'true'}), \
         patch('api.weasis.get_conn') as mock_conn:
        conn = AsyncMock()
        conn.__aenter__.return_value = conn
        conn.fetchval.return_value = False
        mock_conn.return_value = conn

        resp = client.get('/api/weasis/launch?studyUID=1.2.3')

    assert resp.status_code == 404


def _archive_client_stub(resp=None, exc=None):
    """httpx.AsyncClient context stub whose get() answers QIDO-RS."""
    client = AsyncMock()
    if exc is not None:
        client.get = AsyncMock(side_effect=exc)
    else:
        client.get = AsyncMock(return_value=resp)
    ctx = AsyncMock()
    ctx.__aenter__ = AsyncMock(return_value=client)
    ctx.__aexit__ = AsyncMock(return_value=None)
    return ctx


def _study_json():
    return Mock(status_code=200, content=b'[{"0020000D": {"vr": "UI", "Value": ["1.2.3"]}}]',
                json=Mock(return_value=[{'0020000D': {'vr': 'UI', 'Value': ['1.2.3']}}]))


@pytest.mark.anyio
async def test_launch_authorizes_against_archive_in_proxy_mode():
    # M2: with dicom_proxy=true the archive is the store of truth — a fresh
    # archive-only study must launch without waiting for the self-heal sync
    # to import it into the QP files table.
    client = _make_client()
    ctx = _archive_client_stub(_study_json())
    with patch('api.weasis.config', {'weasis_enabled': 'true',
                                     'dicom_proxy': 'true',
                                     'weasis_launch_url': 'http://arc:8082/wpc'}), \
         patch('api.dicomweb_proxy.config', {'dicom_proxy': 'true'}), \
         patch('api.weasis.httpx.AsyncClient', return_value=ctx):
        resp = client.get('/api/weasis/launch?studyUID=1.2.3', follow_redirects=False)
    assert resp.status_code == 302
    assert resp.headers['location'] == 'http://arc:8082/wpc/weasis?studyUID=1.2.3&cdb'
    url = ctx.__aenter__.return_value.get.await_args.args[0]
    assert url.endswith('/aets/DCM4CHEE/rs/studies')
    assert ctx.__aenter__.return_value.get.await_args.kwargs['params'] == {'0020000D': '1.2.3', 'limit': '1'}


@pytest.mark.anyio
async def test_launch_proxy_mode_study_missing_in_archive():
    client = _make_client()
    empty = Mock(status_code=200, content=b'[]', json=Mock(return_value=[]))
    ctx = _archive_client_stub(empty)
    with patch('api.weasis.config', {'weasis_enabled': 'true', 'dicom_proxy': 'true'}), \
         patch('api.dicomweb_proxy.config', {'dicom_proxy': 'true'}), \
         patch('api.weasis.httpx.AsyncClient', return_value=ctx):
        resp = client.get('/api/weasis/launch?studyUID=1.2.3')
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_launch_proxy_mode_archive_unreachable_fails_closed():
    import httpx
    client = _make_client()
    ctx = _archive_client_stub(exc=httpx.ConnectError('archive down'))
    with patch('api.weasis.config', {'weasis_enabled': 'true', 'dicom_proxy': 'true'}), \
         patch('api.dicomweb_proxy.config', {'dicom_proxy': 'true'}), \
         patch('api.weasis.httpx.AsyncClient', return_value=ctx):
        resp = client.get('/api/weasis/launch?studyUID=1.2.3')
    assert resp.status_code == 404


def _make_status_client():
    return TestClient(_make_app(
        [Route('/api/weasis/status', endpoint=WeasisStatus)],
        user=User({'id': 1, 'permissions': ['DICOMWEB_READ']}),
    ))


@pytest.mark.anyio
async def test_status_reports_enabled():
    client = _make_status_client()
    with patch('api.weasis.config',
               {'weasis_enabled': 'true',
                'weasis_launch_url': 'http://arc:8082/wpc'}):
        resp = client.get('/api/weasis/status')
    assert resp.status_code == 200
    assert resp.json() == {'enabled': True,
                           'launch_url': 'http://arc:8082/wpc'}


@pytest.mark.anyio
async def test_status_reports_disabled():
    client = _make_status_client()
    with patch('api.weasis.config', {'weasis_enabled': 'false'}):
        resp = client.get('/api/weasis/status')
    assert resp.status_code == 200
    assert resp.json() == {'enabled': False,
                           'launch_url': ''}