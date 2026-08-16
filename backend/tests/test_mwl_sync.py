"""Tests for the ADR-028 MWL-RS mirror sync worker (backend/api/mwl_sync.py)."""
import json
from unittest.mock import AsyncMock, patch

import pytest

from api.mwl_sync import (
    MwlSyncer,
    MwlSyncClient,
    STATUS_MAP,
    _clean_error,
    _mwl_dataset,
    mwl_sync_enabled,
    mwl_uid,
)


def _row(**overrides):
    base = {
        'id': '11111111-1111-1111-1111-111111111111',
        'patient_id': 'P001',
        'patient_name': 'Doe^John',
        'patient_birth_date': '1980-01-02',
        'patient_sex': 'M',
        'accession_number': 'ACC1',
        'requesting_physician': 'Smith^R',
        'scheduled_station_name': 'CT1',
        'scheduled_procedure_step_id': 'SPS1',
        'protocol_name': 'CT CHEST',
        'scheduled_date': '2026-08-15',
        'scheduled_time': '12:00:00',
        'modality': 'CT',
        'station_ae_title': 'STATION1',
        'study_uid': '',
        'status': 'scheduled',
        'updated_at': None,
        'mwl_synced_at': None,
        'mwl_sync_error': '',
        'tenant_id': 'default',
    }
    base.update(overrides)
    return base


def test_deterministic_uid_is_stable_across_calls():
    row = _row()
    assert mwl_uid(row) == mwl_uid(row)


def test_deterministic_uid_differs_by_patient():
    a = mwl_uid(_row(patient_id='P001'))
    b = mwl_uid(_row(patient_id='P002'))
    assert a != b


def test_dataset_builds_expected_tags():
    row = _row()
    ds = _mwl_dataset(row)
    body = json.loads(ds.to_json())
    # Patient block
    assert body['00100010']['Value'] == [{'Alphabetic': 'Doe^John'}]
    assert body['00100020']['Value'] == ['P001']
    assert body['00100040']['Value'] == ['M']
    # Date normalized YYYYMMDD; time HHMMSS.
    step = body['00400100']['Value'][0]
    assert step['00080060']['Value'] == ['CT']
    assert step['00400002']['Value'] == ['20260815']
    assert step['00400003']['Value'] == ['120000']
    assert step['00400001']['Value'] == ['STATION1']
    assert step['00400009']['Value'] == ['SPS1']
    # Top-level StudyInstanceUID is the deterministic one and is echoed into
    # the SPS step so dcm4chee upserts instead of generating a fresh UID.
    assert body['0020000D']['Value'] == [mwl_uid(row)]
    assert step['0020000D']['Value'] == [mwl_uid(row)]


def test_dataset_omits_empty_optional_fields():
    ds = _mwl_dataset(_row(requesting_physician='', accession_number='',
                            scheduled_station_name='', patient_sex=''))
    body = json.loads(ds.to_json())
    assert '00080050' not in body
    assert '00321032' not in body
    step = body['00400100']['Value'][0]
    assert '00400010' not in step


def test_status_map_values():
    assert STATUS_MAP == {
        'scheduled': 'SCHEDULED',
        'in_progress': 'STARTED',
        'performed': 'COMPLETED',
    }


def test_disabled_when_proxy_off():
    with patch('api.mwl_sync.proxy_enabled', return_value=False):
        assert mwl_sync_enabled() is False


def test_clean_error_caps_and_strips_control():
    assert _clean_error('a' * 500) == 'a' * 240
    assert '\x00' not in _clean_error('a\x00b')


def _make_conn(rows):
    conn = AsyncMock()
    conn.__aenter__ = AsyncMock(return_value=conn)
    conn.__aexit__ = AsyncMock(return_value=None)
    conn.fetch = AsyncMock(return_value=rows)
    conn.execute = AsyncMock(return_value=None)
    return conn


def _client_stub():
    client = AsyncMock(spec=MwlSyncClient)
    client.aclose = AsyncMock()
    client.ensure_patient = AsyncMock()
    client.store = AsyncMock(return_value='1.2.3')
    client.set_status = AsyncMock()
    client.remove = AsyncMock()
    return client


@pytest.mark.anyio
async def test_run_once_returns_none_when_disabled():
    with patch('api.mwl_sync.proxy_enabled', return_value=False):
        assert await MwlSyncer().run_once() is None


@pytest.mark.anyio
async def test_run_once_scheduled_pushes_patient_and_mwlitem():
    row = _row(status='scheduled', mwl_synced_at=None)
    conn = _make_conn([row])
    client = _client_stub()
    with patch('api.mwl_sync.proxy_enabled', return_value=True), \
         patch('api.mwl_sync.get_conn', return_value=conn), \
         patch('api.mwl_sync.MwlSyncClient', return_value=client):
        stats = await MwlSyncer().run_once()
    assert stats == {'pushed': 1, 'status': 0, 'removed': 0, 'failed': 0}
    client.ensure_patient.assert_awaited_once()
    client.store.assert_awaited_once()
    client.set_status.assert_not_awaited()
    client.remove.assert_not_awaited()
    # success path marks the row synced and clears the error.
    assert conn.execute.await_count == 1
    args = conn.execute.await_args
    assert 'mwl_synced_at = now()' in args[0][0]
    assert args[0][1] == row['id']


@pytest.mark.anyio
async def test_run_once_in_progress_sets_started():
    row = _row(status='in_progress', mwl_synced_at='2026-08-01T00:00:00+00:00')
    conn = _make_conn([row])
    client = _client_stub()
    with patch('api.mwl_sync.proxy_enabled', return_value=True), \
         patch('api.mwl_sync.get_conn', return_value=conn), \
         patch('api.mwl_sync.MwlSyncClient', return_value=client):
        stats = await MwlSyncer().run_once()
    assert stats == {'pushed': 0, 'status': 1, 'removed': 0, 'failed': 0}
    client.store.assert_not_awaited()
    client.set_status.assert_awaited_once()
    assert client.set_status.await_args.args[1] == 'STARTED'


@pytest.mark.anyio
async def test_run_once_performed_sets_completed():
    row = _row(status='performed', mwl_synced_at='2026-08-01T00:00:00+00:00')
    conn = _make_conn([row])
    client = _client_stub()
    with patch('api.mwl_sync.proxy_enabled', return_value=True), \
         patch('api.mwl_sync.get_conn', return_value=conn), \
         patch('api.mwl_sync.MwlSyncClient', return_value=client):
        stats = await MwlSyncer().run_once()
    assert stats['status'] == 1
    client.set_status.assert_awaited_once()
    assert client.set_status.await_args.args[1] == 'COMPLETED'


@pytest.mark.anyio
async def test_run_once_cancelled_removes_without_patient():
    row = _row(status='cancelled', mwl_synced_at='2026-08-01T00:00:00+00:00')
    conn = _make_conn([row])
    client = _client_stub()
    with patch('api.mwl_sync.proxy_enabled', return_value=True), \
         patch('api.mwl_sync.get_conn', return_value=conn), \
         patch('api.mwl_sync.MwlSyncClient', return_value=client):
        stats = await MwlSyncer().run_once()
    assert stats == {'pushed': 0, 'status': 0, 'removed': 1, 'failed': 0}
    client.remove.assert_awaited_once()
    client.ensure_patient.assert_not_awaited()
    client.store.assert_not_awaited()


@pytest.mark.anyio
async def test_run_once_failure_records_error_and_skips_synced_at():
    row = _row(status='scheduled')
    conn = _make_conn([row])
    client = _client_stub()
    client.store = AsyncMock(side_effect=RuntimeError('archive down'))
    with patch('api.mwl_sync.proxy_enabled', return_value=True), \
         patch('api.mwl_sync.get_conn', return_value=conn), \
         patch('api.mwl_sync.MwlSyncClient', return_value=client):
        stats = await MwlSyncer().run_once()
    assert stats == {'pushed': 0, 'status': 0, 'removed': 0, 'failed': 1}
    args = conn.execute.await_args
    assert 'mwl_sync_error = $1' in args[0][0]
    assert 'archive down' in args[0][1]
    assert args[0][2] == row['id']


@pytest.mark.anyio
async def test_run_once_scheduled_repush_updates_full_payload():
    # Already synced scheduled row: ADR mandates a full-payload POST refresh.
    row = _row(status='scheduled', mwl_synced_at='2026-08-01T00:00:00+00:00')
    conn = _make_conn([row])
    client = _client_stub()
    with patch('api.mwl_sync.proxy_enabled', return_value=True), \
         patch('api.mwl_sync.get_conn', return_value=conn), \
         patch('api.mwl_sync.MwlSyncClient', return_value=client):
        stats = await MwlSyncer().run_once()
    assert stats == {'pushed': 1, 'status': 0, 'removed': 0, 'failed': 0}
    client.store.assert_awaited_once()
    client.set_status.assert_not_awaited()
