"""H-2 (branch review): read-time tenant isolation for clinical tables.

Writes are tenant-tagged (G-2). This file pins the *read* contract: a tenant
caller must not see another tenant's rows. Today the clinical reads are NOT
scoped by tenant_id — isolation for separate-DB tenants rests on connection
routing, and the shared-DB (`default`) tenant has no read filter — so the
cross-tenant read assertions are `xfail` until the read-scoping decision
(branch-review M-1 / H-3) lands. Once that ships, they become real assertions.

The running-counter tests are real and passing: they lock in H-1's removal of
the per-instance `SUM(files.size)` full-table scan in favour of an O(1)
`tenants.storage_used_bytes` adjustment.
"""
import asyncio
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from db.conn import (get_conn, reset_tenant_slug, set_tenant_slug, setup,
                     teardown)
from db.exams import Exams
from db.patient import Patient
from db.study import Study
from db.worklist import Worklist

READ_CASES = [
    ('patients', lambda c, t: Patient(c).insert_or_select({
        'patient_id': t, 'patient_name': 'X', 'patient_birth_date': '',
        'patient_sex': 'O'})),
    ('studies', lambda c, t: Study(c).insert_or_select({
        'patient_db_id': 1, 'study_id': t, 'study_description': '',
        'study_instance_uid': f'1.2.3.{t}.s', 'accession_number': f'A-{t}',
        'study_date': '', 'referring_physician': '', 'performing_physician': ''})),
    ('exams', lambda c, t: Exams(c).create({
        'patient_id': t, 'patient_name': 'X', 'patient_birth_date': '',
        'patient_sex': 'O', 'accession_number': f'A-{t}', 'modality': 'CT',
        'station_ae_title': '', 'protocol_name': '', 'assigned_technologist': '',
        'assigned_radiologist': '', 'referring_physician': '', 'created_by': ''})),
    ('worklist_entries', lambda c, t: Worklist(c).create({
        'patient_id': t, 'patient_name': 'X', 'patient_birth_date': '',
        'patient_sex': 'O', 'accession_number': f'A-{t}', 'modality': 'CT',
        'scheduled_date': None, 'scheduled_time': None, 'station_ae_title': '',
        'created_by': ''})),
]


class TestClinicalReadIsolation:
    """A read performed in tenant-A's scope must not surface tenant-B's rows.

    xfail until reads are scoped by tenant_id (branch-review M-1 / H-3).
    """

    @pytest.mark.parametrize('table,insert', READ_CASES)
    @pytest.mark.xfail(
        strict=False,
        reason='read-scoping by tenant_id not yet enforced — branch-review M-1/H-3',
    )
    def test_cross_tenant_read_excludes_other_tenant(self, table, insert):
        async def run():
            try:
                await setup()
            except Exception as e:  # pragma: no cover - environmental
                pytest.skip(f'dev database unavailable: {e}')

            try:
                async with get_conn() as conn:
                    tx = conn.transaction()
                    await tx.start()
                    try:
                        tag = uuid.uuid4().hex[:8]
                        set_tenant_slug('clinic-b')
                        rid = (await insert(conn, f'X-{tag}'))['id']

                        # Now act as clinic-a: a list/read in its scope must
                        # not return clinic-b's row.
                        reset_tenant_slug()
                        set_tenant_slug('clinic-a')
                        rows = await conn.fetch(f'SELECT id FROM {table}')
                        ids = {r['id'] for r in rows}
                        assert rid not in ids
                    finally:
                        await tx.rollback()
                        reset_tenant_slug()
            finally:
                await teardown()

        asyncio.run(run())


class TestRunningStorageCounter:
    """H-1: the storage counter is adjusted O(1), never recomputed via SUM."""

    def test_adjust_storage_used_increments_and_clamps(self):
        from db.tenants import Tenants
        conn = MagicMock()
        conn.execute = AsyncMock()

        async def run():
            await Tenants(conn).adjust_storage_used('acme', 100)
            await Tenants(conn).adjust_storage_used('acme', -1_000_000)

        asyncio.run(run())
        calls = conn.execute.await_args_list
        assert 'GREATEST(0, storage_used_bytes + $1)' in calls[0].args[0]
        assert calls[0].args[1:] == (100, 'acme')
        # A delete larger than the recorded total is floored at 0, never
        # drives the counter negative.
        assert calls[1].args[1:] == (-1_000_000, 'acme')

    def test_store_persist_usage_adjusts_not_scans(self):
        from dcm import store as store_mod
        from db.tenants import Tenants
        fake_conn = MagicMock()

        async def run():
            ctx = MagicMock()
            ctx.__aenter__.return_value = fake_conn
            ctx.__aexit__.return_value = False
            with patch.object(store_mod, 'get_database') as gd, \
                    patch.object(Tenants, 'adjust_storage_used', new=AsyncMock()) as adj:
                gd.return_value.acquire.return_value = ctx
                await store_mod._persist_usage('acme', 42)
                adj.assert_awaited_once_with('acme', 42)

        asyncio.run(run())
