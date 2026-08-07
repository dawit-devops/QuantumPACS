from unittest.mock import patch

import pydicom
import pytest
from pydicom.dataelem import DataElement
from pydicom.tag import Tag

from dcm.file import clean, get_meta, parse_dcm


class TestClean:
    def test_strips_whitespace(self):
        assert clean('  hello  ') == 'hello'

    def test_removes_single_quotes(self):
        assert clean("'quoted'") == 'quoted'

    def test_removes_double_quotes(self):
        assert clean('"quoted"') == 'quoted'

    def test_handles_empty_string(self):
        assert clean('') == ''

    def test_strict_replaces_slash(self):
        assert clean('a/b/c', strict=True) == 'a-b-c'

    def test_non_strict_keeps_slash(self):
        assert clean('a/b/c', strict=False) == 'a/b/c'

    def test_strict_on_unquoted_string(self):
        assert clean('hello', strict=True) == 'hello'

    def test_non_string_input(self):
        assert clean(123) == '123'
        assert clean(None) == 'None'

    def test_quotes_and_slash_in_strict(self):
        result = clean("'/path/name'", strict=True)
        assert '-' not in 'path'
        assert result == '-path-name'

    def test_only_leading_quote(self):
        result = clean("'hello")
        assert result == 'hell'


class TestGetMeta:
    @pytest.fixture
    def dataset(self):
        ds = pydicom.Dataset()
        ds.PatientID = 'P001'
        ds.PatientName = 'Smith^John'
        ds.PatientBirthDate = '19800101'
        ds.PatientSex = 'M'
        ds.StudyID = 'S001'
        ds.StudyDescription = 'Chest X-Ray'
        ds.SeriesNumber = '1'
        ds.Modality = 'CT'
        ds.SeriesDescription = 'Axial'
        ds.add(DataElement(Tag(0x0008, 0x0005), 'SH', 'ISO_IR 100'))
        return ds

    def test_returns_all_expected_keys(self, dataset):
        meta = get_meta(dataset)
        expected = {
            'patient_id', 'patient_name', 'patient_birth_date',
            'patient_sex', 'study_id', 'study_description', 'study_date',
            'series_number', 'modality', 'series_description',
            'study_instance_uid', 'series_instance_uid',
            'sop_instance_uid', 'sop_class_uid', 'instance_number',
            'accession_number',
            'referring_physician',
            'performing_physician',
            'reading_physician',
            'requested_procedure_priority',
            'cleaned',
        }
        assert set(meta.keys()) == expected

    def test_extracts_mwl_priority_and_reading_physician(self):
        ds = pydicom.Dataset()
        ds.PatientID = 'P001'
        ds.StudyID = 'S001'
        ds.SeriesNumber = '1'
        ds.Modality = 'CT'
        ds.RequestedProcedurePriority = 'A'
        ds.NameOfPhysiciansReadingStudy = 'Radiologist^Rita'
        meta = get_meta(ds)
        assert meta['requested_procedure_priority'] == 'A'
        assert meta['reading_physician'] == 'Radiologist^Rita'

    def test_patient_id_is_strict_cleaned(self, dataset):
        meta = get_meta(dataset)
        assert meta['patient_id'] == 'P001'

    def test_patient_id_replaces_slash_in_strict(self):
        ds = pydicom.Dataset()
        ds.PatientID = 'P/001'
        ds.StudyID = 'S001'
        ds.SeriesNumber = '1'
        ds.Modality = 'CT'
        meta = get_meta(ds)
        assert '/' not in meta['patient_id']

    def test_study_id_is_strict_cleaned(self, dataset):
        meta = get_meta(dataset)
        assert meta['study_id'] == 'S001'

    def test_series_number_is_strict_cleaned(self, dataset):
        meta = get_meta(dataset)
        assert meta['series_number'] == '1'

    def test_missing_optional_fields_default_to_empty(self):
        ds = pydicom.Dataset()
        ds.PatientID = 'P001'
        ds.StudyID = 'S001'
        ds.SeriesNumber = '1'
        ds.Modality = 'MR'
        meta = get_meta(ds)
        assert meta['patient_name'] == ''
        assert meta['study_description'] == ''
        assert meta['series_description'] == ''

    def test_cleaned_contains_all_element_names(self, dataset):
        meta = get_meta(dataset)
        assert 'Patient ID' in meta['cleaned']
        assert "Patient's Name" in meta['cleaned']

    def test_raw_not_exposed(self, dataset):
        # raw held non-serializable DataElement objects and was unused in
        # production; it must not be part of the returned metadata.
        meta = get_meta(dataset)
        assert 'raw' not in meta

    def test_modality_cleaned(self, dataset):
        meta = get_meta(dataset)
        assert meta['modality'] == 'CT'

    def test_patient_name_unmodified(self, dataset):
        meta = get_meta(dataset)
        assert meta['patient_name'] == 'Smith^John'

    @pytest.mark.filterwarnings('ignore:Invalid value for VR UI')
    def test_get_meta_preserves_slash_in_uids_and_accession(self):
        ds = pydicom.Dataset()
        ds.PatientID = 'P/001'
        ds.StudyID = 'S001'
        ds.SeriesNumber = '1'
        ds.Modality = 'CT'
        ds.StudyInstanceUID = '1.2.840.113619/2.55.1/1760426491.1234.1'
        ds.SeriesInstanceUID = '1.2.840.113619/2.55.1/1760426491.1234.2'
        ds.SOPInstanceUID = '1.2.840.113619/2.55.1/1760426491.1234.3'
        ds.AccessionNumber = 'ACC/001'
        meta = get_meta(ds)
        # UIDs and accessions are identity keys and must survive verbatim.
        assert meta['study_instance_uid'] == '1.2.840.113619/2.55.1/1760426491.1234.1'
        assert meta['series_instance_uid'] == '1.2.840.113619/2.55.1/1760426491.1234.2'
        assert meta['sop_instance_uid'] == '1.2.840.113619/2.55.1/1760426491.1234.3'
        assert meta['accession_number'] == 'ACC/001'
        # Free-text IDs stay sanitized (path-safety).
        assert meta['patient_id'] == 'P-001'

    def test_cleaned_skips_binary_other_vrs(self):
        ds = pydicom.Dataset()
        ds.PatientID = 'P001'
        ds.StudyID = 'S001'
        ds.SeriesNumber = '1'
        ds.Modality = 'CT'
        # Full C-STORE datasets carry PixelData (OB/OW) — binary payloads
        # must not appear in the persisted `cleaned` metadata.
        ds.add(DataElement(Tag(0x7FE0, 0x0010), 'OB', b'\x00' * 4096))
        ds.add(DataElement(Tag(0x0019, 0x1000), 'LO', 'alpha'))
        meta = get_meta(ds)
        assert 'Pixel Data' not in meta['cleaned']
        assert 'Private tag data' in meta['cleaned']

    def test_cleaned_keys_collision_safe_for_private_tags(self):
        ds = pydicom.Dataset()
        ds.PatientID = 'P001'
        ds.StudyID = 'S001'
        ds.SeriesNumber = '1'
        ds.Modality = 'CT'
        # Two distinct private tags both have the name 'Private tag data'.
        ds.add(DataElement(Tag(0x0019, 0x1000), 'LO', 'alpha'))
        ds.add(DataElement(Tag(0x0019, 0x1001), 'LO', 'beta'))
        meta = get_meta(ds)
        private = {k: v for k, v in meta['cleaned'].items() if 'Private tag data' in k}
        assert len(private) == 2
        assert 'alpha' in private.values()
        assert 'beta' in private.values()

    def test_get_meta_returns_study_instance_uid(self):
        ds = pydicom.Dataset()
        ds.PatientID = 'P001'
        ds.StudyID = 'S001'
        ds.SeriesNumber = '1'
        ds.Modality = 'CT'
        ds.StudyInstanceUID = '1.2.840.113619.2.55.1.1760426491.1234.1'
        ds.SeriesInstanceUID = '1.2.840.113619.2.55.1.1760426491.1234.2'
        ds.SOPInstanceUID = '1.2.840.113619.2.55.1.1760426491.1234.3'
        ds.AccessionNumber = 'ACC001'
        meta = get_meta(ds)
        assert meta['study_instance_uid'] == '1.2.840.113619.2.55.1.1760426491.1234.1'
        assert meta['series_instance_uid'] == '1.2.840.113619.2.55.1.1760426491.1234.2'
        assert meta['sop_instance_uid'] == '1.2.840.113619.2.55.1.1760426491.1234.3'
        assert meta['accession_number'] == 'ACC001'

    def test_get_meta_extracts_dicomweb_index_fields(self):
        ds = pydicom.Dataset()
        ds.PatientID = 'P001'
        ds.StudyID = 'S001'
        ds.SeriesNumber = '1'
        ds.Modality = 'CT'
        ds.StudyDate = '20260725'
        ds.SOPClassUID = '1.2.840.10008.5.1.4.1.1.2'
        ds.InstanceNumber = '7'
        meta = get_meta(ds)
        assert meta['study_date'] == '20260725'
        assert meta['sop_class_uid'] == '1.2.840.10008.5.1.4.1.1.2'
        assert meta['instance_number'] == '7'

    def test_get_meta_uids_default_to_empty_when_missing(self):
        ds = pydicom.Dataset()
        ds.PatientID = 'P001'
        ds.StudyID = 'S001'
        ds.SeriesNumber = '1'
        ds.Modality = 'CT'
        meta = get_meta(ds)
        assert meta['study_instance_uid'] == ''
        assert meta['series_instance_uid'] == ''
        assert meta['sop_instance_uid'] == ''
        assert meta['accession_number'] == ''


class TestParseDcm:
    @patch('pydicom.dcmread')
    def test_parse_dcm_calls_dcmread(self, mock_dcmread):
        ds = pydicom.Dataset()
        ds.PatientID = 'P001'
        ds.StudyID = 'S001'
        ds.SeriesNumber = '1'
        ds.Modality = 'US'
        mock_dcmread.return_value = ds

        result = parse_dcm('/path/to/file.dcm')
        mock_dcmread.assert_called_once_with('/path/to/file.dcm', stop_before_pixels=True)
        assert result['patient_id'] == 'P001'
        assert result['modality'] == 'US'

    @patch('pydicom.dcmread')
    def test_stop_before_pixels_true(self, mock_dcmread):
        ds = pydicom.Dataset()
        ds.PatientID = 'P001'
        ds.StudyID = 'S001'
        ds.SeriesNumber = '1'
        ds.Modality = 'XA'
        mock_dcmread.return_value = ds

        parse_dcm('/file.dcm')
        args, kwargs = mock_dcmread.call_args
        assert kwargs.get('stop_before_pixels') is True

    @patch('pydicom.dcmread')
    def test_parse_dcm_returns_get_meta_shape(self, mock_dcmread):
        ds = pydicom.Dataset()
        ds.PatientID = 'P001'
        ds.StudyID = 'S001'
        ds.SeriesNumber = '1'
        ds.Modality = 'CT'
        mock_dcmread.return_value = ds

        result = parse_dcm('/f.dcm')
        assert 'cleaned' in result
        assert 'raw' not in result
        assert 'patient_id' in result
