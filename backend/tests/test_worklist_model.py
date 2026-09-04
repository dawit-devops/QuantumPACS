from unittest.mock import AsyncMock

import pytest


class TestWorklistCreate:
    @pytest.mark.asyncio
    async def test_create_returns_id(self):
        from db.worklist import Worklist
        conn = AsyncMock()
        conn.fetchval.return_value = "550e8400-e29b-41d4-a716-446655440000"
        wl = Worklist(conn=conn)
        data = {
            "patient_id": "P001",
            "patient_name": "Test^Patient",
            "accession_number": "ACC001",
            "modality": "CT",
            "scheduled_date": "2026-07-25",
        }
        result = await wl.create(data)
        assert result["id"] == "550e8400-e29b-41d4-a716-446655440000"

    @pytest.mark.asyncio
    async def test_create_generates_insert_sql(self):
        from db.worklist import Worklist
        conn = AsyncMock()
        conn.fetchval.return_value = "uuid-here"
        wl = Worklist(conn=conn)
        data = {
            "patient_id": "P001",
            "patient_name": "Test^Patient",
            "accession_number": "ACC001",
            "modality": "CT",
            "scheduled_date": "2026-07-25",
        }
        await wl.create(data)
        sql = conn.fetchval.call_args[0][0]
        assert "INSERT INTO" in sql
        assert "worklist_entries" in sql
        assert "patient_id" in sql
        assert "P001" in sql

    @pytest.mark.asyncio
    async def test_create_requires_patient_id(self):
        from db.worklist import Worklist
        conn = AsyncMock()
        wl = Worklist(conn=conn)
        with pytest.raises(KeyError):
            await wl.create({"modality": "CT"})


class TestWorklistSearch:
    @pytest.mark.asyncio
    async def test_search_selects_from_worklist(self):
        from db.worklist import Worklist
        conn = AsyncMock()
        conn.fetch.return_value = []
        wl = Worklist(conn=conn)
        await wl.search()
        sql = conn.fetch.call_args[0][0]
        assert "SELECT" in sql
        assert "worklist_entries" in sql

    @pytest.mark.asyncio
    async def test_search_filters_by_status(self):
        from db.worklist import Worklist
        conn = AsyncMock()
        conn.fetch.return_value = []
        wl = Worklist(conn=conn)
        await wl.search(status="scheduled")
        sql = conn.fetch.call_args[0][0]
        assert "status" in sql
        assert "scheduled" in sql

    @pytest.mark.asyncio
    async def test_search_filters_by_modality(self):
        from db.worklist import Worklist
        conn = AsyncMock()
        conn.fetch.return_value = []
        wl = Worklist(conn=conn)
        await wl.search(modality="CT")
        sql = conn.fetch.call_args[0][0]
        assert "modality" in sql
        assert "CT" in sql

    @pytest.mark.asyncio
    async def test_search_filters_by_date_range(self):
        from db.worklist import Worklist
        conn = AsyncMock()
        conn.fetch.return_value = []
        wl = Worklist(conn=conn)
        await wl.search(date_from="2026-07-01", date_to="2026-07-31")
        sql = conn.fetch.call_args[0][0]
        assert "scheduled_date" in sql
        assert "2026-07-01" in sql
        assert "2026-07-31" in sql

    @pytest.mark.asyncio
    async def test_search_supports_pagination(self):
        from db.worklist import Worklist
        conn = AsyncMock()
        conn.fetch.return_value = []
        wl = Worklist(conn=conn)
        await wl.search(page=2, per_page=10)
        sql = conn.fetch.call_args[0][0]
        assert "LIMIT" in sql or "limit" in sql
        assert "OFFSET" in sql or "offset" in sql


class TestWorklistMarkPerformed:
    @pytest.mark.asyncio
    async def test_mark_performed_updates_status(self):
        from db.worklist import Worklist
        conn = AsyncMock()
        conn.execute.return_value = "UPDATE 1"
        wl = Worklist(conn=conn)
        await wl.mark_performed("ACC001", "1.2.3.4.5.6.7.8")
        sql = conn.execute.call_args[0][0]
        assert "UPDATE" in sql
        assert "worklist_entries" in sql
        assert "performed" in sql
        assert "ACC001" in sql


class TestWorklistGetByAccession:
    @pytest.mark.asyncio
    async def test_get_by_accession_returns_entry(self):
        from db.worklist import Worklist
        conn = AsyncMock()
        conn.fetchrow.return_value = {"id": "uuid", "patient_id": "P001", "status": "scheduled"}
        wl = Worklist(conn=conn)
        result = await wl.get_by_accession("ACC001")
        assert result["patient_id"] == "P001"
        sql = conn.fetchrow.call_args[0][0]
        assert "ACC001" in sql

    @pytest.mark.asyncio
    async def test_get_by_accession_returns_none_when_missing(self):
        from db.worklist import Worklist
        conn = AsyncMock()
        conn.fetchrow.return_value = None
        wl = Worklist(conn=conn)
        result = await wl.get_by_accession("NONEXISTENT")
        assert result is None


class TestWorklistCancel:
    @pytest.mark.asyncio
    async def test_cancel_updates_status(self):
        from db.worklist import Worklist
        conn = AsyncMock()
        conn.execute.return_value = "UPDATE 1"
        wl = Worklist(conn=conn)
        await wl.cancel("entry-uuid-here")
        sql = conn.execute.call_args[0][0]
        assert "UPDATE" in sql
        assert "cancelled" in sql
        assert "entry-uuid-here" in sql

class TestWorklistDicomMatching:
    """M-7: MWL matching must follow DICOM PS3.4 C.2.2.2 — attributes
    match as single values (exact) unless the query carries the '*'/'?'
    wildcards; literal '%'/'_' must never inject LIKE syntax."""

    @pytest.mark.asyncio
    async def test_search_patient_id_exact_without_wildcards(self):
        from db.worklist import Worklist
        conn = AsyncMock()
        conn.fetch.return_value = []
        wl = Worklist(conn=conn)
        await wl.search(patient_id='P001')
        sql = str(conn.fetch.call_args[0][0])
        assert 'patient_id' in sql
        assert '%' not in sql.replace('ILIKE', '')

    @pytest.mark.asyncio
    async def test_search_patient_id_wildcard_translated(self):
        from db.worklist import Worklist
        conn = AsyncMock()
        conn.fetch.return_value = []
        wl = Worklist(conn=conn)
        await wl.search(patient_id='P0*1')
        sql = str(conn.fetch.call_args[0][0])
        assert "'P0%1'" in sql

    @pytest.mark.asyncio
    async def test_search_accession_exact_without_wildcards(self):
        from db.worklist import Worklist
        conn = AsyncMock()
        conn.fetch.return_value = []
        wl = Worklist(conn=conn)
        await wl.search(accession='ACC001')
        sql = str(conn.fetch.call_args[0][0])
        assert "'ACC001'" in sql
        assert '%ACC001%' not in sql

    @pytest.mark.asyncio
    async def test_search_accession_wildcard_translated(self):
        from db.worklist import Worklist
        conn = AsyncMock()
        conn.fetch.return_value = []
        wl = Worklist(conn=conn)
        await wl.search(accession='ACC*1')
        sql = str(conn.fetch.call_args[0][0])
        assert "'ACC%1'" in sql

    @pytest.mark.asyncio
    async def test_search_literal_percent_never_injects_like(self):
        from db.worklist import Worklist
        conn = AsyncMock()
        conn.fetch.return_value = []
        wl = Worklist(conn=conn)
        await wl.search(patient_id='100%')
        sql = str(conn.fetch.call_args[0][0])
        assert "100%" not in sql.replace('ILIKE', '')
        await wl.search(accession='ACC100%')
        sql2 = str(conn.fetch.call_args[0][0])
        assert "ACC100%" not in sql2.replace('ILIKE', '')
