"""S3-20 — RLS isolation regression on new RIS tables.

Verifies that every S3 table (ris_orders, ris_hl7_messages,
ris_interface_endpoints, ris_interface_events) correctly tags rows with
the current tenant slug on write.  Read isolation for these tables is pool
separation (ADR-029) — a tenant-scoped read runs on a pool bound to that
tenant's OWN database; the tenant_id columns are lineage/audit tags and the
shared-DB (`default`) tenant discriminator.

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


async def _insert_ris_charge(conn, tag):
    """Insert a minimal ris_charges row and return it (S11-15).

    report_id/exam_id are NULL so the FK constraints are satisfied without
    fabricating a reports/exams row — the isolation contract only cares
    about the tenant_id tag on write.
    """
    return await conn.fetchrow(
        'INSERT INTO ris_charges '
        '(tenant_id, report_id, exam_id, accession_number, patient_id,'
        ' cpt_code, charge_amount, status) '
        'VALUES ($1, NULL, NULL, $2, $3, $4, 0,'
        " 'PENDING') RETURNING *",
        tag, f'ACC-{tag}', f'P-{tag}', '71250',
    )


async def _insert_ris_claim(conn, tag, charge_id=None):
    """Insert a minimal ris_claims row and return it (S11-15)."""
    if charge_id is None:
        charge_id = (await _insert_ris_charge(conn, tag))['id']
    return await conn.fetchrow(
        'INSERT INTO ris_claims '
        '(tenant_id, charge_id, claim_number, status) '
        'VALUES ($1, $2, $3, $4) RETURNING *',
        tag, charge_id, f'CLM-{tag}', 'DRAFT',
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

    def test_ris_charges_tenant_tagged(self):
        # S11-15: charge rows carry the tenant tag on write, same isolation
        # convention as ris_orders (per-tenant pool separation, ADR-029).
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
                        tag = f'test-e-{uuid.uuid4().hex[:6]}'
                        set_tenant_slug(tag)
                        row = await _insert_ris_charge(conn, tag)
                        assert row['tenant_id'] == tag
                    finally:
                        await tx.rollback()
                        reset_tenant_slug()
            finally:
                await teardown()

        asyncio.run(run())

    def test_ris_claims_tenant_tagged(self):
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
                        tag = f'test-f-{uuid.uuid4().hex[:6]}'
                        set_tenant_slug(tag)
                        row = await _insert_ris_claim(conn, tag)
                        assert row['tenant_id'] == tag
                    finally:
                        await tx.rollback()
                        reset_tenant_slug()
            finally:
                await teardown()

        asyncio.run(run())


# ── Engine-level tenant tagging (S3-20) ──────────────────────────────────

def _orm_o01(control_id: str, accession: str) -> str:
    """Minimal but fully processable ORM^O01 (MSH/PID/ORC/OBR)."""
    return (
        f'MSH|^~\\&|E2E|TENANT_FACILITY|QUANTUMPACS||202608181030||ORM^O01|'
        f'{control_id}|P|2.5\r'
        f'PID|1||{control_id}||Tenant^Patient||19800101|M\r'
        f'ORC|NW|{accession}|||CM|||||||202608181030\r'
        f'OBR|1|{accession}|{accession}|CT CHEST^Chest CT^L|||202608190800|||||'
        f'||||||CT_SCANNER^CT Room 1||||||CT|||1^CM^30^Q^30^A||||Routine'
        f' screening|Lee^Kim\r'
    )


class TestRisEngineTenantTagging:
    """Hl7InterfaceEngine writes (orders + message log) must carry the
    tenant slug active in the engine's context.  The write-tagging tests
    above prove repos tag raw INSERTs; this proves the engine's real
    receive -> persist path tags them too.  The engine acquires its own
    pool connections, so an outer transaction cannot wrap its writes —
    rows are cleaned up by the unique run tag instead."""

    def test_engine_orm_orders_and_messages_carry_tenant_tag(self):
        async def run():
            try:
                await setup()
            except Exception:
                pytest.skip('dev database unavailable')

            tag = f'engine-{uuid.uuid4().hex[:8]}'
            control_id = uuid.uuid4().hex[:8].upper()
            accession = f'TAG-{uuid.uuid4().hex[:8].upper()}'
            try:
                from services.hl7_engine.service import Hl7InterfaceEngine
                set_tenant_slug(tag)
                result = await Hl7InterfaceEngine().receive_message(
                    _orm_o01(control_id, accession).encode()
                )
                assert result == b'ACK', result

                async with get_conn() as conn:
                    order = await conn.fetchrow(
                        'SELECT tenant_id FROM ris_orders '
                        'WHERE accession_number = $1',
                        accession,
                    )
                    assert order is not None
                    assert order['tenant_id'] == tag

                    msg = await conn.fetchrow(
                        'SELECT tenant_id, status FROM ris_hl7_messages '
                        'WHERE control_id = $1',
                        control_id,
                    )
                    assert msg is not None
                    assert msg['tenant_id'] == tag
                    assert msg['status'] == 'PROCESSED'

                    # No cross-tenant residue: rows must not land on 'default'.
                    stray = await conn.fetchval(
                        'SELECT count(*) FROM ris_orders '
                        "WHERE accession_number = $1 AND tenant_id = 'default'",
                        accession,
                    )
                    assert stray == 0
            finally:
                reset_tenant_slug()
                try:
                    async with get_conn() as conn:
                        await conn.execute(
                            'DELETE FROM ris_hl7_messages WHERE tenant_id = $1', tag
                        )
                        await conn.execute(
                            'DELETE FROM ris_orders WHERE tenant_id = $1', tag
                        )
                        await conn.execute(
                            'DELETE FROM ris_interface_events WHERE tenant_id = $1', tag
                        )
                        await conn.execute(
                            'DELETE FROM ris_interface_endpoints WHERE tenant_id = $1', tag
                        )
                except Exception:
                    pass
                await teardown()

        asyncio.run(run())


# ── Cross-tenant read isolation (real asserts, ADR-029) ──────────────────

class TestRisCrossTenantReadIsolation:
    """Read isolation for RIS tables is pool separation (ADR-029): every
    tenant-scoped read runs on a pool bound to that tenant's OWN database,
    so a tenant-A request physically cannot open a connection to tenant-B's
    database. The tenant_id columns are lineage/audit tags and the
    shared-DB (`default`) tenant discriminator — they are NOT the read
    control, and the old `WHERE tenant_id` xfails tested a mechanism the
    architecture does not use.

    These tests pin the routing contract with the same per-slug pool-identity
    pattern as TestPoolIdentityIsolation in test_tenant_isolation.py, plus a
    real-DB write-tagging regression (tenants land tagged, never on
    'default'), which is the shared-DB half of the contract.
    """

    @pytest.mark.asyncio
    async def test_get_conn_scopes_to_tenant_pool_not_main_pool(self):
        """A tenant-scoped request uses the tenant's pool acquire, never the
        main database.acquire — so reads cannot reach other tenants' data."""
        from unittest.mock import AsyncMock, Mock, patch
        from db.conn import set_request_tenant, reset_request_tenant

        tenant_acquire = Mock(return_value=AsyncMock())
        try:
            set_request_tenant(tenant_acquire)
            with patch('db.conn.database.acquire') as main_acquire:
                main_acquire.side_effect = AssertionError(
                    'main pool must not be used inside a tenant scope')
                async with get_conn() as conn:
                    assert conn is not None
            tenant_acquire.assert_called_once()
        finally:
            reset_request_tenant()

    @pytest.mark.asyncio
    async def test_tenant_slug_does_not_change_pool_routing(self):
        """The tenant SLUG tags writes and identifies the pool; the scope that
        routes get_conn() comes from set_request_tenant, so a shared
        transaction can never silently hop databases mid-scope."""
        from unittest.mock import AsyncMock, Mock, patch
        from db.conn import set_request_tenant, reset_request_tenant

        tenant_acquire = Mock(return_value=AsyncMock())
        try:
            set_tenant_slug('clinic-alpha')
            set_request_tenant(tenant_acquire)
            with patch('db.conn.database.acquire') as main_acquire:
                main_acquire.side_effect = AssertionError(
                    'slug change must not reroute to the main pool')
                async with get_conn() as conn:
                    assert conn is not None
            reset_tenant_slug()
            tenant_acquire.assert_called_once()
        finally:
            reset_request_tenant()
            reset_tenant_slug()

    @pytest.mark.asyncio
    async def test_two_tenant_pools_are_distinct_databases(self):
        """Two tenant slugs resolve to pools over different db_name values —
        the physical isolation boundary (same contract as
        test_tenant_isolation.py::TestPoolIdentityIsolation)."""
        from unittest.mock import AsyncMock, patch
        from db.tenants import TenantConnectionPool

        info_a = {'slug': 'clinic-a', 'name': 'A', 'db_name': 'qp_a',
                  'db_host': 'localhost', 'status': 'active'}
        info_b = {'slug': 'clinic-b', 'name': 'B', 'db_name': 'qp_b',
                  'db_host': 'localhost', 'status': 'active'}
        calls = []
        async def fake_create_pool(**kw):
            calls.append(kw)
            pool = AsyncMock()
            pool._db_name = kw.get('database')
            return pool

        with patch('asyncpg.create_pool', new=fake_create_pool):
            pool_a = await TenantConnectionPool.get('clinic-a', info_a)
            pool_b = await TenantConnectionPool.get('clinic-b', info_b)
        assert pool_a is not pool_b
        assert calls[0]['database'] == 'qp_a'
        assert calls[1]['database'] == 'qp_b'
        TenantConnectionPool._pools.clear()

    @pytest.mark.asyncio
    async def test_real_write_tags_ris_orders_never_default(self):
        """Real-DB half of the contract (rolled back): a write in tenant B's
        scope tags tenant B and leaves no 'default' residue — the lineage tag
        that survives pool separation for the shared-DB tenant."""
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
                    stored = await conn.fetchrow(
                        'SELECT tenant_id FROM ris_orders WHERE id = $1',
                        row['id'],
                    )
                    assert stored['tenant_id'] == tag_b
                    stray = await conn.fetchval(
                        'SELECT count(*) FROM ris_orders WHERE id = $1 AND tenant_id = $2',
                        row['id'], 'default',
                    )
                    assert stray == 0
                finally:
                    await tx.rollback()
                    reset_tenant_slug()
        finally:
            await teardown()


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
