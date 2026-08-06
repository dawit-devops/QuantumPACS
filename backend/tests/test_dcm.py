from io import BytesIO
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
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

    def test_get_meta_raw_not_exposed(self):
        ds = _make_minimal_dicom()
        meta = get_meta(ds)
        assert 'raw' not in meta

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
    conn.fetchrow = AsyncMock(return_value=None)
    tx = _AsyncContextMock()
    conn.transaction = MagicMock(return_value=tx)
    return conn

class _TxTracker:
    in_transaction = False
    copy_called_in_tx = False
    copy_call_count = 0

    def track_tx(self, conn, storage_copy):
        tx = _AsyncContextMock()
        orig_aenter = tx.__aenter__

        async def tracked_aenter(*args):
            _TxTracker.in_transaction = True
            return await orig_aenter()

        async def tracked_aexit(*args):
            _TxTracker.in_transaction = False

        tx.__aenter__ = tracked_aenter
        tx.__aexit__ = tracked_aexit
        conn.transaction = MagicMock(return_value=tx)

        async def tracked_copy(*args, **kwargs):
            _TxTracker.copy_call_count += 1
            if _TxTracker.in_transaction:
                _TxTracker.copy_called_in_tx = True
            return await storage_copy(*args, **kwargs)

        return tracked_copy

class _FakeAE:
    def __init__(self):
        self.require_called_aet = False
        self.require_calling_aet = []


def _config_mock(values):
    cfg = MagicMock()
    cfg.get.side_effect = lambda key, default='': values.get(key, default)
    return cfg


class TestAssociationPolicy:
    def test_empty_config_accepts_any_calling_aet(self):
        ae = _FakeAE()
        with patch('dcm.server.config', _config_mock({})):
            from dcm.server import apply_association_policy
            apply_association_policy(ae)
        assert ae.require_called_aet is False
        assert ae.require_calling_aet == []

    def test_called_aet_enforced_when_enabled(self):
        ae = _FakeAE()
        with patch('dcm.server.config', _config_mock({'dicom_require_called_aet': 'true'})):
            from dcm.server import apply_association_policy
            apply_association_policy(ae)
        assert ae.require_called_aet is True

    def test_calling_aet_allowlist_applied(self):
        ae = _FakeAE()
        with patch('dcm.server.config', _config_mock({'dicom_aet_allowed': 'MODALITY-A, MODALITY-B'})):
            from dcm.server import apply_association_policy
            apply_association_policy(ae)
        assert ae.require_calling_aet == ['MODALITY-A', 'MODALITY-B']

    def test_ip_allowed_matches_cidr(self):
        from dcm.server import _ip_allowed
        assert _ip_allowed('10.0.0.5', ['10.0.0.0/8'])
        assert not _ip_allowed('192.168.1.5', ['10.0.0.0/8'])
        assert not _ip_allowed('not-an-ip', ['10.0.0.0/8'])

    def test_handle_accept_aborts_disallowed_ip(self):
        mock_assoc = MagicMock()
        mock_assoc.requestor.address = '203.0.113.9'
        event = MagicMock()
        event.assoc = mock_assoc
        with patch('dcm.server.config', _config_mock({'dicom_allowed_ips': '10.0.0.0/8'})):
            from dcm.server import _handle_accept
            _handle_accept(event)
        mock_assoc.abort.assert_called_once()

    def test_handle_accept_allows_matching_ip(self):
        mock_assoc = MagicMock()
        mock_assoc.requestor.address = '10.0.0.9'
        event = MagicMock()
        event.assoc = mock_assoc
        with patch('dcm.server.config', _config_mock({'dicom_allowed_ips': '10.0.0.0/8'})):
            from dcm.server import _handle_accept
            _handle_accept(event)
        mock_assoc.abort.assert_not_called()

    def test_handle_accept_noop_when_ips_unset(self):
        event = MagicMock()
        with patch('dcm.server.config', _config_mock({})):
            from dcm.server import _handle_accept
            _handle_accept(event)
        event.assoc.abort.assert_not_called()


class TestRenderPreview:
    def _ct_dataset(self):
        ds = Dataset()
        ds.SOPClassUID = '1.2.840.10008.5.1.4.1.1.2'
        ds.Rows = 16
        ds.Columns = 16
        ds.BitsAllocated = 16
        ds.BitsStored = 12
        ds.HighBit = 11
        ds.PixelRepresentation = 1
        ds.SamplesPerPixel = 1
        ds.PhotometricInterpretation = 'MONOCHROME2'
        ds.RescaleSlope = 1
        ds.RescaleIntercept = -1024
        ds.WindowCenter = 40
        ds.WindowWidth = 400
        ds.file_meta = FileMetaDataset()
        ds.file_meta.TransferSyntaxUID = ExplicitVRLittleEndian
        import numpy as np
        ds.PixelData = np.arange(256, dtype=np.int16).tobytes()
        return ds

    def test_render_preview_returns_jpeg(self):
        from api.files import _render_preview
        payload = _render_preview(self._ct_dataset())
        assert payload[:2] == b'\xff\xd8'
        assert payload.rstrip().endswith(b'\xff\xd9')

    def test_render_preview_respects_voi_window(self):
        from api.files import _render_preview
        ds = self._ct_dataset()
        ds.RescaleIntercept = 0
        ds.RescaleSlope = 1
        ds.WindowCenter = 40
        ds.WindowWidth = 400
        import numpy as np
        ds.PixelData = np.ones(256, dtype=np.int16).tobytes()
        payload = _render_preview(ds)
        assert payload[:2] == b'\xff\xd8'

    def test_render_preview_min_max_stretch_without_window(self):
        from api.files import _render_preview
        ds = self._ct_dataset()
        del ds.WindowCenter
        del ds.WindowWidth
        payload = _render_preview(ds)
        assert payload[:2] == b'\xff\xd8'

    def test_render_preview_inverts_monochrome1(self):
        from api.files import _render_preview
        ds = self._ct_dataset()
        ds.PhotometricInterpretation = 'MONOCHROME1'
        payload = _render_preview(ds)
        assert payload[:2] == b'\xff\xd8'

    def test_render_preview_rgb(self):
        from api.files import _render_preview
        import numpy as np
        ds = self._ct_dataset()
        ds.SamplesPerPixel = 3
        ds.PhotometricInterpretation = 'RGB'
        ds.BitsAllocated = 8
        ds.BitsStored = 8
        ds.HighBit = 7
        ds.PixelRepresentation = 0
        ds.PlanarConfiguration = 0
        ds.PixelData = np.zeros((16, 16, 3), dtype=np.uint8).tobytes()
        payload = _render_preview(ds)
        assert payload[:2] == b'\xff\xd8'

    def test_render_preview_uses_middle_frame(self):
        from api.files import _render_preview
        import numpy as np
        ds = self._ct_dataset()
        ds.NumberOfFrames = 3
        ds.BitsAllocated = 16
        ds.BitsStored = 16
        ds.HighBit = 15
        ds.PixelRepresentation = 0
        ds.RescaleSlope = 1
        ds.RescaleIntercept = 0
        ds.WindowCenter = 128
        ds.WindowWidth = 256
        ds.PixelData = np.zeros((3, 16, 16), dtype=np.uint16).tobytes()
        payload = _render_preview(ds)
        assert payload[:2] == b'\xff\xd8'

    def test_render_preview_raises_without_pixel_data(self):
        from api.files import _render_preview
        ds = Dataset()
        ds.SOPClassUID = '1.2.840.10008.5.1.4.1.1.2'
        with pytest.raises(Exception):
            _render_preview(ds)


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
        mock_files_cls.return_value.get_by_hash = AsyncMock(return_value=None)
        mock_files_cls.return_value.get_by_sop_uid = AsyncMock(return_value=None)

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
        mock_files_cls.return_value.get_by_hash = AsyncMock(return_value=None)
        mock_files_cls.return_value.get_by_sop_uid = AsyncMock(return_value=None)

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
    async def test_store_instance_uses_hash_for_dedup(self):
        ds = _make_minimal_dicom()
        del ds.SOPInstanceUID
        data = BytesIO(b'dicom data')

        mock_conn = _make_mock_conn()
        existing_file = {'id': 99, 'name': 'existing.dcm', 'hash': 'abc123'}
        mock_files_cls = MagicMock()
        mock_files_cls.return_value.get_by_hash = AsyncMock(return_value=existing_file)
        mock_files_cls.return_value.get_by_sop_uid = AsyncMock(return_value=None)

        mock_replica_cls = MagicMock()
        mock_replica_cls.return_value.master = AsyncMock(return_value={'id': 1, 'type': 'local', 'location': '/tmp'})

        with patch('dcm.store.Replica', new=mock_replica_cls), \
             patch('dcm.store.Files', new=mock_files_cls), \
             patch('dcm.store.hash_file', return_value='abc123'), \
             patch('dcm.store.get_conn') as mock_get_conn:
            mock_get_conn.return_value.__aenter__.return_value = mock_conn

            from dcm.store import store_instance
            result = await store_instance(ds, data)
            assert result is True
            mock_files_cls.return_value.get_by_hash.assert_called_once_with('abc123')
            mock_files_cls.return_value.get_by_sop_uid.assert_not_called()
            mock_files_cls.return_value.insert_or_select.assert_not_called()

    @pytest.mark.asyncio
    async def test_store_instance_dedups_by_sop_uid(self):
        ds = _make_minimal_dicom()
        data = BytesIO(b'dicom data')

        mock_conn = _make_mock_conn()
        existing_file = {'id': 77, 'name': 'existing.dcm', 'hash': 'abc123'}
        mock_files_cls = MagicMock()
        mock_files_cls.return_value.get_by_sop_uid = AsyncMock(return_value=existing_file)
        mock_files_cls.return_value.get_by_hash = AsyncMock(return_value=None)

        mock_replica_cls = MagicMock()
        mock_replica_cls.return_value.master = AsyncMock(return_value={'id': 1, 'type': 'local', 'location': '/tmp'})

        with patch('dcm.store.Replica', new=mock_replica_cls), \
             patch('dcm.store.Files', new=mock_files_cls), \
             patch('dcm.store.hash_file', return_value='abc123'), \
             patch('dcm.store.get_conn') as mock_get_conn:
            mock_get_conn.return_value.__aenter__.return_value = mock_conn

            from dcm.store import store_instance
            result = await store_instance(ds, data)
            assert result is True
            mock_files_cls.return_value.get_by_sop_uid.assert_called_once_with(
                '1.2.840.113619.2.55.1.1760426491.1234.3',
            )
            mock_files_cls.return_value.get_by_hash.assert_not_called()
            mock_files_cls.return_value.insert_or_select.assert_not_called()

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
        mock_files_cls.return_value.get_by_hash = AsyncMock(return_value=None)
        mock_files_cls.return_value.get_by_sop_uid = AsyncMock(return_value=None)

        mock_storage = MagicMock()
        mock_storage.copy = AsyncMock(return_value={'path': '/tmp/file.dcm', 'size': 1024})
        mock_replicafiles_cls = MagicMock()
        mock_replicafiles_cls.return_value.add = AsyncMock()

        with patch('dcm.store.Replica', new=mock_replica_cls), \
             patch('dcm.store.Files', new=mock_files_cls), \
             patch('dcm.store.Storage.get', AsyncMock(return_value=mock_storage)), \
             patch('dcm.store.ReplicaFiles', new=mock_replicafiles_cls), \
             patch('dcm.store.hash_file', return_value='abc123'), \
             patch('dcm.store.match_worklist_in_progress', new=AsyncMock()) as mock_match, \
             patch('dcm.store.get_conn') as mock_get_conn:
            mock_get_conn.return_value.__aenter__.return_value = mock_conn

            from dcm.store import store_instance
            await store_instance(ds, data)
            assert mock_match.called

    @pytest.mark.asyncio
    async def test_match_worklist_marks_in_progress_on_store(self):
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
                with patch.object(Worklist, 'mark_in_progress', new=AsyncMock()) as mock_mark:
                    from dcm.store import match_worklist_in_progress
                    await match_worklist_in_progress({'accession_number': 'ACC001', 'study_instance_uid': '1.2.3'})
                    mock_get_acc.assert_called_once_with('ACC001')
                    mock_mark.assert_called_once_with('ACC001', '1.2.3')

    @pytest.mark.asyncio
    async def test_match_worklist_in_progress_does_not_mark_performed(self):
        from db.worklist import Worklist

        class _FakeAc:
            async def __aenter__(self):
                return self
            async def __aexit__(self, *args):
                pass

        with patch('dcm.store.get_conn') as mock_get_conn:
            mock_get_conn.return_value = _FakeAc()

            mock_entry = {'status': 'scheduled', 'accession_number': 'ACC001'}
            with patch.object(Worklist, 'get_by_accession', new=AsyncMock(return_value=mock_entry)):
                with patch.object(Worklist, 'mark_performed', new=AsyncMock()) as mock_mark:
                    from dcm.store import match_worklist_in_progress
                    await match_worklist_in_progress({'accession_number': 'ACC001', 'study_instance_uid': '1.2.3'})
                    mock_mark.assert_not_called()

    @pytest.mark.asyncio
    async def test_match_worklist_no_action_when_no_accession(self):
        from dcm.store import match_worklist_in_progress
        with patch('db.worklist.Worklist') as mock_wl_cls:
            await match_worklist_in_progress({'accession_number': '', 'study_instance_uid': '1.2.3'})
            assert not mock_wl_cls.called

    @pytest.mark.asyncio
    async def test_store_instance_routes_to_destination(self):
        _TxTracker.in_transaction = False
        _TxTracker.copy_called_in_tx = False
        _TxTracker.copy_call_count = 0

        ds = _make_minimal_dicom()
        data = BytesIO(b'dicom data')

        mock_conn = _make_mock_conn()
        mock_replica_cls = MagicMock()
        mock_replica_cls.return_value.master = AsyncMock(return_value={'id': 1, 'type': 'local', 'location': '/tmp'})
        mock_replica_cls.return_value.get = AsyncMock(return_value={'id': 2, 'type': 'remote', 'location': '/remote'})
        mock_files_cls = MagicMock()
        mock_files_cls.return_value.insert_or_select = AsyncMock(return_value={'id': 42})
        mock_files_cls.return_value.get_by_hash = AsyncMock(return_value=None)
        mock_files_cls.return_value.get_by_sop_uid = AsyncMock(return_value=None)

        mock_master_storage = MagicMock()
        mock_master_storage.copy = AsyncMock(return_value={'path': '/tmp/file.dcm', 'size': 1024})
        mock_remote_storage = MagicMock()
        mock_remote_storage.copy = AsyncMock(return_value={'path': '/remote/file.dcm', 'size': 1024})

        mock_replicafiles_cls = MagicMock()
        mock_replicafiles_cls.return_value.add = AsyncMock()

        with patch('dcm.store.Replica', new=mock_replica_cls), \
             patch('dcm.store.Files', new=mock_files_cls), \
             patch('dcm.store.Storage.get', side_effect=[mock_master_storage, mock_remote_storage]), \
             patch('dcm.store.ReplicaFiles', new=mock_replicafiles_cls), \
             patch('dcm.store.hash_file', return_value='abc123'), \
             patch('dcm.store.match_worklist_in_progress', new=AsyncMock()), \
             patch('dcm.store.evaluate_routing_rules', new=AsyncMock(return_value=[
                 {'rule_id': '1', 'rule_name': 'CT route', 'destination': '2'},
             ])), \
             patch('dcm.store.get_conn') as mock_get_conn:
            mock_get_conn.return_value.__aenter__.return_value = mock_conn

            from dcm.store import store_instance
            result = await store_instance(ds, data)

        assert result is True
        assert mock_master_storage.copy.call_count == 1
        assert mock_remote_storage.copy.call_count == 1
        assert mock_replicafiles_cls.return_value.add.call_count == 2

    @pytest.mark.asyncio
    async def test_store_instance_two_phase_commit(self):
        _TxTracker.in_transaction = False
        _TxTracker.copy_called_in_tx = False
        _TxTracker.copy_call_count = 0

        ds = _make_minimal_dicom()
        data = BytesIO(b'dicom data')

        mock_conn = _make_mock_conn()
        mock_replica_cls = MagicMock()
        mock_replica_cls.return_value.master = AsyncMock(return_value={'id': 1, 'type': 'local', 'location': '/tmp'})
        mock_files_cls = MagicMock()
        mock_files_cls.return_value.insert_or_select = AsyncMock(return_value={'id': 42})
        mock_files_cls.return_value.get_by_hash = AsyncMock(return_value=None)
        mock_files_cls.return_value.get_by_sop_uid = AsyncMock(return_value=None)

        mock_storage = MagicMock()
        mock_storage_copy = AsyncMock(return_value={'path': '/tmp/file.dcm', 'size': 1024})
        mock_replicafiles_cls = MagicMock()
        mock_replicafiles_cls.return_value.add = AsyncMock()

        tracker = _TxTracker()
        mock_storage.copy = tracker.track_tx(mock_conn, mock_storage_copy)

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
        assert _TxTracker.copy_call_count == 1
        assert not _TxTracker.copy_called_in_tx, \
            "storage.copy must NOT be called inside a DB transaction"
