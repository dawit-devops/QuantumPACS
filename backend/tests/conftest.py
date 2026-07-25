import warnings
import pytest

@pytest.fixture(autouse=True)
def _suppress_stdlib_coroutine_warnings():
    warnings.filterwarnings(
        "ignore",
        message="coroutine 'handle_find_async' was never awaited",
        category=RuntimeWarning,
    )
