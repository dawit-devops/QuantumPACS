from unittest.mock import AsyncMock, MagicMock, patch

from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from starlette.routing import Route
from starlette.testclient import TestClient

from api.auth import User
from api.fhir_audit_middleware import FhirAuditMiddleware


class _FakeAuth(BaseHTTPMiddleware):
    def __init__(self, app, user=None):
        super().__init__(app)
        self._user = user or User({'id': 1, 'permissions': ['PATIENT_READ']})

    async def dispatch(self, request, call_next):
        request.scope['user'] = self._user
        request.scope['auth'] = None
        return await call_next(request)


async def _ok(request):
    return JSONResponse({'status': 'ok'})


async def _not_found(request):
    return JSONResponse({'status': 'not found'}, status_code=404)


async def _patient_read(request):
    return JSONResponse({'resourceType': 'Patient', 'id': request.path_params.get('id', '')})


def _make_app():
    return Starlette(
        routes=[
            Route('/health', endpoint=_ok),
            Route('/fhir/Patient/{id}', endpoint=_patient_read),
            Route('/fhir/metadata', endpoint=_ok),
            Route('/api/hl7', endpoint=_ok),
        ],
        middleware=[
            Middleware(_FakeAuth),
            Middleware(FhirAuditMiddleware),
        ],
    )


class TestFhirAuditMiddleware:
    def test_skips_non_fhir_routes(self):
        mock_conn = MagicMock()
        mock_conn.execute = AsyncMock()

        with patch('api.fhir_audit_middleware.get_conn') as mock_get:
            mock_get.return_value.__aenter__.return_value = mock_conn
            mock_get.return_value.__aexit__ = AsyncMock(return_value=None)

            client = TestClient(_make_app())
            resp = client.get('/health')

        assert resp.status_code == 200
        mock_conn.execute.assert_not_called()

    def test_records_fhir_request(self):
        mock_conn = MagicMock()
        mock_conn.execute = AsyncMock()

        with patch('api.fhir_audit_middleware.get_conn') as mock_get:
            mock_get.return_value.__aenter__.return_value = mock_conn
            mock_get.return_value.__aexit__ = AsyncMock(return_value=None)

            client = TestClient(_make_app())
            resp = client.get('/fhir/Patient/PID001')

        assert resp.status_code == 200
        body = resp.json()
        assert body['resourceType'] == 'Patient'
        mock_conn.execute.assert_called_once()

    def test_records_fhir_not_found(self):
        mock_conn = MagicMock()
        mock_conn.execute = AsyncMock()

        with patch('api.fhir_audit_middleware.get_conn') as mock_get:
            mock_get.return_value.__aenter__.return_value = mock_conn
            mock_get.return_value.__aexit__ = AsyncMock(return_value=None)

            client = TestClient(_make_app())
            resp = client.get('/fhir/metadata')

        assert resp.status_code == 200
        mock_conn.execute.assert_called_once()

    def test_skips_non_fhir_paths_like_api(self):
        mock_conn = MagicMock()
        mock_conn.execute = AsyncMock()

        with patch('api.fhir_audit_middleware.get_conn') as mock_get:
            mock_get.return_value.__aenter__.return_value = mock_conn
            mock_get.return_value.__aexit__ = AsyncMock(return_value=None)

            client = TestClient(_make_app())
            resp = client.get('/api/hl7')

        assert resp.status_code == 200
        mock_conn.execute.assert_not_called()

    def test_db_failure_does_not_break_response(self):
        mock_conn = MagicMock()
        mock_conn.execute = AsyncMock(side_effect=Exception('DB down'))

        with patch('api.fhir_audit_middleware.get_conn') as mock_get:
            mock_get.return_value.__aenter__.return_value = mock_conn
            mock_get.return_value.__aexit__ = AsyncMock(return_value=None)

            client = TestClient(_make_app())
            resp = client.get('/fhir/Patient/PID001')

        assert resp.status_code == 200


class TestFhirAuditModel:
    async def test_log_request_inserts(self):
        mock_conn = MagicMock()
        mock_conn.execute = AsyncMock()
        mock_conn.fetchval = AsyncMock(return_value='some-uuid')

        from db.fhir_audit import FhirAudit
        audit = FhirAudit(mock_conn)
        await audit.log_request({
            'user_id': 1,
            'method': 'GET',
            'path': '/fhir/Patient/PID001',
            'query_params': '',
            'resource_type': 'Patient',
            'resource_id': 'PID001',
            'status_code': 200,
            'duration_ms': 42,
            'ip_address': '127.0.0.1',
        })

        mock_conn.execute.assert_called_once()
        call_sql = str(mock_conn.execute.call_args[0][0])
        assert 'fhir_audit' in call_sql
        assert 'INSERT' in call_sql

    async def test_log_request_minimal(self):
        mock_conn = MagicMock()
        mock_conn.execute = AsyncMock()
        mock_conn.fetchval = AsyncMock(return_value='some-uuid')

        from db.fhir_audit import FhirAudit
        audit = FhirAudit(mock_conn)
        await audit.log_request({
            'method': 'GET',
            'path': '/fhir/Patient',
        })

        mock_conn.execute.assert_called_once()
