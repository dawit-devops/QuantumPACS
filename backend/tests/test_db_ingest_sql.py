"""SQL-shape regression tests for the ingest path (db/study|series|replica_files).

These caught a pypika misuse: `on_conflict('a, b')` renders a single quoted
column `("a, b")` which PostgreSQL rejects with
"column a, b does not exist" — breaking every real ingestion (STOW/C-STORE)
while mocked-unit tests stayed green.
"""

from unittest.mock import AsyncMock, MagicMock


from db.patient import Patient
from db.replica_files import ReplicaFiles
from db.series import Series
from db.study import Study


def _conn():
    conn = AsyncMock()
    conn.fetchval.return_value = 1
    return conn


class TestIngestConflictColumns:
    def test_study_on_conflict_is_two_columns(self):
        conn = _conn()
        data = {
            'patient_db_id': 8, 'study_id': 'ST-1',
            'study_description': 'desc', 'study_instance_uid': '1.2.3',
            'accession_number': 'A1', 'study_date': '20260101',
            'referring_physician': '', 'performing_physician': '',
        }
        result = __import__('asyncio').run(Study(conn).insert_or_select(data))
        sql = str(conn.fetchval.call_args[0][0])
        assert 'ON CONFLICT ("patient_id", "study_id")' in sql
        assert '"patient_id, study_id"' not in sql
        assert result == {'id': 1}

    def test_series_on_conflict_is_two_columns(self):
        conn = _conn()
        data = {
            'study_db_id': 1, 'series_number': '1', 'modality': 'CT',
            'series_description': '', 'series_instance_uid': '1.2.4',
        }
        __import__('asyncio').run(Series(conn).insert_or_select(data))
        sql = str(conn.fetchval.call_args[0][0])
        assert 'ON CONFLICT ("study_id", "number")' in sql
        assert '"study_id, number"' not in sql

    def test_patient_on_conflict_single_column(self):
        conn = _conn()
        data = {
            'patient_id': 'SMOKE001', 'patient_name': 'Smoke^Test',
            'patient_birth_date': '19800101', 'patient_sex': 'M',
        }
        __import__('asyncio').run(Patient(conn).insert_or_select(data))
        sql = str(conn.fetchval.call_args[0][0])
        assert 'ON CONFLICT ("patient_id")' in sql

    def test_replica_files_on_conflict_is_two_columns(self):
        conn = _conn()
        conn.transaction = MagicMock()
        conn.transaction.return_value.__aenter__ = AsyncMock()
        conn.transaction.return_value.__aexit__ = AsyncMock(return_value=False)
        rf = ReplicaFiles(conn)
        rf.conn.execute = AsyncMock()
        rf.conn.fetch = AsyncMock(return_value=[])
        files = [{'id': 2, 'location': '', 'meta': {}}]
        __import__('asyncio').run(rf.add(1, files))
        sqls = [str(c.args[0]) for c in rf.conn.execute.call_args_list]
        assert any('ON CONFLICT ("replica_id", "file_id")' in s for s in sqls)
        assert all('"replica_id, file_id"' not in s for s in sqls)
