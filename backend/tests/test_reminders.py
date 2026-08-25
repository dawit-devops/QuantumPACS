"""v1.1 Sprint R2-S2 — Reminders (E-RIS2-02) tests.

R2-01-11..13: channel dispatch (SMS/email/phone) with retry, opt-out
honored, and send/receipt logging feeding the <= 5-min failure alert.
"""

import pytest

from unittest.mock import AsyncMock, patch

from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.routing import Route
from starlette.testclient import TestClient

from api.auth import User
from api.permissions import Permission


class _FakeAuth(BaseHTTPMiddleware):
    def __init__(self, app, user=None):
        super().__init__(app)
        self._user = user or User({'id': 1, 'permissions': []})

    async def dispatch(self, request, call_next):
        request.scope['user'] = self._user
        request.scope['auth'] = None
        return await call_next(request)


def _make_app(user, handlers):
    from starlette.exceptions import HTTPException
    from api.validate import validation_exception_handler, _ValidationException

    def _http_exception(request, exc):
        from starlette.responses import JSONResponse
        return JSONResponse(
            {'error': exc.detail if hasattr(exc, 'detail') else ''},
            status_code=exc.status_code,
        )

    return Starlette(
        routes=[Route(path, endpoint=h, methods=m) for path, h, m in handlers],
        middleware=[Middleware(_FakeAuth, user=user)],
        exception_handlers={
            HTTPException: _http_exception,
            _ValidationException: validation_exception_handler,
        },
    )


def _user(*perms, tenant='default'):
    return User({'id': 1, 'permissions': list(perms), 'tenant': tenant})


class _Conn:
    """In-memory asyncpg-like connection capturing SQL + results."""

    def __init__(self):
        self.calls = []
        self._fetchval = 0
        self._fetch = []
        self._fetchrow = None

    def set_fetchval(self, v):
        self._fetchval = v

    def set_fetch(self, rows):
        self._fetch = rows

    def set_fetchrow(self, row):
        self._fetchrow = row

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def execute(self, sql, *args):
        self.calls.append(('execute', sql, args))

    async def fetchval(self, sql, *args):
        self.calls.append(('fetchval', sql, args))
        return self._fetchval

    async def fetch(self, sql, *args):
        self.calls.append(('fetch', sql, args))
        return self._fetch

    async def fetchrow(self, sql, *args):
        self.calls.append(('fetchrow', sql, args))
        return self._fetchrow


@pytest.fixture
def conn():
    return _Conn()


# ---------------------------------------------------------------------------
# R2-01-11 — message log + channel dispatch
# ---------------------------------------------------------------------------

class TestMessageLogDb:
    """log_sent / log_failed record the delivery for audit + retry."""

    @pytest.mark.asyncio
    async def test_log_sent_writes_row(self, conn):
        from db.ris_message_log import MessageLog

        conn.set_fetchrow({'id': 'msg-1', 'status': 'SENT'})
        row = await MessageLog(conn).log_sent(
            channel='email', recipient='p@example.com',
            event_type='reminder.appointment', subject='Appt',
            body='Your exam is tomorrow', tenant_id='default',
        )
        assert row['status'] == 'SENT'
        inserts = [sql for m, sql, *_ in conn.calls if 'INSERT INTO ris_message_log' in sql]
        assert inserts, 'log_sent must INSERT a ris_message_log row'
        assert "'SENT'" in inserts[0]

    @pytest.mark.asyncio
    async def test_failed_since_filters_window(self, conn):
        from db.ris_message_log import MessageLog

        conn.set_fetch([{'id': 'm1', 'channel': 'sms', 'status': 'FAILED'}])
        rows = await MessageLog(conn).failed_since(5, 'default')
        assert len(rows) == 1
        sql = [sql for m, sql, *_ in conn.calls if 'ris_message_log' in sql][0]
        assert 'make_interval(mins => $2)' in sql or 'mins =>' in sql

    @pytest.mark.asyncio
    async def test_reminder_config_upsert(self, conn):
        from db.ris_message_log import ReminderConfig

        await ReminderConfig(conn).upsert(
            event_type='reminder.appointment', channel='sms',
            template='Appt at {time}', lead_time_hours=24, tenant_id='default',
        )
        calls = [sql for m, sql, *_ in conn.calls]
        assert any('INSERT INTO ris_reminder_config' in sql for sql in calls)
        assert any('ON CONFLICT (tenant_id, event_type)' in sql for sql in calls)


# ---------------------------------------------------------------------------
# R2-01-11/12 — ReminderService dispatch, opt-out, retry
# ---------------------------------------------------------------------------

class TestReminderService:
    """send() dispatches via channel, honors opt-out, logs every attempt."""

    @pytest.mark.asyncio
    async def test_send_email_logs_sent(self, conn):
        from services.reminders.service import ReminderService

        conn.set_fetchrow({'id': 'msg-1', 'status': 'SENT'})
        svc = ReminderService()

        # The mock conn returns the same row for the config lookup and the
        # log insert, so bypass _opt_out_allowed (covered separately).
        with patch('services.reminders.service.get_conn', return_value=conn), \
             patch.object(ReminderService, '_opt_out_allowed',
                          new=AsyncMock(return_value=True)):
            result = await svc.send(
                event_type='reminder.appointment', recipient='p@example.com',
                channel='email', subject='Appt', body='Tomorrow',
                tenant_id='default',
            )
        assert result['status'] == 'SENT'
        inserts = [sql for m, sql, *_ in conn.calls if 'INSERT INTO ris_message_log' in sql]
        assert inserts

    @pytest.mark.asyncio
    async def test_send_honors_opt_out(self, conn):
        from services.reminders.service import ReminderDeliveryError, ReminderService

        # Config row absent or inactive -> opted out, nothing sent.
        conn.set_fetchrow({'id': 'cfg-1', 'event_type': 'reminder.appointment',
                           'active': False})
        svc = ReminderService()

        with patch('services.reminders.service.get_conn', return_value=conn):
            with pytest.raises(ReminderDeliveryError) as exc:
                await svc.send(
                    event_type='reminder.appointment', recipient='p@example.com',
                    channel='email', tenant_id='default',
                )
        assert 'Opted out' in str(exc.value)
        inserts = [sql for m, sql, *_ in conn.calls if 'INSERT INTO ris_message_log' in sql]
        assert not inserts, 'opt-out must not send or log a delivery'

    @pytest.mark.asyncio
    async def test_sms_rejects_bad_phone_without_retry(self, conn):
        from services.reminders.service import ReminderDeliveryError, ReminderService

        conn.set_fetchrow({'id': 'cfg-1', 'active': True})
        svc = ReminderService()

        with patch('services.reminders.service.get_conn', return_value=conn):
            with pytest.raises(ReminderDeliveryError):
                await svc.send(
                    event_type='reminder.appointment', recipient='123',
                    channel='sms', tenant_id='default',
                )
        # Validation failure is permanent: log FAILED once, no retry loop.
        failed = [sql for m, sql, *_ in conn.calls
                  if 'INSERT INTO ris_message_log' in sql and "'FAILED'" in sql]
        assert failed, 'validation failure must log a FAILED delivery'

    @pytest.mark.asyncio
    async def test_failed_since_feeds_alert(self, conn):
        from services.reminders.service import ReminderService

        conn.set_fetch([{'id': 'm1', 'status': 'FAILED', 'attempts': 2}])
        svc = ReminderService()
        with patch('services.reminders.service.get_conn', return_value=conn):
            rows = await svc.failed_since(5, 'default')
        assert len(rows) == 1


# ---------------------------------------------------------------------------
# R2-01-10/11 — Reminders API
# ---------------------------------------------------------------------------

class TestRemindersApi:
    """Send reminder, message log read, config upsert over HTTP."""

    def _handlers(self):
        from api.reminders import (
            ReminderSendHandler,
            ReminderLogHandler,
            ReminderConfigHandler,
        )
        return [
            ('/ris/reminders/send', ReminderSendHandler, ['POST']),
            ('/ris/reminders/log', ReminderLogHandler, ['GET']),
            ('/ris/reminders/config', ReminderConfigHandler, ['GET', 'POST']),
        ]

    def test_send_requires_write(self, conn):
        from api.reminders import ReminderSendHandler
        client = TestClient(_make_app(
            _user(),
            [('/ris/reminders/send', ReminderSendHandler, ['POST'])],
        ))
        with patch('api.reminders.get_conn', return_value=conn):
            resp = client.post('/ris/reminders/send', json={})
        assert resp.status_code == 403

    def test_send_dispatches(self, conn):
        from api.reminders import ReminderSendHandler
        client = TestClient(_make_app(
            _user(Permission.PRIOR_AUTH_WRITE),
            [('/ris/reminders/send', ReminderSendHandler, ['POST'])],
        ))
        with patch('api.reminders.get_conn', return_value=conn), \
             patch('services.reminders.service.ReminderService.send',
                   new=AsyncMock(return_value={'status': 'SENT'})):
            resp = client.post('/ris/reminders/send', json={
                'event_type': 'reminder.appointment',
                'recipient': 'p@example.com', 'channel': 'email',
                'subject': 'Appt', 'body': 'Tomorrow',
            })
        # A send creates a message-log row -> 201 Created.
        assert resp.status_code == 201, resp.text

    def test_log_requires_read(self, conn):
        from api.reminders import ReminderLogHandler
        client = TestClient(_make_app(
            _user(),
            [('/ris/reminders/log', ReminderLogHandler, ['GET'])],
        ))
        with patch('api.reminders.get_conn', return_value=conn):
            resp = client.get('/ris/reminders/log')
        assert resp.status_code == 403

    def test_log_returns_messages(self, conn):
        from api.reminders import ReminderLogHandler
        conn.set_fetch([{'id': 'm1', 'channel': 'sms', 'status': 'SENT'}])
        conn.set_fetchval(1)
        client = TestClient(_make_app(
            _user(Permission.PRIOR_AUTH_READ),
            [('/ris/reminders/log', ReminderLogHandler, ['GET'])],
        ))
        with patch('api.reminders.get_conn', return_value=conn):
            resp = client.get('/ris/reminders/log')
        assert resp.status_code == 200
        assert resp.json()['total'] == 1


# ---------------------------------------------------------------------------
# R2-01-13 — failure monitor alerts
# ---------------------------------------------------------------------------

class TestReminderFailureMonitor:
    """FAILED deliveries in the window alert ops (<= 5-min SLA)."""

    @pytest.mark.asyncio
    async def test_check_notifies_on_failed(self):
        from services.reminders.service import ReminderFailureMonitor

        conn = _Conn()
        conn.set_fetch([{'id': 'm1', 'channel': 'sms', 'recipient': '555',
                         'attempts': 2, 'event_type': 'reminder.appointment'}])
        monitor = ReminderFailureMonitor(window_minutes=5)

        with patch('services.reminders.service.get_conn', return_value=conn), \
             patch('api.notify.notify_role') as mock_nr:
            n = await monitor.check('default')

        assert n == 1
        mock_nr.assert_awaited_once()
        args = mock_nr.call_args
        assert args[0][2] == 'reminder.delivery'


# ---------------------------------------------------------------------------
# R2-02 E2E — config -> send -> log (real DB)
# ---------------------------------------------------------------------------

class TestReminderE2E:
    """Real-DB roundtrip: configure a reminder event, send it, verify the
    delivery lands in ris_message_log as SENT with a provider receipt."""

    def test_config_send_log_roundtrip(self):
        import asyncio as _asyncio
        import uuid as _uuid

        async def run():
            from db.conn import (
                get_conn,
                reset_tenant_slug,
                set_tenant_slug,
                setup,
                teardown,
            )
            from db.ris_message_log import ReminderConfig
            from services.reminders.service import ReminderService

            try:
                await setup()
            except Exception:
                pytest.skip('dev database unavailable')

            tag = f'r2-{_uuid.uuid4().hex[:8]}'
            try:
                set_tenant_slug(tag)
                async with get_conn() as conn:
                    # Configure the appointment reminder event (active).
                    await ReminderConfig(conn).upsert(
                        event_type='reminder.appointment',
                        channel='email', template='Appt at {time}',
                        lead_time_hours=24, active=True, tenant_id=tag,
                    )
                # Send via the service (its own pool connection).
                result = await ReminderService().send(
                    event_type='reminder.appointment',
                    recipient='p@example.com', channel='email',
                    subject='Appt', body='Your exam is tomorrow',
                    tenant_id=tag,
                )
                assert result['status'] == 'SENT'

                async with get_conn() as conn:
                    row = await conn.fetchrow(
                        'SELECT status, channel, provider_receipt'
                        ' FROM ris_message_log WHERE id = $1',
                        result['id'],
                    )
                    assert row is not None
                    assert row['status'] == 'SENT'
                    assert row['channel'] == 'email'
                    assert row['provider_receipt'], 'provider receipt recorded'
            finally:
                reset_tenant_slug()
                await teardown()

        _asyncio.run(run())


class TestPatientOptOut:
    """CS4/CC-12: per-patient reminder opt-out registry + dispatch gate."""

    @pytest.mark.asyncio
    async def test_patient_optout_blocks_send(self, conn):
        from services.reminders.service import ReminderDeliveryError, ReminderService

        # Config active; patient-level opt-out row present.
        conn.set_fetchrow({'id': 'cfg-1', 'active': True})

        class OptConn(_Conn):
            async def fetchval(self, sql, *args):
                self.calls.append(('fetchval', sql, args))
                if 'patient_reminder_optouts' in sql:
                    return 1
                return self._fetchval

        svc = ReminderService()
        oc = OptConn()
        with patch('services.reminders.service.get_conn', return_value=oc):
            with pytest.raises(ReminderDeliveryError) as exc:
                await svc.send(
                    event_type='reminder.appointment',
                    recipient='p@example.com', channel='email',
                    tenant_id='default', patient_id='P1',
                )
        assert 'opted out' in str(exc.value).lower()

    @pytest.mark.asyncio
    async def test_no_optout_sends(self, conn):
        from services.reminders.service import ReminderService

        conn.set_fetchrow({'id': 'cfg-1', 'active': True})
        conn.set_fetch([{'id': 'msg-1'}])
        # fetchval default 0 → falsy → is_opted_out returns False
        svc = ReminderService()

        with patch('services.reminders.service.get_conn', return_value=conn):
            result = await svc.send(
                event_type='reminder.appointment',
                recipient='p@example.com', channel='email',
                tenant_id='default', patient_id='P1',
            )
        assert result['status'] == 'SENT'

    def test_optout_list_requires_read(self, conn):
        from api.reminders import ReminderOptOutHandler
        client = TestClient(_make_app(
            _user(), [('/ris/reminders/optouts', ReminderOptOutHandler,
                      ['GET', 'POST'])],
        ))
        with patch('api.reminders.get_conn', return_value=conn):
            resp = client.get('/ris/reminders/optouts')
        assert resp.status_code == 403

    def test_optout_toggle_requires_write(self, conn):
        from api.reminders import ReminderOptOutHandler
        client = TestClient(_make_app(
            _user(Permission.PRIOR_AUTH_READ),
            [('/ris/reminders/optouts', ReminderOptOutHandler,
              ['GET', 'POST'])],
        ))
        with patch('api.reminders.get_conn', return_value=conn):
            resp = client.post('/ris/reminders/optouts',
                               json={'patient_id': 'P1'})
        assert resp.status_code == 403

    def test_optout_toggle_roundtrip(self, conn):
        from api.reminders import ReminderOptOutHandler
        client = TestClient(_make_app(
            _user(Permission.PRIOR_AUTH_WRITE),
            [('/ris/reminders/optouts', ReminderOptOutHandler,
              ['GET', 'POST'])],
        ))
        with patch('api.reminders.get_conn', return_value=conn):
            on = client.post('/ris/reminders/optouts', json={
                'patient_id': 'P1', 'event_type': None, 'opted_out': True})
            off = client.post('/ris/reminders/optouts', json={
                'patient_id': 'P1', 'opted_out': False})
        assert on.status_code == 200
        assert on.json()['data']['opted_out'] is True
        assert off.status_code == 200
        assert off.json()['data']['opted_out'] is False

    def test_optout_requires_patient_id(self, conn):
        from api.reminders import ReminderOptOutHandler
        client = TestClient(_make_app(
            _user(Permission.PRIOR_AUTH_WRITE),
            [('/ris/reminders/optouts', ReminderOptOutHandler,
              ['GET', 'POST'])],
        ))
        with patch('api.reminders.get_conn', return_value=conn):
            resp = client.post('/ris/reminders/optouts', json={})
        assert resp.status_code == 400
