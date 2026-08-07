from unittest.mock import AsyncMock, patch

import pytest
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware import Middleware
from starlette.routing import Route
from starlette.testclient import TestClient

from api.auth import User
from api.tokens import create_token


def _http_exception(request, exc):
    from starlette.responses import JSONResponse
    return JSONResponse({'error': exc.detail}, status_code=exc.status_code)


class _FakeAuth(BaseHTTPMiddleware):
    def __init__(self, app, user=None):
        super().__init__(app)
        self._user = user or User({'id': 1, 'permissions': []})

    async def dispatch(self, request, call_next):
        request.scope['user'] = self._user
        request.scope['auth'] = None
        return await call_next(request)


def _fake_auth_middleware(user=None):
    return Middleware(_FakeAuth, user=user or User({'id': 1, 'permissions': []}))


def _make_app(routes, user=None):
    from starlette.applications import Starlette
    from starlette.exceptions import HTTPException
    from api.validate import validation_exception_handler, _ValidationException
    return Starlette(
        routes=routes,
        middleware=[_fake_auth_middleware(user)],
        exception_handlers={
            HTTPException: _http_exception,
            _ValidationException: validation_exception_handler,
        },
    )


@pytest.fixture
def mock_conn():
    return AsyncMock()


@pytest.fixture(scope='session', autouse=True)
def _close_background_clients():
    """Close the sentry transport at session end (not loop-bound). The redis
    pool is loop-bound and is closed per-test by _close_redis_pool instead."""
    yield
    try:
        import sentry_sdk

        sentry_sdk.get_client().close()
    except Exception:
        pass


@pytest.fixture(autouse=True)
async def _close_redis_pool():
    """Close the process-wide redis pool on the test's own event loop.

    Connections are bound to the loop that created them; closing them from a
    different loop (or asyncio.run) leaks the sockets and pytest reports them
    as ResourceWarnings when GC runs during later tests."""
    yield
    try:
        from api.redis_client import close_client

        await close_client()
    except Exception:
        pass


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


@pytest.fixture
def auth_headers():
    user = {'id': 1, 'admin': True, 'permissions': ['*']}
    with patch('api.tokens.config', {'secret': 'test-secret-key-32-bytes-long!!!'}):
        token = create_token(user)
    return {'X-Auth-Pacs': token, 'Authorization': f'Bearer {token}'}


@pytest.fixture
def db_conn():
    conn = AsyncMock()
    conn.fetch = AsyncMock(return_value=[])
    conn.fetchval = AsyncMock(return_value=None)
    conn.fetchrow = AsyncMock(return_value=None)
    conn.execute = AsyncMock()
    return conn


@pytest.fixture
def test_client():
    from starlette.applications import Starlette
    from starlette.middleware import Middleware
    from starlette.middleware.authentication import AuthenticationMiddleware

    from api.auth import TokenAuth

    def _ok(request):
        from starlette.responses import JSONResponse
        return JSONResponse({'ok': True})

    app = Starlette(
        routes=[Route('/api/test', endpoint=_ok)],
        middleware=[
            Middleware(AuthenticationMiddleware, backend=TokenAuth(), on_error=TokenAuth.on_auth_error),
        ],
    )

    with TestClient(app) as client:
        yield client
