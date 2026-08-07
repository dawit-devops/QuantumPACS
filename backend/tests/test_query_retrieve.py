"""Unit tests for the DICOM Query/Retrieve C-FIND implementation."""
from unittest.mock import AsyncMock

import pytest
from pydicom.dataset import Dataset

from db.query_retrieve import (
    QueryRetrieve,
    _date_range,
    _determine_level,
    _wildcard_to_like,
)


class TestLevelDetermination:
    def test_study_level_by_default(self):
        assert _determine_level(Dataset()) == 'study'

    def test_series_level_from_uid(self):
        ds = Dataset()
        ds.SeriesInstanceUID = '1.2.3'
        assert _determine_level(ds) == 'series'

    def test_instance_level_from_uid(self):
        ds = Dataset()
        ds.SeriesInstanceUID = '1.2.3'
        ds.SOPInstanceUID = '1.2.3.4'
        assert _determine_level(ds) == 'instance'


class TestWildcardConversion:
    def test_star_becomes_percent(self):
        assert _wildcard_to_like('DOE*') == 'DOE%'

    def test_literal_percent_is_escaped(self):
        assert _wildcard_to_like('100%') == '100\\%'

    def test_literal_underscore_is_escaped(self):
        assert _wildcard_to_like('A_B') == 'A\\_B'


class TestDateRange:
    def test_exact(self):
        assert _date_range('20230101') == ('20230101', '20230101')

    def test_range(self):
        assert _date_range('20230101-20230201') == ('20230101', '20230201')

    def test_open_ended(self):
        assert _date_range('20230101-') == ('20230101', None)
        assert _date_range('-20230201') == (None, '20230201')


class TestFilters:
    def test_uid_matches_exactly(self):
        qr = QueryRetrieve(Dataset())
        ds = Dataset()
        ds.StudyInstanceUID = '1.2.3'
        qr.query_ds = ds
        sql, params = qr._filters('study')
        assert 'studies.study_instance_uid = $1' in sql
        assert params == ['1.2.3']

    def test_patient_name_uses_wildcard(self):
        qr = QueryRetrieve(Dataset())
        ds = Dataset()
        ds.PatientName = 'DOE*'
        qr.query_ds = ds
        sql, params = qr._filters('study')
        assert 'patients.patient_name ILIKE $1' in sql
        assert params == ['DOE%']

    def test_study_date_range(self):
        qr = QueryRetrieve(Dataset())
        ds = Dataset()
        ds.StudyDate = '20230101-20230201'
        qr.query_ds = ds
        sql, params = qr._filters('study')
        assert 'studies.study_date >= $1' in sql
        assert 'studies.study_date <= $2' in sql
        assert params == ['20230101', '20230201']

    def test_modality_at_study_level_uses_exists(self):
        qr = QueryRetrieve(Dataset())
        ds = Dataset()
        ds.Modality = 'CT'
        qr.query_ds = ds
        sql, params = qr._filters('study')
        assert 'EXISTS (SELECT 1 FROM series s_m' in sql
        assert params == ['CT']

    def test_empty_value_is_ignored(self):
        qr = QueryRetrieve(Dataset())
        ds = Dataset()
        ds.PatientID = ''
        qr.query_ds = ds
        sql, params = qr._filters('study')
        assert sql == ''
        assert params == []


class _FakeConn:
    def __init__(self, rows):
        self._rows = [dict(r) for r in rows]
        self.fetch = AsyncMock(return_value=self._rows)


def _study_row(**overrides):
    row = {
        'patient_id': 'P001', 'patient_name': 'Smith^John',
        'birth_date': '19800101', 'sex': 'M',
        'study_id': 'S1', 'study_instance_uid': '1.2.840.1',
        'description': 'Chest CT', 'study_date': '20230101',
        'accession_number': 'ACC1', 'referring_physician': 'Dr. A',
        'performing_physician': 'Dr. B', 'n_series': 2, 'n_instances': 10,
    }
    row.update(overrides)
    return row


class TestSearch:
    @pytest.mark.asyncio
    async def test_study_level_returns_requested_attrs(self):
        ds = Dataset()
        ds.PatientName = '*'
        ds.StudyDate = '20230101'
        qr = QueryRetrieve(ds)
        conn = _FakeConn([_study_row()])
        results = await qr.search(conn)

        assert len(results) == 1
        rsp = results[0]
        assert rsp.StudyInstanceUID == '1.2.840.1'
        assert rsp.PatientName == 'Smith^John'
        assert rsp.StudyDate == '20230101'
        assert rsp.NumberOfStudyRelatedInstances == 10
        assert rsp.NumberOfStudyRelatedSeries == 2

    @pytest.mark.asyncio
    async def test_instance_level_returns_sop_uid(self):
        ds = Dataset()
        ds.StudyInstanceUID = '1.2.840.1'
        ds.SeriesInstanceUID = '1.2.840.1.2'
        ds.SOPInstanceUID = '1.2.840.1.2.3'
        ds.SOPClassUID = '1.2.840.10008.5.1.4.1.1.2'
        ds.InstanceNumber = '7'
        qr = QueryRetrieve(ds)
        assert qr.level == 'instance'

        row = _study_row(
            series_instance_uid='1.2.840.1.2', series_number='1',
            modality='CT', sop_instance_uid='1.2.840.1.2.3',
            sop_class_uid='1.2.840.10008.5.1.4.1.1.2',
            instance_number='7',
        )
        conn = _FakeConn([row])
        results = await qr.search(conn)

        assert len(results) == 1
        rsp = results[0]
        assert rsp.SOPInstanceUID == '1.2.840.1.2.3'
        assert rsp.SeriesInstanceUID == '1.2.840.1.2'
        assert rsp.InstanceNumber == '7'
        assert rsp.SOPClassUID == '1.2.840.10008.5.1.4.1.1.2'

    @pytest.mark.asyncio
    async def test_filters_reach_sql(self):
        ds = Dataset()
        ds.PatientID = 'P001'
        qr = QueryRetrieve(ds)
        conn = _FakeConn([_study_row()])
        await qr.search(conn)

        sql = conn.fetch.await_args.args[0]
        assert 'patients.patient_id ILIKE $1' in sql
        assert conn.fetch.await_args.args[1] == 'P001'

    @pytest.mark.asyncio
    async def test_skips_rows_without_study_uid(self):
        qr = QueryRetrieve(Dataset())
        conn = _FakeConn([_study_row(study_instance_uid='')])
        results = await qr.search(conn)
        assert results == []
