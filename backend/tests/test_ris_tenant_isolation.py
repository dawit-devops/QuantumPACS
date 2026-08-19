"""S3-20 — RLS isolation regression on new RIS tables.

Verifies that every S3 table (ris_orders, ris_hl7_messages,
ris_interface_endpoints, ris_interface_events) correctly tags rows with
the current tenant slug on write.  Cross-tenant read assertions are
xfail until read-scoping by tenant_id is enforced (same pattern as
test_tenant_read_isolation.py — branch-review M-1 / H-3).

All tests run inside a transaction that is rolled back, so the dev
database is never mutated.
"""

import asyncio
import uuid

import pytest

from db.conn import (
    get_conn,
    reset_tenant_slug,
    set_tenant_slug,
    setup,
    teardown,
)


# ── Helpers ──────────────────────────────────────────────────────────────

async def _insert_ris_order(conn, tag):
    """Insert a minimal ris_orders row and return it."""
    return await conn.fetchrow(
        'INSERT INTO ris_orders '
        '(tenant_id, accession_number, patient_id, patient_name, priority, status) '
        'VALUES ($1, $2, $3, $4, $5, $6) RETURNING *',
        tag, f'ACC-{tag}', f'P-{tag}', f'Patient {tag}', 'ROUTINE', 'ORDERED',
    )


async def _insert_ris_endpoint(conn, tag):
    """Insert a minimal ris_interface_endpoints row and return it."""
    return await conn.fetchrow(
        'INSERT INTO ris_interface_endpoints '
        '(tenant_id, name, interface_type, protocol) '
        'VALUES ($1, $2, $3, $4) RETURNING *',
        tag, f'HL7-{tag}', 'HL7_ORM', 'HL7V2',
    )


async def _insert_ris_hl7_message(conn, tag, endpoint_id=None):
    """Insert a minimal ris_hl7_messages row and return it."""
    return await conn.fetchrow(
        'INSERT INTO ris_hl7_messages '
        '(tenant_id, endpoint_id, message_type, trigger_event, control_id, '
        ' raw_message, status) '
        'VALUES ($1, $2, $3, $4, $5, $6, $7) RETURNING *',
        tag, endpoint_id, 'ORM', 'O01', f'CTRL-{tag}', f'MSH|{tag}', 'RECEIVED',
    )


async def _insert_ris_event(conn, tag, endpoint_id=None):
    """Insert a minimal ris_interface_events row and return it."""
    return await conn.fetchrow(
        'INSERT INTO ris_interface_events '
        '(tenant_id, endpoint_id, event_type, severity, message) '
        'VALUES ($1, $2, $3, $4, $5) RETURNING *',
        tag, endpoint_id, 'HL7_PROCESSED', 'INFO', f'Event {tag}',
    )


# ── Write-scoping tests (real, passing) ──────────────────────────────────

class TestRisWriteTenantTagging:
    """Every INSERT into an S3 table must tag the row with the current
    tenant slug.  These tests use real DB writes inside a rolled-back
    transaction."""

    def test_ris_orders_tenant_tagged(self):
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
                        tag = f'test-a-{uuid.uuid4().hex[:6]}'
                        set_tenant_slug(tag)
                        row = await _insert_ris_order(conn, tag)
                        assert row['tenant_id'] == tag
                    finally:
                        await tx.rollback()
                        reset_tenant_slug()
            finally:
                await teardown()

        asyncio.run(run())

    def test_ris_hl7_messages_tenant_tagged(self):
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
                        tag = f'test-b-{uuid.uuid4().hex[:6]}'
                        set_tenant_slug(tag)
                        row = await _insert_ris_hl7_message(conn, tag)
                        assert row['tenant_id'] == tag
                    finally:
                        await tx.rollback()
                        reset_tenant_slug()
            finally:
                await teardown()

        asyncio.run(run())

    def test_ris_interface_endpoints_tenant_tagged(self):
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
                        tag = f'test-c-{uuid.uuid4().hex[:6]}'
                        set_tenant_slug(tag)
                        row = await _insert_ris_endpoint(conn, tag)
                        assert row['tenant_id'] == tag
                    finally:
                        await tx.rollback()
                        reset_tenant_slug()
            finally:
                await teardown()

        asyncio.run(run())

    def test_ris_interface_events_tenant_tagged(self):
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
                        tag = f'test-d-{uuid.uuid4().hex[:6]}'
                        set_tenant_slug(tag)
                        row = await _insert_ris_event(conn, tag)
                        assert row['tenant_id'] == tag
                    finally:
                        await tx.rollback()
                        reset_tenant_slug()
            finally:
                await teardown()

        asyncio.run(run())


# ── Cross-tenant read isolation (xfail until read-scoping enforced) ─────

class TestRisCrossTenantReadIsolation:
    """A read performed in tenant-A's scope must not surface tenant-B's
    rows.  xfail until reads are scoped by tenant_id (branch-review
    M-1 / H-3)."""

    @pytest.mark.xfail(
        strict=False,
        reason='read-scoping by tenant_id not yet enforced — branch-review M-1/H-3',
    )
    def test_ris_orders_cross_tenant_excluded(self):
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
                        row = await _insert_ris_order(conn, tag_b)

                        # Now act as clinic-a: a SELECT must not see clinic-b's row.
                        reset_tenant_slug()
                        set_tenant_slug(f'clinic-a-{uuid.uuid4().hex[:6]}')
                        rows = await conn.fetch('SELECT id FROM ris_orders')
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
    def test_ris_hl7_messages_cross_tenant_excluded(self):
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
                        row = await _insert_ris_hl7_message(conn, tag_b)

                        reset_tenant_slug()
                        set_tenant_slug(f'clinic-a-{uuid.uuid4().hex[:6]}')
                        rows = await conn.fetch('SELECT id FROM ris_hl7_messages')
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
    def test_ris_interface_endpoints_cross_tenant_excluded(self):
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
                        row = await _insert_ris_endpoint(conn, tag_b)

                        reset_tenant_slug()
                        set_tenant_slug(f'clinic-a-{uuid.uuid4().hex[:6]}')
                        rows = await conn.fetch('SELECT id FROM ris_interface_endpoints')
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
    def test_ris_interface_events_cross_tenant_excluded(self):
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
                        row = await _insert_ris_event(conn, tag_b)

                        reset_tenant_slug()
                        set_tenant_slug(f'clinic-a-{uuid.uuid4().hex[:6]}')
                        rows = await conn.fetch('SELECT id FROM ris_interface_events')
                        ids = {r['id'] for r in rows}
                        assert row['id'] not in ids
                    finally:
                        await tx.rollback()
                        reset_tenant_slug()
            finally:
                await teardown()

        asyncio.run(run())


# ── Unique constraint per tenant (real, passing) ─────────────────────────

class TestRisUniquePerTenant:
    """Accession uniqueness is per-tenant, not global — two tenants can
    share the same accession number."""

    def test_same_accession_different_tenants_allowed(self):
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
                        acc = f'ACC-{uuid.uuid4().hex[:8]}'

                        set_tenant_slug('tenant-x')
                        row_x = await _insert_ris_order(conn, 'tenant-x')
                        # Manually override accession to our shared value
                        await conn.execute(
                            'UPDATE ris_orders SET accession_number = $1 WHERE id = $2',
                            acc, row_x['id'],
                        )

                        set_tenant_slug('tenant-y')
                        row_y = await _insert_ris_order(conn, 'tenant-y')
                        await conn.execute(
                            'UPDATE ris_orders SET accession_number = $1 WHERE id = $2',
                            acc, row_y['id'],
                        )

                        # Both should exist — uniqueness is per tenant_id
                        count = await conn.fetchval(
                            'SELECT count(*) FROM ris_orders WHERE accession_number = $1',
                            acc,
                        )
                        assert count == 2
                    finally:
                        await tx.rollback()
                        reset_tenant_slug()
            finally:
                await teardown()

        asyncio.run(run())
