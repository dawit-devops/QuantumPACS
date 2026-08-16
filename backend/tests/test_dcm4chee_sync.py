"""Tests for the ADR-028 dcm4chee self-heal sync worker (backend/services/dcm4chee_sync.py)."""
import time
from unittest.mock import AsyncMock, Mock, patch

import pytest

from services.dcm4chee_sync import (
    Dcm4cheeSyncer,
    Dcm4cheeSyncClient,
    _PAGE,
    dcm4chee_sync_enabled,
)


def test_disabled_when_proxy_off():
    with patch('services.dcm4chee_sync.proxy_enabled', return_value=False):
        assert dcm4chee_sync_enabled() is False


def test_enabled_when_proxy_on():
    with patch('services.dcm4chee_sync.proxy_enabled', return_value=True):
        assert dcm4chee_sync_enabled() is True


def _conn_stub(rows):
    conn = AsyncMock()
    conn.__aenter__ = AsyncMock(return_value=conn)
    conn.__aexit__ = AsyncMock(return_value=None)
    conn.fetch = AsyncMock(return_value=rows)
    return conn


def _client_stub(uids=None):
    client = AsyncMock(spec=Dcm4cheeSyncClient)
    client.aclose = AsyncMock()
    client.list_study_uids = AsyncMock(return_value=uids or [])
    client.request_export = AsyncMock()
    return client


def _real_client():
    """A Dcm4cheeSyncClient with the httpx client replaced by a mock, so the
    real list_study_uids / request_export logic runs without network."""
    client = Dcm4cheeSyncClient.__new__(Dcm4cheeSyncClient)
    client.rs_base = 'http://arc.test/aets/DCM4CHEE/rs'
    client.dimse_base = 'http://arc.test/aets/DCM4CHEE/dimse'
    client.feed_ae = 'QUANTUMPACS'
    client.client = AsyncMock()
    return client


def _known_row(uid):
    return {'study_instance_uid': uid}


@pytest.mark.anyio
async def test_run_once_returns_none_when_disabled():
    with patch('services.dcm4chee_sync.proxy_enabled', return_value=False):
        assert await Dcm4cheeSyncer().run_once() is None


@pytest.mark.anyio
async def test_run_once_empty_archive_no_ops():
    client = _client_stub(uids=[])
    with patch('services.dcm4chee_sync.proxy_enabled', return_value=True), \
         patch('services.dcm4chee_sync.Dcm4cheeSyncClient', return_value=client):
        stats = await Dcm4cheeSyncer().run_once()
    assert stats == {'exported': 0, 'skipped': 0, 'failed': 0, 'cooldown': 0}
    client.request_export.assert_not_awaited()


@pytest.mark.anyio
async def test_run_once_skips_studies_qp_already_knows():
    client = _client_stub(uids=['1.2.3', '1.2.4'])
    conn = _conn_stub([_known_row('1.2.3'), _known_row('1.2.4')])
    with patch('services.dcm4chee_sync.proxy_enabled', return_value=True), \
         patch('services.dcm4chee_sync.get_conn', return_value=conn), \
         patch('services.dcm4chee_sync.Dcm4cheeSyncClient', return_value=client):
        stats = await Dcm4cheeSyncer().run_once()
    assert stats == {'exported': 0, 'skipped': 2, 'failed': 0, 'cooldown': 0}
    client.request_export.assert_not_awaited()


@pytest.mark.anyio
async def test_run_once_exports_missing_studies():
    client = _client_stub(uids=['1.2.3', '1.2.4', '1.2.5'])
    conn = _conn_stub([_known_row('1.2.4')])  # QP knows only 1.2.4
    with patch('services.dcm4chee_sync.proxy_enabled', return_value=True), \
         patch('services.dcm4chee_sync.get_conn', return_value=conn), \
         patch('services.dcm4chee_sync.Dcm4cheeSyncClient', return_value=client):
        stats = await Dcm4cheeSyncer().run_once()
    assert stats == {'exported': 2, 'skipped': 1, 'failed': 0, 'cooldown': 0}
    assert client.request_export.await_count == 2
    requested = [call.args[0] for call in client.request_export.await_args_list]
    assert requested == ['1.2.3', '1.2.5']


@pytest.mark.anyio
async def test_run_once_export_failure_counts_and_continues():
    client = _client_stub(uids=['1.2.3', '1.2.4'])
    client.request_export = AsyncMock(side_effect=RuntimeError('archive down'))
    conn = _conn_stub([])
    with patch('services.dcm4chee_sync.proxy_enabled', return_value=True), \
         patch('services.dcm4chee_sync.get_conn', return_value=conn), \
         patch('services.dcm4chee_sync.Dcm4cheeSyncClient', return_value=client):
        stats = await Dcm4cheeSyncer().run_once()
    assert stats == {'exported': 0, 'skipped': 0, 'failed': 2, 'cooldown': 0}
    assert client.request_export.await_count == 2


@pytest.mark.anyio
async def test_run_once_cooldown_skips_recently_requested():
    # M1: a study whose export was requested within the cooldown window must
    # not be re-queued — otherwise a dead feed SCP grows the archive export
    # queue by one 202 per cycle, unbounded.
    client = _client_stub(uids=['1.2.3'])
    conn = _conn_stub([])
    with patch('services.dcm4chee_sync.proxy_enabled', return_value=True), \
         patch('services.dcm4chee_sync.get_conn', return_value=conn), \
         patch('services.dcm4chee_sync.Dcm4cheeSyncClient', return_value=client), \
         patch('services.dcm4chee_sync.config', {'dcm4chee_sync_cooldown': '300'}):
        syncer = Dcm4cheeSyncer()
        first = await syncer.run_once()
        second = await syncer.run_once()
    assert first == {'exported': 1, 'skipped': 0, 'failed': 0, 'cooldown': 0}
    assert second == {'exported': 0, 'skipped': 0, 'failed': 0, 'cooldown': 1}
    assert client.request_export.await_count == 1


@pytest.mark.anyio
async def test_run_once_cooldown_expires_after_window():
    # The watermark must expire: once the cooldown passes, a still-unknown
    # study is re-requested (feed SCP may have come back up).
    client = _client_stub(uids=['1.2.3'])
    conn = _conn_stub([])
    with patch('services.dcm4chee_sync.proxy_enabled', return_value=True), \
         patch('services.dcm4chee_sync.get_conn', return_value=conn), \
         patch('services.dcm4chee_sync.Dcm4cheeSyncClient', return_value=client), \
         patch('services.dcm4chee_sync.config', {'dcm4chee_sync_cooldown': '1'}):
        syncer = Dcm4cheeSyncer()
        syncer._last_requested['1.2.3'] = time.time() - 2
        stats = await syncer.run_once()
    assert stats == {'exported': 1, 'skipped': 0, 'failed': 0, 'cooldown': 0}
    assert client.request_export.await_count == 1


@pytest.mark.anyio
async def test_run_once_noop_when_previous_pass_inflight():
    # M3: if the previous pass is still running on the main loop (thread wait
    # timed out at 90 s), the next cycle must not start an overlapping pass.
    syncer = Dcm4cheeSyncer()
    syncer._inflight = True
    with patch('services.dcm4chee_sync.proxy_enabled', return_value=True):
        assert await syncer.run_once() is None


@pytest.mark.anyio
async def test_list_study_uids_paginates_until_short_page():
    client = _real_client()
    first_page = [{'0020000D': {'vr': 'UI', 'Value': [f'1.2.{i}']}} for i in range(_PAGE)]
    short_page = [{'0020000D': {'vr': 'UI', 'Value': ['1.2.999']}}]
    # Plain Mock responses: the worker calls resp.json() synchronously, so
    # AsyncMock responses (whose .json() returns a coroutine) would break it.
    responses = [
        Mock(status_code=200, json=Mock(return_value=first_page), text=''),
        Mock(status_code=200, json=Mock(return_value=short_page), text=''),
    ]
    client.client.get = AsyncMock(side_effect=responses)

    uids = await client.list_study_uids()
    assert len(uids) == _PAGE + 1
    assert uids[-1] == '1.2.999'
    # two pages requested: offset 0 then offset _PAGE
    offsets = [c.kwargs['params']['offset'] for c in client.client.get.await_args_list]
    assert offsets == [0, _PAGE]


@pytest.mark.anyio
async def test_list_study_uids_handles_empty_204():
    # dcm4chee answers 204 No Content (no body) for an empty result set;
    # the worker must treat it as an empty page, not crash on resp.json().
    client = _real_client()
    client.client.get = AsyncMock(
        return_value=Mock(status_code=204, content=b'', text=''),
    )
    uids = await client.list_study_uids()
    assert uids == []


@pytest.mark.anyio
async def test_request_export_posts_dimse_path_with_queue():
    client = _real_client()
    client.client.post = AsyncMock(
        return_value=AsyncMock(status_code=202, text=''),
    )
    with patch('services.dcm4chee_sync.config', {'dcm4chee_ae': 'DCM4CHEE'}):
        await client.request_export('1.2.3')
    url = client.client.post.await_args.args[0]
    assert url.endswith('/aets/DCM4CHEE/dimse/DCM4CHEE/studies/1.2.3/export/dicom:QUANTUMPACS')
    assert client.client.post.await_args.kwargs['params'] == {'queue': 'true'}


@pytest.mark.anyio
async def test_request_export_raises_on_error_status():
    client = _real_client()
    client.client.post = AsyncMock(
        return_value=AsyncMock(status_code=500, text='boom'),
    )
    with pytest.raises(RuntimeError, match='export request failed'):
        await client.request_export('1.2.3')
