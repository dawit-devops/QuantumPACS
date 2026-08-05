from unittest.mock import AsyncMock

import pytest

from db.patient import Patient


class TestPatient:
    @pytest.mark.asyncio
    async def test_insert_or_select_returns_existing(self):
        conn = AsyncMock()
        conn.fetchval.return_value = 1
        p = Patient(conn=conn)
        result = await p.insert_or_select({'patient_id': 'P001', 'patient_name': 'Test', 'patient_birth_date': '', 'patient_sex': ''})
        assert result['id'] == 1

    @pytest.mark.asyncio
    async def test_get_extra_returns_none_for_missing(self):
        conn = AsyncMock()
        conn.fetchrow.return_value = None
        p = Patient(conn=conn)
        result = await p.get_extra(999)
        assert result is None

    @pytest.mark.asyncio
    async def test_get_extra_builds_study_series_tree(self):
        conn = AsyncMock()
        conn.fetchrow.return_value = {'id': 1, 'patient_id': 'P001', 'name': 'Test', 'meta': None}
        conn.fetch.return_value = [
            {'study_id': 10, 'study_uid': '1.2.3', 'study_desc': None,
             'study_instance_uid': None, 'accession_number': None,
             'series_id': 20, 'series_number': 1, 'series_modality': 'CT',
             'series_desc': None, 'series_instance_uid': None,
             'file_id': 30, 'file_name': 'img.dcm', 'file_hash': 'abc',
             'indexed': True, 'sop_instance_uid': None, 'deleted': False,
             'meta': None, 'tools_state': None},
        ]
        p = Patient(conn=conn)
        result = await p.get_extra(1)
        assert result['patient_id'] == 'P001'
        assert len(result['studies']) == 1
        assert result['studies'][0]['study_id'] == '1.2.3'
        assert len(result['studies'][0]['series']) == 1
        series = result['studies'][0]['series'][0]
        assert series['number'] == 1
        assert len(series['files']) == 1

    @pytest.mark.asyncio
    async def test_sync_db_creates_table(self):
        conn = AsyncMock()
        p = Patient(conn=conn)
        await p.sync_db()
        assert conn.execute.call_count == 2
        first_sql = conn.execute.call_args_list[0][0][0]
        assert 'CREATE TABLE' in first_sql
