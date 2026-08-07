"""QIDO JSON mapping tests (dcm.dicom_json)."""

from dcm.dicom_json import row_to_study_json


class TestRowToStudyJson:
    def test_maps_standard_study_fields(self):
        row = {
            'study_instance_uid': '1.2.3',
            'accession_number': 'ACC1',
            'patient_name': 'A^B',
            'patient_id': 'P1',
            'study_date': '20260807',
        }
        result = row_to_study_json(row)
        assert result['0020000D']['Value'] == ['1.2.3']
        assert result['00100010']['Value'] == [{'Alphabetic': 'A^B'}]
        assert result['00080050']['Value'] == ['ACC1']
        assert result['00100020']['Value'] == ['P1']
        assert result['00080020']['Value'] == ['20260807']

    def test_study_status_receiving_maps_to_partial(self):
        row = {'study_status': 'receiving'}
        result = row_to_study_json(row)
        assert result['00080056']['vr'] == 'CS'
        assert result['00080056']['Value'] == ['PARTIAL']

    def test_study_status_complete_maps_to_complete(self):
        row = {'study_status': 'complete'}
        result = row_to_study_json(row)
        assert result['00080056']['Value'] == ['COMPLETE']

    def test_study_status_incomplete_maps_to_incomplete(self):
        row = {'study_status': 'incomplete'}
        result = row_to_study_json(row)
        assert result['00080056']['Value'] == ['INCOMPLETE']

    def test_study_status_absent_omits_tag(self):
        row = {'study_instance_uid': '1.2.3'}
        result = row_to_study_json(row)
        assert '00080056' not in result

    def test_unknown_status_passes_through(self):
        row = {'study_status': 'weird'}
        result = row_to_study_json(row)
        assert result['00080056']['Value'] == ['weird']
