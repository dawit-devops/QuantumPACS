"""R2-02-06 / R2-02-14 — unbilled aging escalation + instrumentation.

$0 > 5 days is the SLA signal (gauge); charges stuck past 10 days page
the biller (throttled to one alert per window per role so a stale backlog
cannot flood the bell).
"""

import pytest

from unittest.mock import AsyncMock, patch


class TestAgingInstrumentation:
    @pytest.mark.asyncio
    async def test_unbilled_handler_sets_age_gauges(self):
        from api.billing import RisUnbilledHandler  # noqa: F401  (wired)
        from db.ris_charges import RisCharges

        conn = AsyncMock()
        conn.__aenter__ = AsyncMock(return_value=conn)
        conn.__aexit__ = AsyncMock(return_value=False)
        groups = [
            {'age_bucket': '0-5 days', 'n': 4},
            {'age_bucket': '5-10 days', 'n': 2},
            {'age_bucket': '>10 days', 'n': 3},
        ]
        observed = {}

        async def fake_aging(tenant_id='default', min_age_days=5):
            return groups, sum(g['n'] for g in groups)

        with patch.object(RisCharges, 'aging_groups', fake_aging), \
             patch('api.billing.get_conn', return_value=conn), \
             patch('api.billing.ris_unbilled_over_5d') as g5, \
             patch('api.billing.ris_unbilled_over_10d') as g10:
            from tests.helpers_billing_api import call_unbilled
            await call_unbilled()

        assert g5.set.called
        assert g10.set.called
        observed['over5'] = g5.set.call_args[0][0]
        observed['over10'] = g10.set.call_args[0][0]
        # 5-10 bucket plus >10 are both past the 5-day SLA.
        assert observed['over5'] == 5
        assert observed['over10'] == 3


class TestAgingEscalation:
    @pytest.mark.asyncio
    async def test_alerts_biller_and_manager_when_over_10d(self):
        from services.billing_alerts import escalate_aging

        notified = []

        async def fake_notify(role_slug, event_type, title, body, link=''):
            notified.append((role_slug, event_type))
            return None

        conn = AsyncMock()
        with patch('services.billing_alerts._notify_role_throttled',
                   new=fake_notify):
            await escalate_aging(conn, 'default', over10=3)

        roles = {r for r, _ in notified}
        assert {'biller', 'practice_manager'} <= roles
        assert all(et == 'billing.unbilled_escalation' for _, et in notified)

    @pytest.mark.asyncio
    async def test_no_backlog_no_alert(self):
        from services.billing_alerts import escalate_aging

        notified = []

        async def fake_notify(*a, **kw):
            notified.append(a)

        with patch('services.billing_alerts._notify_role_throttled',
                   new=fake_notify):
            await escalate_aging(AsyncMock(), 'default', over10=0)
        assert not notified

    @pytest.mark.asyncio
    async def test_throttle_window_is_daily(self):
        import services.billing_alerts as ba
        assert ba.ALERT_WINDOW_HOURS == 24

    @pytest.mark.asyncio
    async def test_handler_fires_escalation_best_effort(self):
        """A failing escalation must never break the aging query."""
        from db.ris_charges import RisCharges

        conn = AsyncMock()
        conn.__aenter__ = AsyncMock(return_value=conn)
        conn.__aexit__ = AsyncMock(return_value=False)

        async def fake_aging(tenant_id='default', min_age_days=5):
            return [{'age_bucket': '>10 days', 'n': 9}], 9

        async def boom(*a, **kw):
            raise RuntimeError('notify down')

        from api.billing import RisUnbilledHandler as _H
        handler = object.__new__(_H)
        scope = type('S', (), {
            'path_params': {}, 'query_params': {},
            'user': type('U', (), {'id': 1, 'tenant': 'default',
                          'is_authenticated': True, 'admin': True,
                          'permissions': ['*']})(),
        })()
        sent = {}

        class _Resp:
            def __init__(self, body):
                sent['body'] = body

        with patch.object(RisCharges, 'aging_groups', fake_aging), \
             patch('api.billing.get_conn', return_value=conn), \
             patch('api.billing.ris_unbilled_over_5d'), \
             patch('api.billing.ris_unbilled_over_10d'), \
             patch('services.billing_alerts.escalate_aging', new=boom):
            resp = await _H.get(handler, scope)
        assert resp is not None
