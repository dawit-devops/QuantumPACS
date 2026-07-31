from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from starlette.testclient import TestClient

from api.auth import User
from api.tokens import create_token


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
