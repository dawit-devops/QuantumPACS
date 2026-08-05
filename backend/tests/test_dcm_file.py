from unittest.mock import MagicMock, patch

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
            'patient_sex', 'study_id', 'study_description',
            'series_number', 'modality', 'series_description',
            'cleaned', 'raw',
        }
        assert set(meta.keys()) == expected

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

    def test_raw_is_dict_of_tag_to_element(self, dataset):
        meta = get_meta(dataset)
        assert isinstance(meta['raw'], dict)
        assert len(meta['raw']) > 0

    def test_modality_cleaned(self, dataset):
        meta = get_meta(dataset)
        assert meta['modality'] == 'CT'

    def test_patient_name_unmodified(self, dataset):
        meta = get_meta(dataset)
        assert meta['patient_name'] == 'Smith^John'


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
        assert 'raw' in result
        assert 'patient_id' in result
