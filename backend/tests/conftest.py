import warnings
import pytest


@pytest.fixture(autouse=True)
def _suppress_stdlib_coroutine_warnings():
    warnings.filterwarnings(
        "ignore",
        message="coroutine 'handle_find_async' was never awaited",
        category=RuntimeWarning,
    )


@pytest.fixture(autouse=True)
def _reset_otel_tracer():
    from opentelemetry import trace
    existing = trace._TRACER_PROVIDER
    if existing is not None and hasattr(existing, 'shutdown'):
        try:
            existing.shutdown()
        except Exception:
            pass
    trace._TRACER_PROVIDER_SET_ONCE._done = False
    trace._TRACER_PROVIDER = None
    yield
