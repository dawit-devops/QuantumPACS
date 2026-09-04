from io import BytesIO
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydicom.dataset import Dataset, FileDataset, FileMetaDataset
from pydicom.uid import ExplicitVRLittleEndian, generate_uid

from dcm.file import get_meta, parse_dcm
from dcm.dicom_json import row_to_study_json, row_to_series_json, row_to_instance_json


class _TxContext:
    async def __aenter__(self):
        return self
    async def __aexit__(self, *args):
        pass


class _FakeAc:
    async def __aenter__(self):
        return self
    async def __aexit__(self, *args):
        return False


def _make_fake_database():
    """Fake the main-pool singleton for store_instance's control-plane reads.

    A plain class is required: Python 3.14's mock machinery force-replaces
    __aenter__/__aexit__ on AsyncMock subclasses with child-mock descriptors,
    so `async with` would yield an object whose transaction() is a bare
    coroutine.
    """
    conn = _FakeAc()
    conn.fetchrow = AsyncMock(return_value=None)
    conn.fetch = AsyncMock(return_value=[])
    conn.execute = AsyncMock()
    conn.add = AsyncMock()
    conn.transaction = MagicMock(return_value=_FakeAc())
    db = MagicMock()
    db.acquire = MagicMock(return_value=conn)
    return db





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
    ds.AccessionNumber = 'ACC001'
    file_meta = FileMetaDataset()
    file_meta.MediaStorageSOPClassUID = '1.2.840.10008.5.1.4.1.1.2'
    file_meta.MediaStorageSOPInstanceUID = sop_uid
    file_meta.TransferSyntaxUID = ExplicitVRLittleEndian
    fd = FileDataset('test.dcm', {}, file_meta=file_meta, preamble=b'\0' * 128)
    for attr in ('PatientName', 'PatientID', 'StudyInstanceUID', 'SeriesInstanceUID', 'SOPInstanceUID', 'Modality', 'StudyDate', 'AccessionNumber'):
        setattr(fd, attr, getattr(ds, attr))
    buf = BytesIO()
    fd.save_as(buf, enforce_file_format=False)
    return buf, fd


class TestDicomCoreStoreIntegration:
    @pytest.mark.asyncio
    async def test_store_instance_success(self):
        buf, ds = _make_mini_dicom()
        buf.seek(0)

        mock_conn = MagicMock()
        mock_conn.transaction.return_value.__aenter__ = AsyncMock()
        mock_conn.transaction.return_value.__aexit__ = AsyncMock(return_value=None)
        # The auto-handoff bridge (services/reading_handoff) runs inside
        # store_instance and issues its own reads/writes on the same conn.
        mock_conn.fetchrow = AsyncMock(return_value=None)
        mock_conn.fetchval = AsyncMock(return_value=None)
        mock_conn.execute = AsyncMock(return_value='UPDATE 0')

        with patch('dcm.store.get_conn') as mock_get_conn, \
             patch('dcm.store.get_database', return_value=_make_fake_database()):
            mock_get_conn.return_value.__aenter__.return_value = mock_conn
            mock_get_conn.return_value.__aexit__ = AsyncMock(return_value=None)

            with patch('dcm.store.Replica') as mock_replica_cls:
                mock_replica = AsyncMock()
                mock_replica.master = AsyncMock(return_value={'id': 1, 'type': 'local', 'location': '/data/files', 'master': True, 'delay': 0, 'status': 'ok', 'total': 100, 'meta': '{}'})
                mock_replica_cls.return_value = mock_replica

                with patch('dcm.store.Files') as mock_files_cls:
                    mock_files = MagicMock()
                    mock_files.insert_or_select = AsyncMock(return_value={'id': 42})
                    mock_files.get_by_sop_uid = AsyncMock(return_value=None)
                    mock_files.get_by_hash = AsyncMock(return_value=None)
                    mock_files_cls.return_value = mock_files

                    with patch('dcm.store.Storage') as mock_storage_cls:
                        mock_storage = MagicMock()
                        mock_storage.copy = AsyncMock(return_value={'location': '/data/files/test.dcm', 'replica_meta': '{}'})
                        mock_storage_cls.get = AsyncMock(return_value=mock_storage)

                        with patch('dcm.store.ReplicaFiles') as mock_rf_cls:
                            mock_rf = MagicMock()
                            mock_rf.add = AsyncMock()
                            mock_rf_cls.return_value = mock_rf

                            from dcm.store import store_instance
                            result = await store_instance(ds, buf)

        assert result is True

    @pytest.mark.asyncio
    async def test_store_instance_failure_returns_false(self):
        buf, ds = _make_mini_dicom()
        buf.seek(0)

        mock_conn = MagicMock()
        mock_conn.transaction.return_value.__aenter__ = AsyncMock(side_effect=Exception('DB error'))
        mock_conn.transaction.return_value.__aexit__ = AsyncMock(return_value=None)

        with patch('dcm.store.get_conn') as mock_get_conn:
            mock_get_conn.return_value.__aenter__.return_value = mock_conn
            mock_get_conn.return_value.__aexit__ = AsyncMock(return_value=None)

            with patch('dcm.store.Replica') as mock_replica_cls:
                mock_replica = AsyncMock()
                mock_replica.master = AsyncMock(return_value={'id': 1})
                mock_replica_cls.return_value = mock_replica

                with patch('dcm.store.Files') as mock_files_cls:
                    mock_files = MagicMock()
                    mock_files.insert_or_select = AsyncMock(return_value={'id': 42})
                    mock_files.get_by_sop_uid = AsyncMock(return_value=None)
                    mock_files_cls.return_value = mock_files

                    with patch('dcm.store.Log') as mock_log_cls:
                        mock_log = MagicMock()
                        mock_log.add = AsyncMock()
                        mock_log_cls.return_value = mock_log

                        from dcm.store import store_instance
                        result = await store_instance(ds, buf)

        assert result is False


class TestDicomCoreUidExtraction:
    def test_get_meta_extracts_all_uids(self):
        buf, ds = _make_mini_dicom()
        meta = get_meta(ds)
        assert meta['patient_id'] == 'P001'
        assert meta['study_instance_uid'] == '1.2.3.4.5.6'
        assert meta['series_instance_uid'] == '1.2.3.4.5.6.7'
        assert meta['sop_instance_uid'] == ds.SOPInstanceUID
        assert meta['accession_number'] == 'ACC001'

    def test_parse_dcm_from_bytes(self):
        buf, ds = _make_mini_dicom()
        buf.seek(0)
        meta = parse_dcm(buf)
        assert meta['study_instance_uid'] == '1.2.3.4.5.6'
        assert meta['series_instance_uid'] == '1.2.3.4.5.6.7'
        assert meta['sop_instance_uid'] == ds.SOPInstanceUID
        assert meta['accession_number'] == 'ACC001'


class TestDicomJsonSerialization:
    def test_row_to_study_json(self):
        row = {
            'patient_id': 'P001',
            'patient_name': 'Test^Patient',
            'patient_birth_date': '19800101',
            'patient_sex': 'M',
            'study_db_id': 1,
            'study_id': 'ST1',
            'study_description': 'Chest CT',
            'study_instance_uid': '1.2.3.4.5.6',
            'accession_number': 'ACC001',
        }
        result = row_to_study_json(row)
        assert result['00100020']['Value'][0] == 'P001'
        assert result['0020000D']['Value'][0] == '1.2.3.4.5.6'
        assert result['00080050']['Value'][0] == 'ACC001'

    def test_row_to_series_json(self):
        row = {
            'series_number': '1',
            'modality': 'CT',
            'series_description': 'Chest',
            'series_instance_uid': '1.2.3.4.5.6.7',
        }
        result = row_to_series_json(row)
        assert result['0020000E']['Value'][0] == '1.2.3.4.5.6.7'
        assert result['00080060']['Value'][0] == 'CT'

    def test_row_to_instance_json(self):
        row = {
            'sop_instance_uid': '1.2.3.4.5.6.7.8',
            'sop_class_uid': '1.2.840.10008.5.1.4.1.1.2',
            'instance_number': '1',
        }
        result = row_to_instance_json(row)
        assert result['00080018']['Value'][0] == '1.2.3.4.5.6.7.8'
        assert result['00080016']['Value'][0] == '1.2.840.10008.5.1.4.1.1.2'


class TestDicomCoreWorklistMatch:
    @pytest.mark.asyncio
    async def test_match_worklist_in_progress_skips_without_accession(self):
        from dcm.store import match_worklist_in_progress
        meta = {'patient_id': 'P001', 'study_instance_uid': '1.2.3.4.5.6'}
        result = await match_worklist_in_progress(meta)
        assert result is None

    @pytest.mark.asyncio
    async def test_match_worklist_in_progress_calls_mark_in_progress(self):
        mock_conn = MagicMock()
        mock_conn.fetchrow = AsyncMock(return_value={
            'id': 'uuid-1', 'accession_number': 'ACC001', 'status': 'scheduled',
        })
        mock_conn.execute = AsyncMock()

        with patch('dcm.store.get_conn') as mock_get_conn:
            mock_get_conn.return_value.__aenter__.return_value = mock_conn
            mock_get_conn.return_value.__aexit__ = AsyncMock(return_value=None)

            from dcm.store import match_worklist_in_progress
            await match_worklist_in_progress({
                'accession_number': 'ACC001',
                'study_instance_uid': '1.2.3.4.5.6',
            })

        assert mock_conn.execute.called


class TestPhase3Pipeline:
    @pytest.mark.asyncio
    async def test_full_store_with_dedup_and_routing(self):
        buf, ds = _make_mini_dicom()
        buf.seek(0)

        mock_conn = MagicMock()
        mock_tx = _TxContext()
        mock_conn.transaction = MagicMock(return_value=mock_tx)
        # The auto-handoff bridge (services/reading_handoff) runs inside
        # store_instance and issues its own reads/writes on the same conn.
        mock_conn.fetchrow = AsyncMock(return_value=None)
        mock_conn.fetchval = AsyncMock(return_value=None)
        mock_conn.execute = AsyncMock(return_value='UPDATE 0')

        mock_replica = AsyncMock()
        mock_replica.master = AsyncMock(return_value={'id': 1, 'type': 'local', 'location': '/data'})
        mock_replica.get = AsyncMock(return_value={'id': 2, 'type': 'remote', 'location': '/remote'})

        with patch('dcm.store.get_conn') as mock_get_conn, \
             patch('dcm.store.get_database', return_value=_make_fake_database()):
            mock_get_conn.return_value.__aenter__.return_value = mock_conn
            mock_get_conn.return_value.__aexit__ = AsyncMock(return_value=None)

            with patch('dcm.store.Replica') as mock_replica_cls:
                mock_replica_cls.return_value = mock_replica

                with patch('dcm.store.Files') as mock_files_cls:
                    mock_files = MagicMock()
                    mock_files.get_by_hash = AsyncMock(return_value=None)
                    mock_files.get_by_sop_uid = AsyncMock(return_value=None)
                    mock_files.insert_or_select = AsyncMock(return_value={'id': 42})
                    mock_files_cls.return_value = mock_files

                    with patch('dcm.store.Storage') as mock_storage_cls:
                        mock_storage = MagicMock()
                        mock_storage.copy = AsyncMock(return_value={'path': '/data/test.dcm', 'size': 1024})
                        mock_storage_cls.get = AsyncMock(return_value=mock_storage)

                        with patch('dcm.store.ReplicaFiles') as mock_rf_cls:
                            mock_rf = MagicMock()
                            mock_rf.add = AsyncMock()
                            mock_rf_cls.return_value = mock_rf

                            with patch('dcm.store.evaluate_routing_rules',
                                       new=AsyncMock(return_value=[
                                           {'rule_id': '1', 'rule_name': 'Test', 'destination': '2'},
                                       ])):
                                from dcm.store import store_instance
                                result = await store_instance(ds, buf)

        assert result is True
        assert mock_files.get_by_sop_uid.called
        assert mock_files.insert_or_select.called
        assert mock_storage.copy.call_count == 2
        assert mock_rf.add.call_count == 2
