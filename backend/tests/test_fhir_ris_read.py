"""R2-04-01/02 — FHIR R4 read: ServiceRequest + DiagnosticReport (RIS).

ServiceRequest maps a ris_orders row; DiagnosticReport maps a signed
reports row. Both are tenant-scoped by the shared middleware pool routing
and gated by the existing FHIR feature flag.
"""

import pytest

from unittest.mock import AsyncMock, patch

from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.routing import Route
from starlette.testclient import TestClient

from api.auth import User


class _FakeAuth(BaseHTTPMiddleware):
    def __init__(self, app, user=None):
        super().__init__(app)
        self._user = user or User({'id': 1, 'permissions': []})

    async def dispatch(self, request, call_next):
        request.scope['user'] = self._user
        request.scope['auth'] = None
        return await call_next(request)


def _make_app(user=None):
    from api.fhir import (
        FhirServiceRequestRead,
        FhirServiceRequestSearch,
        FhirDiagnosticReportRead,
        FhirDiagnosticReportSearch,
    )

    return Starlette(
        routes=[
            Route('/fhir/ServiceRequest/{id}', endpoint=FhirServiceRequestRead),
            Route('/fhir/ServiceRequest', endpoint=FhirServiceRequestSearch),
            Route('/fhir/DiagnosticReport/{id}',
                  endpoint=FhirDiagnosticReportRead),
            Route('/fhir/DiagnosticReport',
                  endpoint=FhirDiagnosticReportSearch),
        ],
        middleware=[Middleware(_FakeAuth,
                               user=user or User({'id': 1, 'tenant': 'default',
                                                  'permissions': ['*'],
                                                  'admin': True}))],
    )


_ORDER_ROW = {
    'id': '11111111-1111-1111-1111-111111111111',
    'accession_number': 'ACC-FHIR-1', 'patient_id': 'P-1',
    'patient_name': 'Fhir^Test', 'priority': 'STAT', 'status': 'ORDERED',
    'created_at': '2026-08-22T10:00:00+00:00',
}

_REPORT_ROW = {
    'id': '22222222-2222-2222-2222-222222222222',
    'status': 'final', 'findings': 'Mass seen.',
    'impression': 'Probable neoplasm.',
    'signed_at': '2026-08-22T12:00:00+00:00',
    'exam_id': 5,
}


@pytest.fixture
def client():
    c = TestClient(_make_app())
    return c


class TestFhirRisResources:
    def test_service_request_read_maps_ris_order(self, client):
        conn = AsyncMock()
        conn.__aenter__ = AsyncMock(return_value=conn)
        conn.__aexit__ = AsyncMock(return_value=False)
        conn.fetchrow.return_value = _ORDER_ROW
        with patch('api.fhir.get_conn', return_value=conn), \
             patch('api.fhir._is_fhir_enabled', AsyncMock(return_value=True)):
            resp = client.get(
                f"/fhir/ServiceRequest/{_ORDER_ROW['id']}")
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body['resourceType'] == 'ServiceRequest'
        assert body['status'] == 'active'
        assert body['intent'] == 'order'
        assert body['identifier'][0]['value'] == 'ACC-FHIR-1'
        assert body['priority'] == 'stat'

    def test_diagnostic_report_read_maps_signed_report(self, client):
        conn = AsyncMock()
        conn.__aenter__ = AsyncMock(return_value=conn)
        conn.__aexit__ = AsyncMock(return_value=False)
        conn.fetchrow.side_effect = [
            dict(_REPORT_ROW, exam_accession='ACC-FHIR-1'),
            {'accession_number': 'ACC-FHIR-1', 'study_uid': '1.2.3'},
        ]
        with patch('api.fhir.get_conn', return_value=conn), \
             patch('api.fhir._is_fhir_enabled', AsyncMock(return_value=True)):
            resp = client.get(
                f"/fhir/DiagnosticReport/{_REPORT_ROW['id']}")
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body['resourceType'] == 'DiagnosticReport'
        assert body['status'] == 'final'
        assert body.get('conclusion') == 'Probable neoplasm.'

    def test_read_404_when_missing(self, client):
        conn = AsyncMock()
        conn.__aenter__ = AsyncMock(return_value=conn)
        conn.__aexit__ = AsyncMock(return_value=False)
        conn.fetchrow.return_value = None
        with patch('api.fhir.get_conn', return_value=conn), \
             patch('api.fhir._is_fhir_enabled', AsyncMock(return_value=True)):
            resp = client.get('/fhir/ServiceRequest/nope')
        assert resp.status_code == 404

    def test_search_returns_bundle(self, client):
        conn = AsyncMock()
        conn.__aenter__ = AsyncMock(return_value=conn)
        conn.__aexit__ = AsyncMock(return_value=False)
        conn.fetch.return_value = [_ORDER_ROW]
        conn.fetchval.return_value = 1
        with patch('api.fhir.get_conn', return_value=conn), \
             patch('api.fhir._is_fhir_enabled', AsyncMock(return_value=True)):
            resp = client.get('/fhir/ServiceRequest?status=ORDERED')
        assert resp.status_code == 200
        bundle = resp.json()
        assert bundle['resourceType'] == 'Bundle'
        assert bundle['type'] == 'searchset'
        assert bundle['total'] == 1
        assert bundle['entry'][0]['resource']['resourceType'] \
            == 'ServiceRequest'
