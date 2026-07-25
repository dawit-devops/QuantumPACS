from io import BytesIO
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pydicom
from pydicom.dataset import Dataset, FileMetaDataset
from pydicom.uid import ExplicitVRLittleEndian

from dcm.file import clean, get_meta, parse_dcm


def _make_minimal_dicom():
    ds = Dataset()
    ds.PatientID = 'P001'
    ds.PatientName = 'Test^Patient'
    ds.PatientBirthDate = '20000101'
    ds.PatientSex = 'M'
    ds.StudyID = 'S001'
    ds.StudyDescription = 'Chest X-Ray'
    ds.SeriesNumber = '1'
    ds.Modality = 'CR'
    ds.SeriesDescription = 'AP View'
    ds.SOPClassUID = '1.2.840.10008.5.1.4.1.1.1'
    ds.StudyInstanceUID = '1.2.840.113619.2.55.1.1760426491.1234.1'
    ds.SeriesInstanceUID = '1.2.840.113619.2.55.1.1760426491.1234.2'
    ds.SOPInstanceUID = '1.2.840.113619.2.55.1.1760426491.1234.3'
    ds.AccessionNumber = 'ACC001'
    ds.file_meta = FileMetaDataset()
    ds.file_meta.MediaStorageSOPClassUID = '1.2.840.10008.5.1.4.1.1.1'
    ds.file_meta.MediaStorageSOPInstanceUID = '1.2.3.4.5.6.7.8'
    ds.file_meta.TransferSyntaxUID = ExplicitVRLittleEndian
    return ds


class TestClean:
    def test_clean_strips_whitespace(self):
        assert clean('  hello  ') == 'hello'

    def test_clean_strips_single_quotes(self):
        assert clean("'hello'") == 'hello'

    def test_clean_strips_double_quotes(self):
        assert clean('"hello"') == 'hello'

    def test_clean_strict_replaces_slashes(self):
        assert clean('P/001/2', strict=True) == 'P-001-2'

    def test_clean_strict_no_change_without_slashes(self):
        assert clean('P001', strict=True) == 'P001'

    def test_clean_empty_string(self):
        assert clean('') == ''

    def test_clean_strips_both_quote_types(self):
        assert clean("'\"hello\"'") == 'hello'


class TestGetMeta:
    def test_get_meta_returns_correct_keys(self):
        ds = _make_minimal_dicom()
        meta = get_meta(ds)
        assert meta['patient_id'] == 'P001'
        assert meta['patient_name'] == 'Test^Patient'
        assert meta['patient_birth_date'] == '20000101'
        assert meta['patient_sex'] == 'M'
        assert meta['study_id'] == 'S001'
        assert meta['study_description'] == 'Chest X-Ray'
        assert meta['series_number'] == '1'
        assert meta['modality'] == 'CR'
        assert meta['series_description'] == 'AP View'
        assert meta['study_instance_uid'] == '1.2.840.113619.2.55.1.1760426491.1234.1'
        assert meta['series_instance_uid'] == '1.2.840.113619.2.55.1.1760426491.1234.2'
        assert meta['sop_instance_uid'] == '1.2.840.113619.2.55.1.1760426491.1234.3'
        assert meta['accession_number'] == 'ACC001'

    def test_get_meta_includes_cleaned_dict(self):
        ds = _make_minimal_dicom()
        meta = get_meta(ds)
        assert 'cleaned' in meta
        assert isinstance(meta['cleaned'], dict)
        assert 'Patient\'s Name' in meta['cleaned']

    def test_get_meta_includes_raw_dict(self):
        ds = _make_minimal_dicom()
        meta = get_meta(ds)
        assert 'raw' in meta
        assert isinstance(meta['raw'], dict)

    def test_get_meta_missing_optional_fields(self):
        ds = Dataset()
        ds.PatientID = 'P001'
        ds.StudyID = 'S001'
        ds.SeriesNumber = '1'
        ds.Modality = 'CT'
        ds.file_meta = FileMetaDataset()
        meta = get_meta(ds)
        assert meta['patient_name'] == ''
        assert meta['study_description'] == ''
        assert meta['series_description'] == ''


class TestParseDcm:
    def test_parse_dcm_returns_meta_dict(self):
        ds = _make_minimal_dicom()
        buf = BytesIO()
        ds.save_as(buf, enforce_file_format=True)
        buf.seek(0)
        meta = parse_dcm(buf)
        assert meta['patient_id'] == 'P001'
        assert meta['modality'] == 'CR'

    def test_parse_dcm_handles_file_without_pixel_data(self):
        ds = _make_minimal_dicom()
        buf = BytesIO()
        ds.save_as(buf, enforce_file_format=True)
        buf.seek(0)
        meta = parse_dcm(buf)
        assert meta['patient_id'] == 'P001'

    def test_parse_dcm_raises_on_invalid_data(self):
        buf = BytesIO(b'not a DICOM file')
        with pytest.raises(Exception):
            parse_dcm(buf)

    def test_parse_dcm_with_special_characters(self):
        ds = _make_minimal_dicom()
        ds.PatientName = 'Müller^José'
        buf = BytesIO()
        ds.save_as(buf, enforce_file_format=True)
        buf.seek(0)
        meta = parse_dcm(buf)
        assert meta['patient_name'] == 'Müller^José'


class _AsyncContextMock(AsyncMock):
    async def __aenter__(self):
        return self
    async def __aexit__(self, *args):
        pass

def _make_mock_conn():
    conn = _AsyncContextMock()
    tx = _AsyncContextMock()
    conn.transaction = MagicMock(return_value=tx)
    return conn

class TestStoreHandler:
    @pytest.mark.asyncio
    async def test_store_success(self):
        ds = _make_minimal_dicom()
        data = BytesIO(b'dicom data')

        mock_conn = _make_mock_conn()
        mock_replica_cls = MagicMock()
        mock_replica_cls.return_value.master = AsyncMock(return_value={'id': 1, 'type': 'local', 'location': '/tmp'})
        mock_files_cls = MagicMock()
        mock_files_cls.return_value.insert_or_select = AsyncMock(return_value={'id': 42})

        mock_storage = MagicMock()
        mock_storage.copy = AsyncMock(return_value={'path': '/tmp/file.dcm', 'size': 1024})
        mock_replicafiles_cls = MagicMock()
        mock_replicafiles_cls.return_value.add = AsyncMock()

        with patch('dcm.server.setup', AsyncMock()), \
             patch('dcm.store.Replica', new=mock_replica_cls), \
             patch('dcm.store.Files', new=mock_files_cls), \
             patch('dcm.store.Storage.get', AsyncMock(return_value=mock_storage)), \
             patch('dcm.store.ReplicaFiles', new=mock_replicafiles_cls), \
             patch('dcm.store.hash_file', return_value='abc123'), \
             patch('dcm.store.get_conn') as mock_get_conn:
            mock_get_conn.return_value.__aenter__.return_value = mock_conn

            from dcm.server import store
            result = await store(ds, data)
            assert result is True

    @pytest.mark.asyncio
    async def test_store_no_master_handles_gracefully(self):
        ds = _make_minimal_dicom()
        data = BytesIO(b'dicom data')

        mock_conn = _make_mock_conn()
        mock_replica_cls = MagicMock()
        mock_replica_cls.return_value.master = AsyncMock(return_value=None)

        with patch('dcm.server.setup', AsyncMock()), \
             patch('dcm.store.Replica', new=mock_replica_cls), \
             patch('dcm.store.get_conn') as mock_get_conn:
            mock_get_conn.return_value.__aenter__.return_value = mock_conn

            from dcm.server import store
            result = await store(ds, data)
            assert result is False


class TestStoreInstance:
    @pytest.mark.asyncio
    async def test_store_instance_importable(self):
        from dcm.store import store_instance
        assert callable(store_instance)

    @pytest.mark.asyncio
    async def test_store_instance_success(self):
        ds = _make_minimal_dicom()
        data = BytesIO(b'dicom data')

        mock_conn = _make_mock_conn()
        mock_replica_cls = MagicMock()
        mock_replica_cls.return_value.master = AsyncMock(return_value={'id': 1, 'type': 'local', 'location': '/tmp'})
        mock_files_cls = MagicMock()
        mock_files_cls.return_value.insert_or_select = AsyncMock(return_value={'id': 42})

        mock_storage = MagicMock()
        mock_storage.copy = AsyncMock(return_value={'path': '/tmp/file.dcm', 'size': 1024})
        mock_replicafiles_cls = MagicMock()
        mock_replicafiles_cls.return_value.add = AsyncMock()

        with patch('dcm.store.Replica', new=mock_replica_cls), \
             patch('dcm.store.Files', new=mock_files_cls), \
             patch('dcm.store.Storage.get', AsyncMock(return_value=mock_storage)), \
             patch('dcm.store.ReplicaFiles', new=mock_replicafiles_cls), \
             patch('dcm.store.hash_file', return_value='abc123'), \
             patch('dcm.store.get_conn') as mock_get_conn:
            mock_get_conn.return_value.__aenter__.return_value = mock_conn

            from dcm.store import store_instance
            result = await store_instance(ds, data)
            assert result is True

    @pytest.mark.asyncio
    async def test_store_instance_no_setup_guard(self):
        from dcm.store import store_instance
        import inspect
        source = inspect.getsource(store_instance)
        assert '_initialized' not in source
        assert 'setup()' not in source

    @pytest.mark.asyncio
    async def test_store_instance_calls_worklist_bridge(self):
        ds = _make_minimal_dicom()
        data = BytesIO(b'dicom data')

        mock_conn = _make_mock_conn()
        mock_replica_cls = MagicMock()
        mock_replica_cls.return_value.master = AsyncMock(return_value={'id': 1, 'type': 'local', 'location': '/tmp'})
        mock_files_cls = MagicMock()
        mock_files_cls.return_value.insert_or_select = AsyncMock(return_value={'id': 42})

        mock_storage = MagicMock()
        mock_storage.copy = AsyncMock(return_value={'path': '/tmp/file.dcm', 'size': 1024})
        mock_replicafiles_cls = MagicMock()
        mock_replicafiles_cls.return_value.add = AsyncMock()

        with patch('dcm.store.Replica', new=mock_replica_cls), \
             patch('dcm.store.Files', new=mock_files_cls), \
             patch('dcm.store.Storage.get', AsyncMock(return_value=mock_storage)), \
             patch('dcm.store.ReplicaFiles', new=mock_replicafiles_cls), \
             patch('dcm.store.hash_file', return_value='abc123'), \
             patch('dcm.store.match_worklist_performed', new=AsyncMock()) as mock_match, \
             patch('dcm.store.get_conn') as mock_get_conn:
            mock_get_conn.return_value.__aenter__.return_value = mock_conn

            from dcm.store import store_instance
            await store_instance(ds, data)
            assert mock_match.called

    @pytest.mark.asyncio
    async def test_match_worklist_performed_uses_accession(self):
        from db.worklist import Worklist

        class _FakeAc:
            async def __aenter__(self):
                return self
            async def __aexit__(self, *args):
                pass

        with patch('dcm.store.get_conn') as mock_get_conn:
            mock_get_conn.return_value = _FakeAc()

            mock_entry = {'status': 'scheduled', 'accession_number': 'ACC001'}
            with patch.object(Worklist, 'get_by_accession', new=AsyncMock(return_value=mock_entry)) as mock_get_acc:
                with patch.object(Worklist, 'mark_performed', new=AsyncMock()) as mock_mark:
                    from dcm.store import match_worklist_performed
                    await match_worklist_performed({'accession_number': 'ACC001', 'study_instance_uid': '1.2.3'})
                    mock_get_acc.assert_called_once_with('ACC001')
                    mock_mark.assert_called_once_with('ACC001', '1.2.3')

    @pytest.mark.asyncio
    async def test_match_worklist_no_action_when_no_accession(self):
        from dcm.store import match_worklist_performed
        with patch('db.worklist.Worklist') as mock_wl_cls:
            await match_worklist_performed({'accession_number': '', 'study_instance_uid': '1.2.3'})
            assert not mock_wl_cls.called
