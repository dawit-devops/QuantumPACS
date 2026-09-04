"""E2 (GAP_AUDIT_TDD_PIPELINE.md): SMART-on-FHIR scope enforcement.

FHIR had no OAuth scope handling — the `requires_permission` decorator gates
by role, not by SMART scope. The middleware must check `smart_scopes` from
the JWT before the handler runs. Without a matching scope, reads also 403
when the token carries explicit scopes (no-scope tokens keep existing
behaviour for backward compatibility).
"""
import pytest
from unittest.mock import AsyncMock, patch

from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.routing import Route
from starlette.testclient import TestClient

from api.auth import User
from api.tokens import create_token


class _FakeAuthWithScope(BaseHTTPMiddleware):
    """Inject a user with a `smart_scopes` attribute into the request scope,
    matching what the SMART middleware would read from the JWT."""

    def __init__(self, app, user=None, scopes=None):
        super().__init__(app)
        self._user = user or User({'id': 1, 'permissions': ['*'], 'admin': True})
        self._scopes = scopes or []

    async def dispatch(self, request, call_next):
        request.scope['user'] = self._user
        request.scope['auth'] = None
        request.scope['smart_scopes'] = self._scopes
        return await call_next(request)


def _make_app(user=None, scopes=None):
    from api.fhir import (
        FhirPatientResource,
        FhirServiceRequestItem,
        FhirDiagnosticReportRead,
        FhirMetadata,
    )

    from api.fhir_scope_middleware import FhirScopeMiddleware

    return Starlette(
        routes=[
            Route('/fhir/metadata', endpoint=FhirMetadata),
            Route('/fhir/Patient/{id}', endpoint=FhirPatientResource),
            Route('/fhir/ServiceRequest/{id}', endpoint=FhirServiceRequestItem),
            Route('/fhir/DiagnosticReport/{id}', endpoint=FhirDiagnosticReportRead),
        ],
        middleware=[
            Middleware(_FakeAuthWithScope, user=user, scopes=scopes),
            Middleware(FhirScopeMiddleware),
        ],
    )


_READ_ONLY_SCOPES = ['patient/Patient.read', 'patient/ServiceRequest.read',
                     'patient/DiagnosticReport.read']

PATIENT_HANDLER_ROWS = {
    'mock': {'id': 'P-1', 'patient_id': 'P-1', 'name': 'Fhir^Test',
             'birth_date': '1990-01-01', 'sex': 'F'}
}


class TestSmartFhirScopes:
    def test_no_scopes_keeps_reads_allowed(self):
        client = TestClient(_make_app(scopes=None))
        mock_conn = AsyncMock()
        mock_conn.__aenter__.return_value = mock_conn
        mock_conn.fetchrow.return_value = PATIENT_HANDLER_ROWS['mock']
        with patch('api.fhir.get_conn', return_value=mock_conn):
            resp = client.get('/fhir/Patient/P-1')
        assert resp.status_code == 200

    def test_read_without_scope_blocked(self):
        client = TestClient(_make_app(scopes=['patient/Patient.read']))
        mock_conn = AsyncMock()
        mock_conn.__aenter__.return_value = mock_conn
        mock_conn.fetchrow.return_value = PATIENT_HANDLER_ROWS['mock']
        with patch('api.fhir.get_conn', return_value=mock_conn):
            resp = client.get('/fhir/ServiceRequest/sr-1')
        # Has Patient.read but not ServiceRequest.read -> 403
        assert resp.status_code == 403
        body = resp.json()
        assert 'scope' in str(body).lower() or 'authorization' in str(body).lower()

    def test_matching_scope_passes(self):
        client = TestClient(_make_app(scopes=_READ_ONLY_SCOPES))
        mock_conn = AsyncMock()
        mock_conn.__aenter__.return_value = mock_conn
        mock_conn.fetchrow.return_value = PATIENT_HANDLER_ROWS['mock']
        with patch('api.fhir.get_conn', return_value=mock_conn):
            resp = client.get('/fhir/Patient/P-1')
        assert resp.status_code == 200

    def test_scope_in_capability_statement(self):
        client = TestClient(_make_app())
        resp = client.get('/fhir/metadata')
        assert resp.status_code == 200
        cs = resp.json()
        sec = cs.get('rest', [{}])[0].get('security', {})
        ext = sec.get('extension', [])
        assert any('smart' in str(e).lower() or 'scopes' in str(e).lower()
                    for e in ext), 'CapabilityStatement must advertise SMART scopes'