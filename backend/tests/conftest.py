from unittest.mock import AsyncMock, MagicMock, patch

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
    from starlette.routing import Route

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
