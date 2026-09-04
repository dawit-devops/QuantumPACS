"""S4-19 — Scheduling E2E over the real DB (order -> book -> worklist).

Live-wire test of the whole scheduling pipeline: create order, book via
the engine (which must gate, transition the order to SCHEDULED, and hand
off to worklist_entries), reschedule, override a conflict, cancel, and
read the audit timeline. Uses the real pool (engine acquires its own
connections), rows are cleaned up by the unique tenant tag. Skipped when
the dev DB is unreachable, mirroring test_ris_hl7_e2e.
"""

import uuid

import asyncpg
import pytest

from config import load_config
from db.audit_log import AuditLog
from db.conn import get_conn, reset_tenant_slug, set_tenant_slug
from db.ris_orders import RisOrders
from db.ris_resources import RisResources
from services.scheduling.engine import SchedulingEngine, SchedulingConflict


@pytest.fixture(scope='module')
async def live_db():
    cfg = load_config()
    try:
        conn = await asyncpg.connect(
            user=cfg['db_user'], password=cfg['db_password'],
            database=cfg['db_database'], host=cfg['db_host'],
            port=int(cfg['db_port']),
        )
    except Exception:
        pytest.skip('dev database unavailable')
    try:
        yield conn
    finally:
        await conn.close()


@pytest.fixture(scope='module')
async def live_engine():
    import db.conn
    created = db.conn.database._pool is None
    if created:
        await db.conn.setup(pool_size=4)
    try:
        yield SchedulingEngine()
    finally:
        if created:
            await db.conn.database.close()


@pytest.mark.asyncio(loop_scope='module')
class TestSchedulingE2E:
    async def test_order_book_worklist_reschedule_override_cancel(
            self, live_engine, live_db):
        tag = f'e2e-{uuid.uuid4().hex[:8]}'
        set_tenant_slug(tag)

        async def cleanup():
            reset_tenant_slug()
            try:
                async with get_conn() as conn:
                    await conn.execute(
                        'DELETE FROM ris_appointments WHERE tenant_id = $1', tag)
                    await conn.execute(
                        'DELETE FROM worklist_entries WHERE tenant_id = $1', tag)
                    await conn.execute(
                        'DELETE FROM ris_resources WHERE tenant_id = $1', tag)
                    await conn.execute(
                        'DELETE FROM ris_orders WHERE tenant_id = $1', tag)
            except Exception:
                pass

        try:
            async with get_conn() as conn:
                resource = await RisResources(conn).create({
                    'name': f'CT-{tag}', 'resource_type': 'MODALITY',
                    'modality': 'CT'})
                order = await RisOrders(conn).create({
                    'accession_number': f'E2E-{uuid.uuid4().hex[:8]}',
                    'patient_id': f'P-{tag}', 'patient_name': 'E2E Patient',
                    'referring_physician': 'Dr. E2E',
                    'clinical_indication': 'screening', 'priority': 'ROUTINE',
                    'created_by': 'e2e'})
                assert order['status'] == 'ORDERED'
                order_id = order['id']
                resource_id = resource['id']

            # 1. Book — order -> SCHEDULED + appointment + worklist entry.
            appt = await live_engine.book(
                order_id=order_id, patient_id=f'P-{tag}',
                resource_id=resource_id,
                start_time='2026-08-20 09:00:00+00',
                end_time='2026-08-20 09:30:00+00',
                reason='e2e')
            assert appt['status'] == 'SCHEDULED'

            async with get_conn() as conn:
                order_after = await conn.fetchrow(
                    'SELECT status FROM ris_orders WHERE id = $1', order_id)
                assert order_after['status'] == 'SCHEDULED'
                appt_row = await conn.fetchrow(
                    'SELECT id, status FROM ris_appointments WHERE id = $1',
                    appt['id'])
                assert appt_row is not None
                wl = await conn.fetchval(
                    'SELECT count(*) FROM worklist_entries '
                    'WHERE tenant_id = $1 AND status = $2', tag, 'scheduled')
                assert wl >= 1

            # 2. Double-booking the same slot must conflict.
            with pytest.raises(SchedulingConflict):
                await live_engine.book(
                    order_id=order_id, patient_id=f'P-{tag}',
                    resource_id=resource_id,
                    start_time='2026-08-20 09:00:00+00',
                    end_time='2026-08-20 09:30:00+00')

            # 3. Reschedule to a free slot.
            moved = await live_engine.reschedule(
                appointment_id=appt['id'],
                new_start_time='2026-08-20 10:00:00+00',
                new_end_time='2026-08-20 10:30:00+00',
                reason='e2e-reschedule')
            assert moved['start_time'].hour == 10

            # 4. Override a conflicting booking with a mandatory reason.
            async with get_conn() as conn:
                order2 = await RisOrders(conn).create({
                    'accession_number': f'E2E-{uuid.uuid4().hex[:8]}',
                    'patient_id': f'P2-{tag}', 'patient_name': 'E2E Patient 2',
                    'priority': 'URGENT', 'created_by': 'e2e'})
            replaced = await live_engine.book(
                order_id=order2['id'], patient_id=f'P2-{tag}',
                resource_id=resource_id,
                start_time='2026-08-20 10:00:00+00',
                end_time='2026-08-20 10:30:00+00',
                override_reason='e2e emergency rebook')
            assert replaced['id'] != appt['id']
            async with get_conn() as conn:
                gone = await conn.fetchval(
                    'SELECT count(*) FROM ris_appointments WHERE id = $1',
                    appt['id'])
                assert gone == 0

            # 5. Cancel releases the slot and cancels the order.
            cancelled = await live_engine.cancel(
                appointment_id=replaced['id'], reason='e2e no-show')
            assert cancelled['status'] == 'CANCELLED'
            async with get_conn() as conn:
                order2_after = await conn.fetchrow(
                    'SELECT status FROM ris_orders WHERE id = $1', order2['id'])
                assert order2_after['status'] == 'CANCELLED'

            # 6. Audit timeline for the order: transitions + booking events.
            async with get_conn() as conn:
                events = await AuditLog(conn).query(
                    resource_id=order_id, limit=50)
            event_types = {e['event_type'] for e in events}
            assert 'ORDER_STATUS_TRANSITION' in event_types
        finally:
            await cleanup()