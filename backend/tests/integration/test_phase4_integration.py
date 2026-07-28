from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.routing import Route
from starlette.testclient import TestClient

from api.auth import User
from api.fhir import (
    FhirPatientRoot,
    FhirPatientResource,
    FhirImagingStudyRead,
    FhirImagingStudySearch,
)
from api.routing import RoutingHandler


class _FakeAuth(BaseHTTPMiddleware):
    def __init__(self, app, user=None):
        super().__init__(app)
        self._user = user or User({'id': 1, 'permissions': ['PATIENT_READ', 'PATIENT_WRITE', 'DICOMWEB_READ', 'ROUTING_READ', 'ROUTING_WRITE']})

    async def dispatch(self, request, call_next):
        request.scope['user'] = self._user
        request.scope['auth'] = None
        return await call_next(request)


@pytest.mark.asyncio
class TestHl7ToFhirPatientFlow:
    async def test_adt_a01_then_fhir_read(self):
        from services.ingestion.hl7_server import default_handler

        mock_conn = MagicMock()
        mock_conn.fetchval = AsyncMock(return_value=42)
        mock_conn.execute = AsyncMock()
        mock_conn.fetchrow = AsyncMock(return_value={
            'id': 1, 'patient_id': 'PID001', 'name': 'Smith^John',
            'birth_date': '19800101', 'sex': 'M', 'meta': None,
        })
        mock_conn.fetch = AsyncMock(return_value=[])

        with patch('services.ingestion.hl7_server.get_conn') as mock_hl7_conn, \
             patch('api.fhir.get_conn') as mock_fhir_conn:
            mock_hl7_conn.return_value.__aenter__.return_value = mock_conn
            mock_hl7_conn.return_value.__aexit__ = AsyncMock(return_value=None)
            mock_fhir_conn.return_value.__aenter__.return_value = mock_conn
            mock_fhir_conn.return_value.__aexit__ = AsyncMock(return_value=None)

            msg = (
                b'MSH|^~\\&|SENDING|FACILITY|RECV|APP|20250101000000||ADT^A01|MSG001|P|2.5\r'
                b'PID|1||PID001^^^FACILITY^MR||Smith^John||19800101|M\r'
            )
            ack = await default_handler(msg)
            assert ack == b'ACK', f'Expected ACK, got {ack}'

            client = TestClient(_make_fhir_app())
            resp = client.get('/fhir/Patient/PID001')

        assert resp.status_code == 200
        body = resp.json()
        assert body['resourceType'] == 'Patient'
        assert body['id'] == 'PID001'
        assert body['name'][0]['family'] == 'Smith'

    async def test_adt_a01_patient_appears_in_fhir_search(self):
        from services.ingestion.hl7_server import default_handler

        mock_conn = MagicMock()
        mock_conn.fetchval = AsyncMock(return_value=42)
        mock_conn.execute = AsyncMock()
        mock_conn.fetchrow = AsyncMock(return_value={
            'id': 1, 'patient_id': 'PID001', 'name': 'Smith^John',
            'birth_date': '19800101', 'sex': 'M', 'meta': None,
        })
        mock_conn.fetch = AsyncMock(return_value=[{
            'id': 1, 'patient_id': 'PID001', 'name': 'Smith^John',
            'birth_date': '19800101', 'sex': 'M', 'meta': None,
        }])

        with patch('services.ingestion.hl7_server.get_conn') as mock_hl7_conn, \
             patch('api.fhir.get_conn') as mock_fhir_conn:
            mock_hl7_conn.return_value.__aenter__.return_value = mock_conn
            mock_hl7_conn.return_value.__aexit__ = AsyncMock(return_value=None)
            mock_fhir_conn.return_value.__aenter__.return_value = mock_conn
            mock_fhir_conn.return_value.__aexit__ = AsyncMock(return_value=None)

            msg = (
                b'MSH|^~\\&|SENDING|FACILITY|RECV|APP|20250101000000||ADT^A01|MSG001|P|2.5\r'
                b'PID|1||PID001^^^FACILITY^MR||Smith^John||19800101|M\r'
            )
            ack = await default_handler(msg)
            assert ack == b'ACK'

            client = TestClient(_make_fhir_app())
            resp = client.get('/fhir/Patient?identifier=PID001')

        assert resp.status_code == 200
        body = resp.json()
        assert len(body.get('entry', [])) >= 1


class TestRoutingStudyFlow:
    @pytest.mark.asyncio
    async def test_create_rule_then_study_routes(self):
        from services.ingestion.routing import evaluate_routing_rules

        mock_conn = MagicMock()
        mock_conn.fetch = AsyncMock(return_value=[{
            'id': 'r1', 'name': 'CT to PACS-A', 'destination': 'pacs-a.example.com', 'conditions': '{"modality": "CT"}', 'priority': 10, 'enabled': True, 'description': '',
        }])
        mock_conn.fetchval = AsyncMock(return_value='r1')
        mock_conn.execute = AsyncMock()
        mock_conn.fetchrow = AsyncMock(return_value=None)

        with patch('api.routing.get_conn') as mock_api_conn, \
             patch('services.ingestion.routing.get_conn') as mock_engine_conn:
            mock_api_conn.return_value.__aenter__.return_value = mock_conn
            mock_api_conn.return_value.__aexit__ = AsyncMock(return_value=None)
            mock_engine_conn.return_value.__aenter__.return_value = mock_conn
            mock_engine_conn.return_value.__aexit__ = AsyncMock(return_value=None)

            client = TestClient(_make_routing_app())
            resp = client.post('/routing', json={
                'name': 'CT to PACS-A',
                'destination': 'pacs-a.example.com',
                'conditions': {"modality": "CT"},
                'priority': 10,
            })
            assert resp.status_code == 201

            from db.routing_rule import RoutingRule
            mock_conn.fetch = AsyncMock(return_value=[{
                'id': 'r1', 'name': 'CT to PACS-A', 'destination': 'pacs-a.example.com',
                'conditions': '{"modality": "CT"}', 'priority': 10, 'enabled': True,
                'description': '', 'tenant_id': None, 'created_at': None, 'updated_at': None,
            }])
            routes = await evaluate_routing_rules({"modality": "CT"})

        assert len(routes) == 1
        assert routes[0]['destination'] == 'pacs-a.example.com'


def _make_fhir_app():
    return Starlette(
        routes=[
            Route('/fhir/Patient', endpoint=FhirPatientRoot),
            Route('/fhir/Patient/{id}', endpoint=FhirPatientResource),
            Route('/fhir/ImagingStudy', endpoint=FhirImagingStudySearch),
            Route('/fhir/ImagingStudy/{id}', endpoint=FhirImagingStudyRead),
        ],
        middleware=[Middleware(_FakeAuth)],
    )


def _make_routing_app():
    return Starlette(
        routes=[Route('/routing', endpoint=RoutingHandler)],
        middleware=[Middleware(_FakeAuth)],
    )
