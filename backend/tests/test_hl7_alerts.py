"""S3-17 — HL7 interface failure alerting tests.

services/hl7_engine/alerts.py: fan-out to HL7_READ roles (super_admin,
tenant_admin), per-user pref resolution, 5-minute throttle, PHI-free
bodies. The engine hooks (service.py) are covered in test_hl7_engine.py.
"""

from unittest.mock import AsyncMock, patch

import pytest

from services.hl7_engine.alerts import (
    ALERT_EVENT_TYPE,
    ALERT_LINK,
    _recent_alert_exists,
    notify_interface_failure,
)

SUPER_ROLE = {'id': 1}
TENANT_ROLE = {'id': 2}


@pytest.fixture
def endpoints_patch():
    with patch('services.hl7_engine.alerts.RisInterfaceEndpoints') as cls:
        cls.return_value.get = AsyncMock(return_value={'name': 'SENDING_FACILITY'})
        yield cls


def _conn():
    conn = AsyncMock()
    conn.fetchrow.side_effect = [SUPER_ROLE, TENANT_ROLE]
    conn.fetch.side_effect = [
        [{'id': 10}, {'id': 11}],  # super_admin users
        [{'id': 20}],              # tenant_admin users
    ]
    return conn


class TestNotifyInterfaceFailure:
    @pytest.mark.asyncio
    async def test_fans_out_to_alert_roles_with_phi_free_body(self, endpoints_patch):
        conn = _conn()
        # per user: is_enabled (None -> role default True), throttle (False)
        conn.fetchval.side_effect = [None, False, None, False, None, False]

        await notify_interface_failure(
            conn,
            endpoint_id='11111111-1111-1111-1111-111111111111',
            parsed={'message_type': 'ORM', 'message_control_id': 'SMK001'},
            error='boom',
        )

        created = [c.args for c in conn.execute.call_args_list if c.args[3] == 'interface.failure']
        assert len(created) == 3
        for sql, nid, user_id, event_type, title, body, link in created:
            assert event_type == ALERT_EVENT_TYPE
            assert title == 'HL7 interface failure'
            assert link == ALERT_LINK
            assert 'SMK001' in body and 'boom' in body
            # PHI-free: no patient demographics in bodies
            assert 'Smith' not in body and 'PID' not in body

    @pytest.mark.asyncio
    async def test_pref_disabled_user_is_skipped(self, endpoints_patch):
        conn = _conn()
        # user 10 explicitly disabled; 11 and 20 enabled with no recent alert
        conn.fetchval.side_effect = [False, None, False, None, False]

        await notify_interface_failure(conn, parsed={'message_type': 'ORM'}, error='x')

        notified = [c.args[2] for c in conn.execute.call_args_list if c.args[3] == 'interface.failure']
        assert 10 not in notified
        assert 11 in notified and 20 in notified
        assert len(notified) == 2

    @pytest.mark.asyncio
    async def test_throttles_repeat_alerts_per_user(self, endpoints_patch):
        conn = _conn()
        # user 10 has an unread alert inside the window
        conn.fetchval.side_effect = [None, True, None, False, None, False]

        await notify_interface_failure(conn, parsed={'message_type': 'ADT'}, error='x')

        notified = [c.args[2] for c in conn.execute.call_args_list if c.args[3] == 'interface.failure']
        assert 10 not in notified
        assert len(notified) == 2

    @pytest.mark.asyncio
    async def test_unknown_endpoint_yields_generic_body(self, endpoints_patch):
        conn = _conn()
        endpoints_patch.return_value.get.return_value = None
        conn.fetchval.side_effect = [None, False, None, False, None, False]

        await notify_interface_failure(conn, endpoint_id='missing', parsed=None, error='Unparseable message')

        created = [c.args for c in conn.execute.call_args_list if c.args[3] == 'interface.failure']
        assert len(created) == 3
        for sql_, nid_, uid_, ev_, title_, body, link_ in created:
            assert body.startswith('HL7 message failed')
            assert 'Unparseable message' in body

    @pytest.mark.asyncio
    async def test_recent_alert_exists_queries_window(self):
        conn = AsyncMock()
        conn.fetchval.return_value = False

        await _recent_alert_exists(conn, 42)

        sql, user_id, event_type, minutes = conn.fetchval.call_args.args
        assert 'make_interval(mins => $3)' in sql
        assert event_type == ALERT_EVENT_TYPE
        assert minutes == 5


if __name__ == '__main__':
    pytest.main([__file__, '-v'])