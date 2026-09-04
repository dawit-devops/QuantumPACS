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
    reset_request_tenant,
    reset_tenant_slug,
    set_request_tenant,
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
    """Concurrent bookings for the same resource+slot through the REAL
    scheduling path — SchedulingEngine.book() (EXCLUDE admits one).

    S4-20 reroute: previously this hammered raw RisAppointments.create;
    it now drives book(), which adds the ORDERED→SCHEDULED lifecycle
    transition, the MWL hand-off, and the H2 ExclusionViolation →
    SchedulingConflict mapping (409 semantics). Exactly one booking wins,
    exactly one order transitions, and the MWL carries a single entry.
    """

    def test_fifty_concurrent_same_slot_yields_exactly_one_booked(self):
        async def run():
            from services.scheduling.engine import SchedulingConflict, SchedulingEngine

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
                    try:
                        return await SchedulingEngine().book(
                            order_id=order['id'], patient_id=f'P-{tag}',
                            resource_id=resource['id'],
                            start_time=start, end_time=end)
                    except SchedulingConflict:
                        return None

                results = await asyncio.gather(*[try_book() for _ in range(50)])
                successes = [r for r in results if r is not None]
                assert len(successes) == 1, f'expected 1 success, got {len(successes)}'

                async with get_conn() as conn:
                    # Exactly one appointment on the slot…
                    count = await conn.fetchval(
                        'SELECT count(*) FROM ris_appointments '
                        'WHERE tenant_id = $1 AND start_time = $2',
                        tag, datetime.fromisoformat(start))
                    assert count == 1

                    # …exactly one ORDERED → SCHEDULED transition…
                    row = await conn.fetchrow(
                        'SELECT status FROM ris_orders WHERE id = $1',
                        order['id'])
                    assert row['status'] == 'SCHEDULED', row

                    # …and a single MWL entry for the booking.
                    wl = await conn.fetchval(
                        'SELECT count(*) FROM worklist_entries '
                        'WHERE accession_number = $1',
                        order['accession_number'])
                    assert wl == 1, f'expected 1 MWL entry, got {wl}'
            finally:
                reset_tenant_slug()
                try:
                    async with get_conn() as conn:
                        await conn.execute(
                            'DELETE FROM worklist_entries WHERE accession_number = $1',
                            order['accession_number'])
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
    """Scheduling-table read isolation is pool separation (ADR-029): the
    tenant-scoped connection comes from the tenant's pool (its own
    database), never the main pool — a tenant-A request cannot surface
    tenant-B's ris_resources / ris_appointments rows. The old `WHERE
    tenant_id` xfails tested a mechanism the architecture does not use;
    these assert the real routing contract (same pattern as
    test_ris_tenant_isolation.py and test_tenant_read_isolation.py).
    """

    @pytest.mark.asyncio
    async def test_tenant_scope_routes_to_tenant_pool_never_main(self):
        from unittest.mock import AsyncMock, Mock, patch

        tenant_acquire = Mock(return_value=AsyncMock())
        try:
            set_tenant_slug('clinic-b')
            set_request_tenant(tenant_acquire)
            with patch('db.conn.database.acquire') as main_acquire:
                main_acquire.side_effect = AssertionError(
                    'main pool must not be used inside a tenant scope')
                async with get_conn() as conn:
                    assert conn is not None
            tenant_acquire.assert_called_once()
        finally:
            reset_request_tenant()
            reset_tenant_slug()

    @pytest.mark.asyncio
    async def test_slug_change_does_not_reroute_mid_scope(self):
        from unittest.mock import AsyncMock, Mock

        tenant_acquire = Mock(return_value=AsyncMock())
        try:
            set_request_tenant(tenant_acquire)
            set_tenant_slug('clinic-alpha')
            async with get_conn() as conn:
                assert conn is not None
                set_tenant_slug('clinic-omega')
                async with get_conn() as conn2:
                    assert conn2 is not None
            assert tenant_acquire.call_count == 2
        finally:
            reset_request_tenant()
            reset_tenant_slug()

    def test_real_write_tags_resources_and_appointments(self):
        """Real-DB half of the contract (rolled back): writes in tenant B's
        scope tag ris_resources / ris_appointments — the lineage tag that
        survives pool separation for the shared-DB tenant."""

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
                        assert appt['tenant_id'] == tag_b
                        stored = await conn.fetchrow(
                            'SELECT tenant_id FROM ris_resources WHERE id = $1',
                            resource['id'],
                        )
                        assert stored['tenant_id'] == tag_b
                    finally:
                        await tx.rollback()
                        reset_tenant_slug()
            finally:
                await teardown()

        asyncio.run(run())


class TestOverrideAtomicity:
    """H3: override delete→insert must be atomic — a failed rebook restores
    the original appointment instead of silently losing it."""

    def test_failed_override_insert_restores_deleted_appointment(self):
        async def run():
            try:
                await setup()
            except Exception:
                pytest.skip('dev database unavailable')

            tag = f'ovr-{uuid.uuid4().hex[:8]}'
            try:
                set_tenant_slug(tag)
                async with get_conn() as conn:
                    resource = await _make_resource(conn, tag, f'CT-{tag}')
                    order_a = await _make_order(conn, tag, f'P-{tag}')

                from services.scheduling.engine import SchedulingConflict, SchedulingEngine

                booked = await SchedulingEngine().book(
                    order_id=order_a['id'], patient_id=f'P-{tag}',
                    resource_id=resource['id'],
                    start_time='2026-08-20 09:00:00+00',
                    end_time='2026-08-20 09:30:00+00',
                )
                assert booked['id'] is not None

                from unittest.mock import patch

                from asyncpg import ExclusionViolationError

                # Second booking overlaps; pre-check admits an override, but the
                # insert then hits the EXCLUDE backstop. H3: the delete of the
                # original must roll back with the failed insert.
                with patch.object(RisAppointments, 'create',
                                  side_effect=ExclusionViolationError(
                                      'conflicting key value violates exclusion constraint "no_double_book"')):
                    with pytest.raises(SchedulingConflict):
                        await SchedulingEngine().book(
                            order_id=order_a['id'], patient_id=f'P-{tag}',
                            resource_id=resource['id'],
                            start_time='2026-08-20 09:15:00+00',
                            end_time='2026-08-20 09:45:00+00',
                            override_reason='urgent stat',
                        )

                async with get_conn() as conn:
                    still = await conn.fetchval(
                        'SELECT count(*) FROM ris_appointments WHERE id = $1',
                        booked['id'])
                    assert still == 1, 'override delete was not rolled back'
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
