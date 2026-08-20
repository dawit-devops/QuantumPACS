"""DB-backed regression test for CR-1: tracking status values must be
allowed by the worklist_entries CHECK constraint.

The API-level tests in test_tracking_api.py mock `conn.execute` and therefore
mask the real defect: `TRACKING_VALID_TRANSITIONS` permits `arrived` and
`completed`, but the table CHECK only allows
('scheduled', 'in_progress', 'performed', 'cancelled'). These tests exercise
the real database via an in-loop ASGI transport (httpx ASGITransport) so the
constraint is hit end-to-end.
"""
import pytest

from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.routing import Route

import httpx

from api.auth import User
from db.conn import get_conn, database
from tests.test_tracking_api import _FakeAuth
from api.worklist import TrackingStatusHandler

PERMS = ['WORKLIST_READ', 'WORKLIST_WRITE']


@pytest.fixture(autouse=True)
async def setup_db():
    await database.setup()
    yield
    await database.close()


async def _client(user=None):
    user = user or User({'id': 1, 'permissions': PERMS})
    app = Starlette(
        routes=[
            Route('/ris/tracking/{id}/status', endpoint=TrackingStatusHandler),
        ],
        middleware=[Middleware(_FakeAuth, user=user)],
    )
    transport = httpx.ASGITransport(app=app)
    return httpx.AsyncClient(transport=transport, base_url='http://test')


class TestTrackingStatusConstraint:
    """S6-15: manual guard transitions must survive the DB CHECK constraint."""

    async def _insert_entry(self, conn, accession, status='scheduled'):
        row = await conn.fetchrow(
            "INSERT INTO worklist_entries"
            " (patient_id, patient_name, accession_number, status)"
            " VALUES ($1, $2, $3, $4) RETURNING id",
            'PAT-TSC-01', 'Test Patient', accession, status,
        )
        return row['id']

    @pytest.mark.asyncio
    async def test_arrived_transition_allowed_by_database(self):
        async with get_conn() as conn:
            entry_id = await self._insert_entry(conn, 'ACC-TSC-ARRIVED')
        try:
            async with await _client() as client:
                resp = await client.put(
                    f'/ris/tracking/{entry_id}/status',
                    json={'status': 'arrived'},
                )
            assert resp.status_code == 200, resp.text
            assert resp.json()['data']['status'] == 'arrived'
        finally:
            async with get_conn() as conn:
                await conn.execute(
                    'DELETE FROM worklist_entries WHERE id = $1', entry_id)

    @pytest.mark.asyncio
    async def test_completed_transition_allowed_by_database(self):
        async with get_conn() as conn:
            entry_id = await self._insert_entry(conn, 'ACC-TSC-COMPLETED',
                                                status='in_progress')
        try:
            async with await _client() as client:
                resp = await client.put(
                    f'/ris/tracking/{entry_id}/status',
                    json={'status': 'completed'},
                )
            assert resp.status_code == 200, resp.text
            assert resp.json()['data']['status'] == 'completed'
        finally:
            async with get_conn() as conn:
                await conn.execute(
                    'DELETE FROM worklist_entries WHERE id = $1', entry_id)

    @pytest.mark.asyncio
    async def test_invalid_transition_still_rejected_by_guard(self):
        async with get_conn() as conn:
            entry_id = await self._insert_entry(conn, 'ACC-TSC-BOGUS')
        try:
            async with await _client() as client:
                resp = await client.put(
                    f'/ris/tracking/{entry_id}/status',
                    json={'status': 'bogus'},
                )
            assert resp.status_code == 409, resp.text
        finally:
            async with get_conn() as conn:
                await conn.execute(
                    'DELETE FROM worklist_entries WHERE id = $1', entry_id)
