"""S4-06 — ris_resources + ris_resource_schedules persistence (B1).

Real-DB repository tests in the style of test_ris_tenant_isolation.py:
rows are created through the public repository interface, written inside a
transaction that is rolled back, so the dev database is never mutated.
"""

import asyncio
import uuid

import pytest

from db.conn import get_conn, reset_tenant_slug, set_tenant_slug, setup, teardown


async def _ensure_schema(conn, repos):
    """DDL inside the rollback tx: schema ships with the test, not the DB."""
    for repo in repos:
        await repo(conn).sync_db()


class TestRisResourcesRepo:
    def test_create_resource_persists_with_tenant_tag(self):
        from db.ris_resources import RisResources

        async def run():
            try:
                await setup()
            except Exception:
                pytest.skip('dev database unavailable')

            tag = f'res-{uuid.uuid4().hex[:6]}'
            try:
                async with get_conn() as conn:
                    tx = conn.transaction()
                    await tx.start()
                    try:
                        set_tenant_slug(tag)
                        await _ensure_schema(conn, [RisResources])
                        row = await RisResources(conn).create({
                            'name': f'CT Room {tag}',
                            'resource_type': 'ROOM',
                            'modality': 'CT',
                            'location': 'Wing B',
                        })
                        assert row['id'] is not None
                        assert row['tenant_id'] == tag
                        assert row['resource_type'] == 'ROOM'
                        assert row['status'] == 'ACTIVE'
                    finally:
                        await tx.rollback()
                        reset_tenant_slug()
            finally:
                await teardown()

        asyncio.run(run())

    def test_duplicate_resource_name_rejected(self):
        from asyncpg.exceptions import UniqueViolationError
        from db.ris_resources import RisResources

        async def run():
            try:
                await setup()
            except Exception:
                pytest.skip('dev database unavailable')

            tag = f'res-{uuid.uuid4().hex[:6]}'
            try:
                async with get_conn() as conn:
                    tx = conn.transaction()
                    await tx.start()
                    try:
                        set_tenant_slug(tag)
                        await _ensure_schema(conn, [RisResources])
                        await RisResources(conn).create({
                            'name': f'US Suite {tag}',
                            'resource_type': 'ROOM',
                        })
                        with pytest.raises(UniqueViolationError):
                            await RisResources(conn).create({
                                'name': f'US Suite {tag}',
                                'resource_type': 'ROOM',
                            })
                    finally:
                        await tx.rollback()
                        reset_tenant_slug()
            finally:
                await teardown()

        asyncio.run(run())

    def test_create_schedule_persists_for_resource(self):
        from db.ris_resources import RisResourceSchedules, RisResources

        async def run():
            try:
                await setup()
            except Exception:
                pytest.skip('dev database unavailable')

            tag = f'res-{uuid.uuid4().hex[:6]}'
            try:
                async with get_conn() as conn:
                    tx = conn.transaction()
                    await tx.start()
                    try:
                        set_tenant_slug(tag)
                        await _ensure_schema(conn, [RisResources, RisResourceSchedules])
                        resource = await RisResources(conn).create({
                            'name': f'MR Room {tag}',
                            'resource_type': 'ROOM',
                            'modality': 'MR',
                        })
                        row = await RisResourceSchedules(conn).create({
                            'resource_id': resource['id'],
                            'day_of_week': 1,
                            'start_time': '08:00:00',
                            'end_time': '17:00:00',
                        })
                        assert row['id'] is not None
                        assert row['resource_id'] == resource['id']
                        assert row['day_of_week'] == 1
                    finally:
                        await tx.rollback()
                        reset_tenant_slug()
            finally:
                await teardown()

        asyncio.run(run())