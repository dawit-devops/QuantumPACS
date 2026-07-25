from io import BytesIO
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydicom.dataset import Dataset, FileDataset, FileMetaDataset
from pydicom.uid import ExplicitVRLittleEndian, generate_uid

from dcm.file import get_meta, parse_dcm
from dcm.dicom_json import row_to_study_json, row_to_series_json, row_to_instance_json





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

        with patch('dcm.store.get_conn') as mock_get_conn:
            mock_get_conn.return_value.__aenter__.return_value = mock_conn
            mock_get_conn.return_value.__aexit__ = AsyncMock(return_value=None)

            with patch('dcm.store.Replica') as mock_replica_cls:
                mock_replica = AsyncMock()
                mock_replica.master = AsyncMock(return_value={'id': 1, 'type': 'local', 'location': '/data/files', 'master': True, 'delay': 0, 'status': 'ok', 'total': 100, 'meta': '{}'})
                mock_replica_cls.return_value = mock_replica

                with patch('dcm.store.Files') as mock_files_cls:
                    mock_files = MagicMock()
                    mock_files.insert_or_select = AsyncMock(return_value={'id': 42})
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
    async def test_match_worklist_performed_skips_without_accession(self):
        from dcm.store import match_worklist_performed
        meta = {'patient_id': 'P001', 'study_instance_uid': '1.2.3.4.5.6'}
        result = await match_worklist_performed(meta)
        assert result is None

    @pytest.mark.asyncio
    async def test_match_worklist_performed_calls_mark_performed(self):
        mock_conn = MagicMock()
        mock_conn.fetchrow = AsyncMock(return_value={
            'id': 'uuid-1', 'accession_number': 'ACC001', 'status': 'scheduled',
        })
        mock_conn.execute = AsyncMock()

        with patch('dcm.store.get_conn') as mock_get_conn:
            mock_get_conn.return_value.__aenter__.return_value = mock_conn
            mock_get_conn.return_value.__aexit__ = AsyncMock(return_value=None)

            from dcm.store import match_worklist_performed
            await match_worklist_performed({
                'accession_number': 'ACC001',
                'study_instance_uid': '1.2.3.4.5.6',
            })

        assert mock_conn.execute.called
