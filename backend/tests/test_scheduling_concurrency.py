"""B9 (S4-09/10 QA) — no_double_book EXCLUDE under concurrency + RLS.

The engine pre-checks overlaps for a friendly error, but the real
guarantee (RIS-SL-34: 0 double-books) is the Postgres EXCLUDE constraint
(migration 069). This suite hammers it: 50 concurrent bookings for the
same resource/slot must admit exactly one. Also proves override deletes
physically release the slot (the EXCLUDE has no WHERE, so CANCELLED rows
still overlap), and that appointments/resources carry the tenant tag.

Pattern mirrors test_ris_tenant_isolation.py: real DB, rolled-back tx for
the tagging tests; the concurrency test cannot be wrapped in a tx (each
task needs its own connection) so it cleans up by tenant tag instead.
"""

import asyncio
import uuid
from datetime import datetime

import pytest

from db.conn import (
    get_conn,
    reset_tenant_slug,
    set_tenant_slug,
    setup,
    teardown,
)
from db.ris_appointments import RisAppointments
from db.ris_resources import RisResources


async def _make_resource(conn, tag, name):
    """Insert a minimal ris_resources row and return it."""
    return await conn.fetchrow(
        'INSERT INTO ris_resources (tenant_id, name, resource_type, modality) '
        'VALUES ($1, $2, $3, $4) RETURNING *',
        tag, name, 'MODALITY', 'CT',
    )


async def _make_order(conn, tag, patient_id):
    return await conn.fetchrow(
        'INSERT INTO ris_orders '
        '(tenant_id, accession_number, patient_id, patient_name, priority, status) '
        'VALUES ($1, $2, $3, $4, $5, $6) RETURNING *',
        tag, f'ACC-{uuid.uuid4().hex[:8]}', patient_id, f'Patient {patient_id}',
        'ROUTINE', 'ORDERED',
    )


class TestNoDoubleBookConcurrency:
    """Concurrent bookings for the same resource+slot — EXCLUDE admits one."""

    def test_fifty_concurrent_same_slot_yields_exactly_one_booked(self):
        async def run():
            try:
                await setup()
            except Exception:
                pytest.skip('dev database unavailable')

            tag = f'conc-{uuid.uuid4().hex[:8]}'
            try:
                set_tenant_slug(tag)
                async with get_conn() as conn:
                    resource = await _make_resource(conn, tag, f'CT-{tag}')
                    order = await _make_order(conn, tag, f'P-{tag}')

                start = '2026-08-20 09:00:00+00'
                end = '2026-08-20 09:30:00+00'

                async def try_book():
                    async with get_conn() as conn:
                        try:
                            row = await RisAppointments(conn).create({
                                'order_id': order['id'],
                                'resource_id': resource['id'],
                                'patient_id': f'P-{tag}',
                                'start_time': datetime.fromisoformat(start),
                                'end_time': datetime.fromisoformat(end),
                            })
                            return row
                        except Exception as exc:
                            from asyncpg import ExclusionViolationError
                            assert isinstance(exc, ExclusionViolationError), exc
                            return None

                results = await asyncio.gather(*[try_book() for _ in range(50)])
                successes = [r for r in results if r is not None]
                assert len(successes) == 1, f'expected 1 success, got {len(successes)}'

                # The surviving row must be queryable.
                async with get_conn() as conn:
                    count = await conn.fetchval(
                        'SELECT count(*) FROM ris_appointments '
                        'WHERE tenant_id = $1 AND start_time = $2',
                        tag, datetime.fromisoformat(start),
                    )
                    assert count == 1
            finally:
                reset_tenant_slug()
                try:
                    async with get_conn() as conn:
                        await conn.execute(
                            'DELETE FROM ris_appointments WHERE tenant_id = $1', tag)
                        await conn.execute(
                            'DELETE FROM ris_resources WHERE tenant_id = $1', tag)
                        await conn.execute(
                            'DELETE FROM ris_orders WHERE tenant_id = $1', tag)
                except Exception:
                    pass
                await teardown()

        asyncio.run(run())


class TestOverrideReleasesSlot:
    """Override deletes the conflicting row — EXCLUDE then admits the rebook."""

    def test_delete_then_rebook_same_slot_succeeds(self):
        async def run():
            try:
                await setup()
            except Exception:
                pytest.skip('dev database unavailable')

            try:
                async with get_conn() as conn:
                    tx = conn.transaction()
                    await tx.start()
                    try:
                        tag = f'ovr-{uuid.uuid4().hex[:6]}'
                        set_tenant_slug(tag)
                        resource = await _make_resource(conn, tag, f'CT-{tag}')
                        order_a = await _make_order(conn, tag, 'P-A')
                        order_b = await _make_order(conn, tag, 'P-B')

                        first = await RisAppointments(conn).create({
                            'order_id': order_a['id'],
                            'resource_id': resource['id'],
                            'patient_id': 'P-A',
                            'start_time': datetime.fromisoformat('2026-08-20 09:00:00+00'),
                            'end_time': datetime.fromisoformat('2026-08-20 09:30:00+00'),
                        })
                        assert first is not None

                        await RisAppointments(conn).delete(first['id'])

                        # Same slot is free again after the physical delete.
                        second = await RisAppointments(conn).create({
                            'order_id': order_b['id'],
                            'resource_id': resource['id'],
                            'patient_id': 'P-B',
                            'start_time': datetime.fromisoformat('2026-08-20 09:00:00+00'),
                            'end_time': datetime.fromisoformat('2026-08-20 09:30:00+00'),
                        })
                        assert second is not None
                        assert second['id'] != first['id']
                    finally:
                        await tx.rollback()
                        reset_tenant_slug()
            finally:
                await teardown()

        asyncio.run(run())


class TestRisSchedulingWriteTagging:
    """Resources and appointments must tag rows with the tenant slug (S3-20
    pattern)."""

    def test_resource_tenant_tagged(self):
        async def run():
            try:
                await setup()
            except Exception:
                pytest.skip('dev database unavailable')

            try:
                async with get_conn() as conn:
                    tx = conn.transaction()
                    await tx.start()
                    try:
                        tag = f'tag-a-{uuid.uuid4().hex[:6]}'
                        set_tenant_slug(tag)
                        row = await RisResources(conn).create({
                            'name': f'CT-{tag}', 'resource_type': 'MODALITY',
                            'modality': 'CT'})
                        assert row['tenant_id'] == tag
                    finally:
                        await tx.rollback()
                        reset_tenant_slug()
            finally:
                await teardown()

        asyncio.run(run())

    def test_appointment_tenant_tagged(self):
        async def run():
            try:
                await setup()
            except Exception:
                pytest.skip('dev database unavailable')

            try:
                async with get_conn() as conn:
                    tx = conn.transaction()
                    await tx.start()
                    try:
                        tag = f'tag-b-{uuid.uuid4().hex[:6]}'
                        set_tenant_slug(tag)
                        resource = await _make_resource(conn, tag, f'CT-{tag}')
                        order = await _make_order(conn, tag, 'P-1')
                        appt = await RisAppointments(conn).create({
                            'order_id': order['id'],
                            'resource_id': resource['id'],
                            'patient_id': 'P-1',
                            'start_time': datetime.fromisoformat('2026-08-20 09:00:00+00'),
                            'end_time': datetime.fromisoformat('2026-08-20 09:30:00+00'),
                        })
                        assert appt['tenant_id'] == tag
                    finally:
                        await tx.rollback()
                        reset_tenant_slug()
            finally:
                await teardown()

        asyncio.run(run())


class TestRisSchedulingCrossTenantReadIsolation:
    @pytest.mark.xfail(
        strict=False,
        reason='read-scoping by tenant_id not yet enforced — branch-review M-1/H-3',
    )
    def test_resources_cross_tenant_excluded(self):
        async def run():
            try:
                await setup()
            except Exception:
                pytest.skip('dev database unavailable')

            try:
                async with get_conn() as conn:
                    tx = conn.transaction()
                    await tx.start()
                    try:
                        tag_b = f'clinic-b-{uuid.uuid4().hex[:6]}'
                        set_tenant_slug(tag_b)
                        row = await _make_resource(conn, tag_b, f'CT-{tag_b}')

                        reset_tenant_slug()
                        set_tenant_slug(f'clinic-a-{uuid.uuid4().hex[:6]}')
                        rows = await conn.fetch('SELECT id FROM ris_resources')
                        ids = {r['id'] for r in rows}
                        assert row['id'] not in ids
                    finally:
                        await tx.rollback()
                        reset_tenant_slug()
            finally:
                await teardown()

        asyncio.run(run())

    @pytest.mark.xfail(
        strict=False,
        reason='read-scoping by tenant_id not yet enforced — branch-review M-1/H-3',
    )
    def test_appointments_cross_tenant_excluded(self):
        async def run():
            try:
                await setup()
            except Exception:
                pytest.skip('dev database unavailable')

            try:
                async with get_conn() as conn:
                    tx = conn.transaction()
                    await tx.start()
                    try:
                        tag_b = f'clinic-b-{uuid.uuid4().hex[:6]}'
                        set_tenant_slug(tag_b)
                        resource = await _make_resource(conn, tag_b, f'CT-{tag_b}')
                        order = await _make_order(conn, tag_b, 'P-1')
                        appt = await RisAppointments(conn).create({
                            'order_id': order['id'],
                            'resource_id': resource['id'],
                            'patient_id': 'P-1',
                            'start_time': datetime.fromisoformat('2026-08-20 09:00:00+00'),
                            'end_time': datetime.fromisoformat('2026-08-20 09:30:00+00'),
                        })

                        reset_tenant_slug()
                        set_tenant_slug(f'clinic-a-{uuid.uuid4().hex[:6]}')
                        rows = await conn.fetch('SELECT id FROM ris_appointments')
                        ids = {r['id'] for r in rows}
                        assert appt['id'] not in ids
                    finally:
                        await tx.rollback()
                        reset_tenant_slug()
            finally:
                await teardown()

        asyncio.run(run())