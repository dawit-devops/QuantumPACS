"""S4-09 — ris_appointments persistence + EXCLUDE conflict guard (B3).

Real-DB repository tests: the EXCLUDE constraint is the scheduling
engine's last line of defense against double-booking, so it must be
verified against a real Postgres, not a mock. Rows are created inside a
transaction that is rolled back; schema DDL ships with the test.
"""

import asyncio
import uuid
from datetime import datetime

import pytest

from db.conn import get_conn, reset_tenant_slug, set_tenant_slug, setup, teardown


class TestRisAppointmentsRepo:
    async def _schema(self, conn):
        from db.ris_appointments import RisAppointments
        from db.ris_resources import RisResources
        await RisResources(conn).sync_db()
        await RisAppointments(conn).sync_db()

    async def _resource(self, conn, tag):
        from db.ris_resources import RisResources
        return await RisResources(conn).create({
            'name': f'CT Room {tag}',
            'resource_type': 'ROOM',
            'modality': 'CT',
        })

    def test_book_slot_persists_with_tenant_tag(self):
        async def run():
            try:
                await setup()
            except Exception:
                pytest.skip('dev database unavailable')

            tag = f'appt-{uuid.uuid4().hex[:6]}'
            try:
                async with get_conn() as conn:
                    tx = conn.transaction()
                    await tx.start()
                    try:
                        set_tenant_slug(tag)
                        await self._schema(conn)
                        resource = await self._resource(conn, tag)
                        row = await conn.fetchrow(
                            'INSERT INTO ris_appointments '
                            '(tenant_id, resource_id, patient_id, start_time, end_time) '
                            "VALUES ($1, $2, 'MRN-1', '2026-08-20 09:00+00', "
                            "'2026-08-20 09:30+00') RETURNING *",
                            tag, resource['id'],
                        )
                        assert row['id'] is not None
                        assert row['tenant_id'] == tag
                        assert row['status'] == 'SCHEDULED'
                    finally:
                        await tx.rollback()
                        reset_tenant_slug()
            finally:
                await teardown()

        asyncio.run(run())

    def test_overlapping_same_resource_rejected(self):
        async def run():
            try:
                await setup()
            except Exception:
                pytest.skip('dev database unavailable')

            tag = f'appt-{uuid.uuid4().hex[:6]}'
            try:
                async with get_conn() as conn:
                    tx = conn.transaction()
                    await tx.start()
                    try:
                        set_tenant_slug(tag)
                        await self._schema(conn)
                        resource = await self._resource(conn, tag)
                        await conn.execute(
                            'INSERT INTO ris_appointments '
                            '(tenant_id, resource_id, patient_id, start_time, end_time) '
                            "VALUES ($1, $2, 'MRN-1', '2026-08-20 09:00+00', "
                            "'2026-08-20 09:30+00')",
                            tag, resource['id'],
                        )
                        from asyncpg.exceptions import ExclusionViolationError
                        with pytest.raises(ExclusionViolationError):
                            await conn.execute(
                                'INSERT INTO ris_appointments '
                                '(tenant_id, resource_id, patient_id, start_time, end_time) '
                                "VALUES ($1, $2, 'MRN-2', '2026-08-20 09:15+00', "
                                "'2026-08-20 09:45+00')",
                                tag, resource['id'],
                            )
                    finally:
                        await tx.rollback()
                        reset_tenant_slug()
            finally:
                await teardown()

        asyncio.run(run())

    def test_adjacent_slots_allowed(self):
        async def run():
            try:
                await setup()
            except Exception:
                pytest.skip('dev database unavailable')

            tag = f'appt-{uuid.uuid4().hex[:6]}'
            try:
                async with get_conn() as conn:
                    tx = conn.transaction()
                    await tx.start()
                    try:
                        set_tenant_slug(tag)
                        await self._schema(conn)
                        resource = await self._resource(conn, tag)
                        await conn.execute(
                            'INSERT INTO ris_appointments '
                            '(tenant_id, resource_id, patient_id, start_time, end_time) '
                            "VALUES ($1, $2, 'MRN-1', '2026-08-20 09:00+00', "
                            "'2026-08-20 09:30+00')",
                            tag, resource['id'],
                        )
                        row = await conn.fetchrow(
                            'INSERT INTO ris_appointments '
                            '(tenant_id, resource_id, patient_id, start_time, end_time) '
                            "VALUES ($1, $2, 'MRN-2', '2026-08-20 09:30+00', "
                            "'2026-08-20 10:00+00') RETURNING id",
                            tag, resource['id'],
                        )
                        assert row['id'] is not None
                    finally:
                        await tx.rollback()
                        reset_tenant_slug()
            finally:
                await teardown()

        asyncio.run(run())

    def test_same_time_different_resource_allowed(self):
        async def run():
            try:
                await setup()
            except Exception:
                pytest.skip('dev database unavailable')

            tag = f'appt-{uuid.uuid4().hex[:6]}'
            try:
                async with get_conn() as conn:
                    tx = conn.transaction()
                    await tx.start()
                    try:
                        set_tenant_slug(tag)
                        await self._schema(conn)
                        room_a = await self._resource(conn, f'{tag}a')
                        room_b = await self._resource(conn, f'{tag}b')
                        await conn.execute(
                            'INSERT INTO ris_appointments '
                            '(tenant_id, resource_id, patient_id, start_time, end_time) '
                            "VALUES ($1, $2, 'MRN-1', '2026-08-20 09:00+00', "
                            "'2026-08-20 09:30+00')",
                            tag, room_a['id'],
                        )
                        row = await conn.fetchrow(
                            'INSERT INTO ris_appointments '
                            '(tenant_id, resource_id, patient_id, start_time, end_time) '
                            "VALUES ($1, $2, 'MRN-2', '2026-08-20 09:00+00', "
                            "'2026-08-20 09:30+00') RETURNING id",
                            tag, room_b['id'],
                        )
                        assert row['id'] is not None
                    finally:
                        await tx.rollback()
                        reset_tenant_slug()
            finally:
                await teardown()

        asyncio.run(run())

class TestOrderFkBackstop(TestRisAppointmentsRepo):
    """C-4: ris_appointments.order_id must reference a real ris_orders row —
    the migration-076 FK makes dangling references impossible even if the
    engine's pre-check is bypassed."""

    def test_insert_with_unknown_order_id_fails_fk(self):
        async def run():
            from asyncpg.exceptions import ForeignKeyViolationError

            try:
                await setup()
            except Exception:
                pytest.skip('dev database unavailable')

            tag = f'fk-{uuid.uuid4().hex[:6]}'
            try:
                async with get_conn() as conn:
                    tx = conn.transaction()
                    await tx.start()
                    try:
                        set_tenant_slug(tag)
                        await self._schema(conn)
                        resource = await self._resource(conn, tag)
                        with pytest.raises(ForeignKeyViolationError):
                            await conn.fetchrow(
                                'INSERT INTO ris_appointments '
                                '(tenant_id, order_id, resource_id, patient_id,'
                                ' start_time, end_time) '
                                "VALUES ($1, '00000000-0000-0000-0000-000000000000',"
                                " $2, 'MRN-1', '2026-08-20 09:00+00', "
                                "'2026-08-20 09:30+00')",
                                tag, resource['id'])
                    finally:
                        await tx.rollback()
            finally:
                reset_tenant_slug()
                await teardown()

        asyncio.run(run())


class TestForResourcePriority:
    """C4 support (GAP_AUDIT_TDD_PIPELINE.md): the calendar day view needs
    each block's priority for STAT/URGENT badges — priority lives on the
    order, so for_resource must surface it via a LEFT JOIN."""

    @staticmethod
    async def _schema(conn):
        from db.ris_appointments import RisAppointments
        from db.ris_resources import RisResources
        await RisResources(conn).sync_db()
        await RisAppointments(conn).sync_db()

    @staticmethod
    async def _resource(conn, tag):
        from db.ris_resources import RisResources
        return await RisResources(conn).create({
            'name': f'CT Room {tag}',
            'resource_type': 'ROOM',
            'modality': 'CT',
        })

    def test_for_resource_returns_order_priority(self):
        async def run():
            try:
                await setup()
            except Exception:
                pytest.skip('dev database unavailable')

            tag = uuid.uuid4().hex[:6]
            from db.conn import get_conn
            from db.ris_appointments import RisAppointments
            from db.ris_orders import RisOrders

            set_tenant_slug('default')
            try:
                async with get_conn() as conn:
                    await self._schema(conn)
                    order = await RisOrders(conn).create({
                        'accession_number': f'ACC-C4-{tag}',
                        'patient_id': f'P-C4-{tag}',
                        'priority': 'STAT',
                    })
                    resource = await self._resource(conn, tag)
                    appt = await RisAppointments(conn).create({
                        'order_id': order['id'],
                        'resource_id': resource['id'],
                        'patient_id': f'P-C4-{tag}',
                        'start_time': '2026-09-01 09:00:00+00',
                        'end_time': '2026-09-01 09:30:00+00',
                    })
                    rows = await RisAppointments(conn).for_resource(
                        resource['id'],
                        datetime.fromisoformat('2026-09-01T00:00:00+00:00'),
                        datetime.fromisoformat('2026-09-02T00:00:00+00:00'),
                    )
                    match = [r for r in rows if r['id'] == appt['id']]
                    assert match, 'booked appointment must be returned'
                    assert match[0].get('priority') == 'STAT', (
                        'for_resource must join the order priority for '
                        'day-view badges')
            finally:
                try:
                    async with get_conn() as conn:
                        await conn.execute(
                            'DELETE FROM ris_appointments WHERE patient_id = $1',
                            f'P-C4-{tag}')
                        await conn.execute(
                            'DELETE FROM ris_orders WHERE accession_number = $1',
                            f'ACC-C4-{tag}')
                        await conn.execute(
                            'DELETE FROM ris_resources WHERE name = $1',
                            f'CT Room {tag}')
                finally:
                    reset_tenant_slug()

        asyncio.run(run())


class TestForDayAggregate:
    """FD-06: for_day lists every resource's appointments for a day window
    with modality/room/patient-name joins and optional filters — the data
    behind the front-desk "Today's Schedule"."""

    @staticmethod
    async def _schema(conn):
        from db.ris_appointments import RisAppointments
        from db.ris_resources import RisResources
        await RisResources(conn).sync_db()
        await RisAppointments(conn).sync_db()

    @staticmethod
    async def _resource(conn, tag, modality):
        from db.ris_resources import RisResources
        return await RisResources(conn).create({
            'name': f'{modality} Room {tag}',
            'resource_type': 'ROOM',
            'modality': modality,
            'location': f'{modality}-1',
        })

    def test_for_day_aggregates_resources_with_joins_and_filters(self):
        async def run():
            try:
                await setup()
            except Exception:
                pytest.skip('dev database unavailable')

            tag = uuid.uuid4().hex[:6]
            from db.conn import get_conn
            from db.ris_appointments import RisAppointments

            set_tenant_slug('default')
            try:
                async with get_conn() as conn:
                    tx = conn.transaction()
                    await tx.start()
                    try:
                        await self._schema(conn)
                        ct = await self._resource(conn, tag, 'CT')
                        mr = await self._resource(conn, tag, 'MR')
                        await conn.execute(
                            'INSERT INTO ris_appointments '
                            '(tenant_id, resource_id, patient_id, start_time, end_time) '
                            "VALUES ($1, $2, 'MRN-A', '2026-09-01 09:00+00', "
                            "'2026-09-01 09:30+00')",
                            'default', ct['id'],
                        )
                        await conn.execute(
                            'INSERT INTO ris_appointments '
                            '(tenant_id, resource_id, patient_id, start_time, end_time) '
                            "VALUES ($1, $2, 'MRN-B', '2026-09-01 10:00+00', "
                            "'2026-09-01 10:30+00')",
                            'default', mr['id'],
                        )
                        repo = RisAppointments(conn)
                        day_start = datetime.fromisoformat(
                            '2026-09-01T00:00:00+00:00')
                        day_end = datetime.fromisoformat(
                            '2026-09-02T00:00:00+00:00')
                        rows = await repo.for_day(day_start, day_end)
                        assert len(rows) == 2, 'both resources must appear'
                        modalities = {r['modality'] for r in rows}
                        assert modalities == {'CT', 'MR'}
                        assert all(r['room'] for r in rows)
                        # modality filter narrows to CT only
                        ct_rows = await repo.for_day(
                            day_start, day_end, modality='CT')
                        assert len(ct_rows) == 1
                        assert ct_rows[0]['modality'] == 'CT'
                    finally:
                        await tx.rollback()
                        reset_tenant_slug()
            finally:
                await teardown()

        asyncio.run(run())
