"""CR-7 regression tests: critical-flag recipient wiring.

S10-02 finding: the frontend only sent recipient_role/recipient_name, so the
backend `notify_role('radiologist')` fallback fired for any selection and the
`ed_physician` role was never notified. The POST handler already branches on
`recipient_id` (notifications.py:144-158) — these tests pin that contract and
the scoped recipients directory the FlagCriticalModal picker needs (the
clinical roles lack USER_READ/ROLE_READ, so the directory lives here, gated
on the same REPORT_WRITE as the flag POST).
"""
import pytest

from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.routing import Route

import httpx

from api.auth import User
from db.conn import get_conn, database
from tests.test_tracking_api import _FakeAuth
from api.notifications import CriticalResultsHandler, CriticalRecipientsHandler, CriticalResultAckHandler

PERMS = ['REPORT_READ', 'REPORT_WRITE']


@pytest.fixture(autouse=True)
async def setup_db():
    await database.setup()
    yield
    await database.close()


async def _client(user=None):
    user = user or User({'id': 1, 'permissions': PERMS})
    app = Starlette(
        routes=[
            Route('/notifications/critical/recipients', endpoint=CriticalRecipientsHandler),
            Route('/notifications/critical', endpoint=CriticalResultsHandler),
            Route('/notifications/critical/{id}/ack', endpoint=CriticalResultAckHandler),
        ],
        middleware=[Middleware(_FakeAuth, user=user)],
    )
    transport = httpx.ASGITransport(app=app)
    return httpx.AsyncClient(transport=transport, base_url='http://test')


class TestAckGuard:
    """H12: acknowledgement is gated and cannot overwrite escalated state."""

    async def _flag(self, recipient_id='cr7_ed_1', accession='ACC-CR7-ACK'):
        from db.ris_critical_results import RisCriticalResults
        async with get_conn() as conn:
            return await RisCriticalResults(conn).create_flag({
                'accession_number': accession,
                'patient_id': 'PAT-CR7-ACK',
                'patient_name': 'Ack Patient',
                'finding_description': 'Acute CVA',
                'recipient_id': recipient_id,
                'recipient_role': 'ed_physician',
            }, flagged_by='cr7_rad_1')

    @pytest.mark.asyncio
    async def test_non_recipient_without_critical_permission_forbidden(self):
        flag = await self._flag()
        client = await _client(User({'id': 999, 'permissions': ['REPORT_READ']}))
        resp = await client.post(f'/notifications/critical/{flag["id"]}/ack')
        assert resp.status_code == 403, resp.text
        async with get_conn() as conn:
            row = await conn.fetchrow(
                'SELECT status FROM ris_critical_results WHERE id = $1', flag['id'])
            assert row['status'] == 'flagged'

    @pytest.mark.asyncio
    async def test_recipient_can_acknowledge(self):
        flag = await self._flag(recipient_id='5')
        client = await _client(User({'id': 5, 'permissions': ['REPORT_READ']}))
        resp = await client.post(f'/notifications/critical/{flag["id"]}/ack')
        assert resp.status_code == 200, resp.text
        assert resp.json()['data']['status'] == 'acknowledged'

    @pytest.mark.asyncio
    async def test_privileged_user_can_ack_and_audits(self):
        flag = await self._flag()
        client = await _client(User({
            'id': 6, 'permissions': ['REPORT_READ', 'CRITICAL_RESULTS_WRITE'],
        }))
        resp = await client.post(f'/notifications/critical/{flag["id"]}/ack')
        assert resp.status_code == 200, resp.text
        async with get_conn() as conn:
            row = await conn.fetchrow(
                "SELECT log FROM logs WHERE (log::json->>'event') = 'critical.acknowledged' "
                "AND (log::json->'resource'->>'id') = $1 "
                "ORDER BY created DESC LIMIT 1", str(flag['id']))
            assert row is not None, 'ack audit event missing'

    @pytest.mark.asyncio
    async def test_ack_of_escalated_flag_rejected(self):
        from db.ris_critical_results import RisCriticalResults
        flag = await self._flag()
        async with get_conn() as conn:
            await RisCriticalResults(conn).escalate(flag['id'], escalated_to='radiologist')
        client = await _client(User({'id': 7, 'permissions': ['REPORT_READ', 'CRITICAL_RESULTS_WRITE']}))
        resp = await client.post(f'/notifications/critical/{flag["id"]}/ack')
        assert resp.status_code == 404, resp.text


class TestCriticalRecipientWiring:
    """S10-02: recipient_id must route to notify_user; role is the fallback."""

    @pytest.mark.asyncio
    async def test_recipients_directory_lists_users_by_role(self):
        async with get_conn() as conn:
            role = await conn.fetchrow(
                "SELECT id FROM roles WHERE slug = $1", 'radiologist',
            )
            if not role:
                pytest.skip('radiologist role not seeded')
            await conn.execute(
                "INSERT INTO users (username, password, admin, role_id, status)"
                " VALUES ($1, $2, false, $3, 'active')"
                " ON CONFLICT (username) DO NOTHING",
                'cr7_recipient_user', 'x', role['id'],
            )
        async with get_conn() as conn:
            row = await conn.fetchrow(
                "SELECT id FROM users WHERE username = 'cr7_recipient_user'",
            )
            assert row is not None

        async with await _client() as client:
            resp = await client.get(
                '/notifications/critical/recipients', params={'role': 'radiologist'},
            )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        usernames = [u['username'] for u in body['data']]
        assert 'cr7_recipient_user' in usernames

    @pytest.mark.asyncio
    async def test_create_flag_with_recipient_id_succeeds(self):
        async with get_conn() as conn:
            user = await conn.fetchrow(
                "SELECT id, role_id FROM users WHERE username = 'cr7_recipient_user'",
            )
        assert user is not None

        async with await _client() as client:
            resp = await client.post('/notifications/critical', json={
                'accession_number': 'ACC-CR7-01',
                'patient_id': 'PAT-CR7-01',
                'patient_name': 'CR7 Patient',
                'finding_description': 'Acute Aortic Dissection',
                'recipient_role': 'ed_physician',
                'recipient_id': str(user['id']),
            })
        assert resp.status_code == 200, resp.text
        flag = resp.json()['data']
        assert flag['status'] == 'flagged'
        # The stored recipient must carry the chosen user (not the role fallback).
        assert str(flag.get('recipient_id')) == str(user['id'])

    @pytest.mark.asyncio
    async def test_create_flag_without_recipient_id_keeps_role_fallback(self):
        async with await _client() as client:
            resp = await client.post('/notifications/critical', json={
                'accession_number': 'ACC-CR7-02',
                'patient_id': 'PAT-CR7-02',
                'patient_name': 'CR7 Patient B',
                'finding_description': 'Acute Pulmonary Embolism',
                'recipient_role': 'ed_physician',
            })
        assert resp.status_code == 200, resp.text
        flag = resp.json()['data']
        assert flag['status'] == 'flagged'
        assert flag['recipient_role'] == 'ed_physician'