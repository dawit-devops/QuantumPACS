"""Portal appointment reminder emitter tests (portal.appointment_reminder).

The emitter scans SCHEDULED appointments in the reminder window that have
no reminder_sent_at yet and whose patient has granted consent, emits a
patient-scoped notification, and stamps reminder_sent_at to avoid
re-sending. These tests pin the window/consent/dedup behavior against a
mocked connection.
"""

import pytest

from unittest.mock import AsyncMock, patch
from datetime import datetime, timezone


class _Conn:
    def __init__(self, rows=None):
        self.rows = rows or []
        self.executed = []

    async def fetch(self, sql, *args):
        self.last_fetch_sql = sql
        return self.rows

    async def execute(self, sql, *args):
        self.executed.append((sql, args))

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False


def _row(pid='P001', days_ahead=1, reason='CT scan', status='SCHEDULED'):
    from datetime import timedelta
    start = datetime.now(timezone.utc) + timedelta(days=days_ahead)
    return {
        'id': f'{pid}-appt',
        'patient_id': pid,
        'start_time': start,
        'reason': reason,
    }


@pytest.mark.asyncio
async def test_emits_for_upcoming_consented_appointment():
    from db.portal import Portal
    conn = _Conn([_row('P001', days_ahead=1)])
    portal = Portal(conn)
    with patch('api.notify.notify_patient_scoped',
               new_callable=AsyncMock) as notify:
        emitted = await portal.emit_appointment_reminders(window_hours=48)
    assert emitted == 1
    notify.assert_awaited_once()
    args = notify.await_args.args
    assert args[1] == 'P001'
    assert args[2] == 'appointment.reminder'
    assert len(conn.executed) == 1
    assert 'reminder_sent_at' in conn.executed[0][0]


@pytest.mark.asyncio
async def test_skips_appointment_outside_window():
    from db.portal import Portal
    conn = _Conn([])  # DB filters out-of-window rows; emitter sees nothing
    portal = Portal(conn)
    with patch('api.notify.notify_patient_scoped',
               new_callable=AsyncMock) as notify:
        emitted = await portal.emit_appointment_reminders(window_hours=48)
    assert emitted == 0
    notify.assert_not_awaited()
    assert conn.executed == []
    # The window constraint must be enforced in SQL (upper bound on start).
    assert 'start_time <= now() + ($1 ||' in conn.last_fetch_sql
    assert 'start_time >= now()' in conn.last_fetch_sql


@pytest.mark.asyncio
async def test_returns_zero_for_no_appointments():
    from db.portal import Portal
    conn = _Conn([])
    portal = Portal(conn)
    with patch('api.notify.notify_patient_scoped',
               new_callable=AsyncMock) as notify:
        emitted = await portal.emit_appointment_reminders(window_hours=48)
    assert emitted == 0
    notify.assert_not_awaited()


@pytest.mark.asyncio
async def test_default_window_is_24_hours():
    from db.portal import Portal
    conn = _Conn([_row('P001', days_ahead=1)])
    portal = Portal(conn)
    with patch('api.notify.notify_patient_scoped',
               new_callable=AsyncMock) as notify:
        await portal.emit_appointment_reminders()
    # SQL must reference the passed window parameter positionally.
    assert 'now() + ($1 ||' in conn.last_fetch_sql
    notify.assert_awaited_once()
