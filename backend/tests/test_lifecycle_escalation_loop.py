"""S12-01: Escalation engine must run on the main loop (owning the asyncpg
pool / redis clients), not a throwaway new_event_loop in a daemon thread.
Running it on a fresh loop raises RuntimeError 'Future attached to a different
loop' on every pass (seen in prod logs)."""

import asyncio
from unittest.mock import patch

from lifecycle import _start_critical_escalation, _run_critical_escalation


class TestCriticalEscalationLoop:
    """The escalation engine's `_loop()` coroutine uses get_conn() which
    binds to the uvicorn main loop.  Scheduling it on a second loop (via
    loop.create_task + loop.run_forever) raises the 'different loop' error.
    The fix: pass the main loop to _run_critical_escalation and schedule
    via run_coroutine_threadsafe (mirroring _run_dicom)."""

    def test_start_passes_main_loop_not_new_loop(self):
        """_start_critical_escalation must capture the running loop and
        pass it to the thread, not create a new one."""
        captured = {}

        class _NoopThread:
            def __init__(self, *a, **k):
                captured['kwargs'] = k
            def start(self):
                pass

        async def _run():
            with patch('lifecycle._run_critical_escalation'), \
                 patch('threading.Thread', _NoopThread):
                _start_critical_escalation()
                return captured['kwargs']['args'][0]

        loop = asyncio.new_event_loop()
        try:
            passed_loop = loop.run_until_complete(_run())
            assert passed_loop is loop, \
                'must pass the running loop, not a new_event_loop'
        finally:
            loop.close()

    def test_run_escalation_schedules_on_passed_loop(self):
        """_run_critical_escalation(loop) must schedule the periodic
        coroutine on the passed main loop via run_coroutine_threadsafe,
        not fall into create_task + run_forever on a fresh loop."""
        loop = asyncio.new_event_loop()
        scheduled = []

        async def fake_check():
            return

        async def _run():
            import services.notification.escalation as escalation_mod
            with patch.object(escalation_mod, 'CriticalEscalationEngine') as FakeEngine:
                FakeEngine.return_value.run_escalation_check = fake_check

                def _capture_schedule(coro, target_loop):
                    scheduled.append((coro, target_loop))
                    fut = asyncio.get_event_loop().create_future()
                    fut.set_result(None)
                    return fut

                with patch('asyncio.run_coroutine_threadsafe', _capture_schedule):
                    _run_critical_escalation(loop)

        try:
            loop.run_until_complete(_run())
        finally:
            loop.close()

        assert scheduled, 'must schedule via run_coroutine_threadsafe, not ' \
            'block forever in run_forever'
        assert scheduled[0][1] is loop, \
            'coroutine must be scheduled on the passed main loop'