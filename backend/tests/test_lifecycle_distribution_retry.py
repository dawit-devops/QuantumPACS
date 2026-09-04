"""A2 (GAP_AUDIT_TDD_PIPELINE.md): the ORU retry manager must actually run
in production. retry_failed_deliveries() existed but nothing scheduled it —
FAILED rows accumulated forever. Mirrors
tests/test_lifecycle_escalation_loop.py: the worker runs on the uvicorn main
loop (owner of the asyncpg pool) via run_coroutine_threadsafe, and setup()
must start it."""

import asyncio
from unittest.mock import patch

from lifecycle import _start_distribution_retry, _run_distribution_retry


class TestDistributionRetryLoop:

    def test_start_passes_main_loop_not_new_loop(self):
        captured = {}

        class _NoopThread:
            def __init__(self, *a, **k):
                captured['kwargs'] = k

            def start(self):
                pass

        async def _run():
            with patch('lifecycle._run_distribution_retry'), \
                 patch('threading.Thread', _NoopThread):
                _start_distribution_retry()
                return captured['kwargs']['args'][0]

        loop = asyncio.new_event_loop()
        try:
            passed_loop = loop.run_until_complete(_run())
            assert passed_loop is loop, \
                'must pass the running loop, not a new_event_loop'
        finally:
            loop.close()

    def test_run_retry_schedules_on_passed_loop(self):
        loop = asyncio.new_event_loop()
        scheduled = []

        async def fake_retry():
            return 0

        async def _run():
            import services.results_distribution.service as dist_mod
            with patch.object(dist_mod, 'ResultsDistributionEngine') as FakeEngine:
                FakeEngine.return_value.retry_failed_deliveries = fake_retry

                def _capture_schedule(coro, target_loop):
                    scheduled.append((coro, target_loop))
                    fut = asyncio.get_event_loop().create_future()
                    fut.set_result(None)
                    return fut

                with patch('asyncio.run_coroutine_threadsafe',
                           _capture_schedule):
                    _run_distribution_retry(loop)

        try:
            loop.run_until_complete(_run())
        finally:
            loop.close()

        assert scheduled, 'must schedule via run_coroutine_threadsafe'
        assert scheduled[0][1] is loop, \
            'coroutine must be scheduled on the passed main loop'

    def test_setup_starts_the_worker(self):
        """setup() must register the retry worker alongside the other
        background engines — otherwise the scheduler regression repeats."""
        import inspect
        import lifecycle
        source = inspect.getsource(lifecycle.setup)
        assert '_start_distribution_retry()' in source
