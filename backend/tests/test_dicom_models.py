from unittest.mock import AsyncMock, patch

import pytest

from db.study import Study
from db.series import Series


class TestStudyUidColumns:
    @pytest.mark.asyncio
    async def test_insert_or_select_sql_contains_study_instance_uid(self):
        conn = AsyncMock()
        conn.fetchval.return_value = 1
        s = Study(conn=conn)
        data = {
            'study_db_id': 1,
            'study_id': 'S001',
            'study_description': 'Chest',
            'study_instance_uid': '1.2.3.4.5.6.7.8.1',
            'accession_number': 'ACC001',
        }
        await s.insert_or_select(data)
        sql = conn.fetchval.call_args[0][0]
        assert 'study_instance_uid' in sql
        assert 'accession_number' in sql
        assert data['study_instance_uid'] in sql
        assert data['accession_number'] in sql

    @pytest.mark.asyncio
    async def test_insert_or_select_handles_missing_uids(self):
        conn = AsyncMock()
        conn.fetchval.return_value = 1
        s = Study(conn=conn)
        data = {
            'study_db_id': 1,
            'study_id': 'S001',
            'study_description': 'Chest',
        }
        await s.insert_or_select(data)
        sql = conn.fetchval.call_args[0][0]
        assert 'study_instance_uid' in sql
        assert 'accession_number' in sql


class TestSeriesUidColumns:
    @pytest.mark.asyncio
    async def test_insert_or_select_sql_contains_series_instance_uid(self):
        conn = AsyncMock()
        conn.fetchval.return_value = 1
        s = Series(conn=conn)
        data = {
            'study_db_id': 1,
            'series_number': '1',
            'modality': 'CT',
            'series_description': 'Axial',
            'series_instance_uid': '1.2.3.4.5.6.7.8.2',
        }
        await s.insert_or_select(data)
        sql = conn.fetchval.call_args[0][0]
        assert 'series_instance_uid' in sql
        assert data['series_instance_uid'] in sql

    @pytest.mark.asyncio
    async def test_insert_or_select_handles_missing_uid(self):
        conn = AsyncMock()
        conn.fetchval.return_value = 1
        s = Series(conn=conn)
        data = {
            'study_db_id': 1,
            'series_number': '1',
            'modality': 'CT',
        }
        await s.insert_or_select(data)
        sql = conn.fetchval.call_args[0][0]
        assert 'series_instance_uid' in sql
