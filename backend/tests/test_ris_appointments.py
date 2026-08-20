"""S4-09 — ris_appointments persistence + EXCLUDE conflict guard (B3).

Real-DB repository tests: the EXCLUDE constraint is the scheduling
engine's last line of defense against double-booking, so it must be
verified against a real Postgres, not a mock. Rows are created inside a
transaction that is rolled back; schema DDL ships with the test.
"""

import asyncio
import uuid

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
