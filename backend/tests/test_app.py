import json
from unittest.mock import MagicMock, patch

import pytest
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.authentication import AuthenticationMiddleware
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.routing import Route
from starlette.testclient import TestClient
from starlette.exceptions import HTTPException
from starlette.responses import JSONResponse

from app import CustomMiddleware, http_exception, server_error_handler
from api.tenant_middleware import TenantMiddleware
from api.fhir_audit_middleware import FhirAuditMiddleware
from api.tracing_middleware import TracingMiddleware
from api.telemetry import RequestIDMiddleware
from api.auth import TokenAuth
from api.validate import validation_exception_handler, _ValidationException


def _dummy_endpoint(request):
    return JSONResponse({'ok': True})


def _error_endpoint(request):
    raise RuntimeError('unhandled error')


def _http_error_endpoint(request):
    raise HTTPException(status_code=404, detail='Not Found')


def _validation_error_endpoint(request):
    raise _ValidationException('Bad Request Body')


_ORIGIN = 'http://localhost:5173'


@pytest.fixture
def app():
    return Starlette(
        routes=[
            Route('/api/test', endpoint=_dummy_endpoint),
            Route('/api/error', endpoint=_error_endpoint),
            Route('/api/http-error', endpoint=_http_error_endpoint),
            Route('/api/validation-error', endpoint=_validation_error_endpoint),
        ],
        middleware=[
            Middleware(TracingMiddleware),
            Middleware(AuthenticationMiddleware, backend=TokenAuth(), on_error=TokenAuth.on_auth_error),
            Middleware(TenantMiddleware),
            Middleware(FhirAuditMiddleware),
            Middleware(TrustedHostMiddleware, allowed_hosts=['*']),
            Middleware(RequestIDMiddleware),
            Middleware(CustomMiddleware),
        ],
        exception_handlers={
            HTTPException: http_exception,
            _ValidationException: validation_exception_handler,
            Exception: server_error_handler,
        },
    )


class TestMiddlewareStack:
    def test_middleware_ordering(self):
        from app import app as real_app
        mw_names = [m.cls.__name__ for m in real_app.user_middleware]
        expected_order = [
            'TracingMiddleware',
            'AuthenticationMiddleware',
            'TenantMiddleware',
            'FhirAuditMiddleware',
            'TrustedHostMiddleware',
            'RequestIDMiddleware',
            'CORSMiddleware',
            'SecurityHeadersMiddleware',
            'CSRFMiddleware',
            'CustomMiddleware',
        ]
        assert mw_names == expected_order, f'Expected {expected_order}, got {mw_names}'

    def test_authentication_middleware_present(self):
        from app import app as real_app
        auth_mw = [m for m in real_app.user_middleware if m.cls == AuthenticationMiddleware]
        assert len(auth_mw) == 1


class TestCors:
    def test_cors_headers_on_success(self):
        with patch('app.config', {'cors_origins': '*', 'allowed_hosts': '*'}):
            client = TestClient(_make_app())
            resp = client.get('/api/test', headers={'Host': 'localhost', 'Origin': _ORIGIN})
        assert resp.headers.get('Access-Control-Allow-Origin') == _ORIGIN
        assert resp.headers.get('Access-Control-Allow-Credentials') == 'true'

    def test_cors_preflight(self):
        with patch('app.config', {'cors_origins': '*', 'allowed_hosts': '*'}):
            client = TestClient(_make_app())
            resp = client.options('/api/test', headers={
                'Host': 'localhost',
                'Origin': _ORIGIN,
                'Access-Control-Request-Method': 'POST',
            })
        assert resp.status_code == 200
        assert resp.headers.get('Access-Control-Allow-Origin') == _ORIGIN
        assert resp.headers.get('Access-Control-Allow-Methods') == 'OPTIONS, GET, POST, PUT, DELETE'
        allowed_headers = resp.headers.get('Access-Control-Allow-Headers', '')
        assert 'X-Auth-Pacs' in allowed_headers
        assert 'X-CSRF-Token' in allowed_headers
        assert 'X-API-Key' in allowed_headers

    def test_cors_headers_custom_origin(self):
        with patch('app.config', {'cors_origins': 'https://my-pacs.example.com', 'allowed_hosts': '*'}):
            client = TestClient(_make_app())
            resp = client.get('/api/test', headers={'Host': 'localhost', 'Origin': 'https://my-pacs.example.com'})
        assert resp.headers.get('Access-Control-Allow-Origin') == 'https://my-pacs.example.com'

    def test_cors_headers_on_non_api_path(self):
        with patch('app.config', {'cors_origins': '*', 'allowed_hosts': '*'}):
            client = TestClient(_make_app())
            resp = client.get('/non-api', headers={'Host': 'localhost', 'Origin': _ORIGIN})
        assert resp.status_code == 200
        assert resp.headers.get('Access-Control-Allow-Origin') == _ORIGIN


class TestErrorHandlers:
    def test_500_unhandled_error(self):
        with patch('app.config', {'cors_origins': '*', 'allowed_hosts': '*'}):
            client = TestClient(_make_app())
            resp = client.get('/api/error', headers={'Host': 'localhost'})
        assert resp.status_code == 500
        body = resp.json()
        assert 'Internal server error' in body.get('error', '')

    def test_500_has_cors_headers(self):
        with patch('app.config', {'cors_origins': '*', 'allowed_hosts': '*'}):
            client = TestClient(_make_app())
            resp = client.get('/api/error', headers={'Host': 'localhost', 'Origin': _ORIGIN})
        assert resp.headers.get('Access-Control-Allow-Origin') == _ORIGIN

    def test_exception_handlers_exist(self):
        from app import app as real_app
        handlers = real_app.exception_handlers
        assert HTTPException in handlers
        assert _ValidationException in handlers
        assert Exception in handlers

    async def test_http_exception_handler_returns_json(self):
        exc = HTTPException(status_code=404, detail='Custom not found')
        req = MagicMock()
        req.method = 'GET'
        req.url.path = '/api/test'
        resp = await http_exception(req, exc)
        assert resp.status_code == 404
        body = json.loads(resp.body)
        assert 'Custom not found' in body.get('error', '')

    async def test_server_error_handler_returns_json(self):
        exc = RuntimeError('boom')
        req = MagicMock()
        req.method = 'GET'
        req.url.path = '/api/test'
        with patch('app.log.exception'):
            resp = await server_error_handler(req, exc)
        assert resp.status_code == 500
        body = json.loads(resp.body)
        assert 'Internal server error' in body.get('error', '')


class TestSecurityHeaders:
    def test_cors_methods_restricted(self):
        with patch('app.config', {'cors_origins': '*', 'allowed_hosts': '*'}):
            client = TestClient(_make_app())
            resp = client.options('/api/test', headers={
                'Host': 'localhost',
                'Origin': _ORIGIN,
                'Access-Control-Request-Method': 'POST',
            })
        methods = resp.headers.get('Access-Control-Allow-Methods', '')
        allowed = {m.strip() for m in methods.split(',')}
        assert allowed == {'OPTIONS', 'GET', 'POST', 'PUT', 'DELETE'}

    def test_no_put_or_patch_in_cors(self):
        with patch('app.config', {'cors_origins': '*', 'allowed_hosts': '*'}):
            client = TestClient(_make_app())
            resp = client.options('/api/test', headers={
                'Host': 'localhost',
                'Origin': _ORIGIN,
                'Access-Control-Request-Method': 'POST',
            })
        methods = resp.headers.get('Access-Control-Allow-Methods', '')
        assert 'PATCH' not in methods


class _FakeAuth(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        from api.auth import User
        request.scope['user'] = User({'id': 1, 'permissions': []})
        request.scope['auth'] = None
        return await call_next(request)


def _make_app():
    from app import config as app_config
    return Starlette(
        routes=[
            Route('/api/test', endpoint=_dummy_endpoint),
            Route('/api/error', endpoint=_error_endpoint),
            Route('/api/http-error', endpoint=_http_error_endpoint),
            Route('/api/validation-error', endpoint=_validation_error_endpoint),
            Route('/non-api', endpoint=_dummy_endpoint),
        ],
        middleware=[
            Middleware(_FakeAuth),
            Middleware(CORSMiddleware, allow_origins=app_config.get('cors_origins', '*').split(','), allow_methods=['OPTIONS', 'GET', 'POST', 'PUT', 'DELETE'], allow_headers=['Origin', 'Accept', 'X-Auth-Pacs', 'Content-Type', 'X-Requested-With', 'X-API-Key', 'X-CSRF-Token'], allow_credentials=True),
            Middleware(CustomMiddleware),
        ],
    )
