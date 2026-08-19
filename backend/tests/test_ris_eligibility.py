"""S3-14 — Insurance eligibility stub.

RIS-AC-P04-02: GET /api/ris/patients/{id}/eligibility returns
{"status": "active"} for any patient — the stub satisfies the check-in
flow today; real payer API integration is deferred to v1.1.
"""

from unittest.mock import AsyncMock, patch

import pytest
from starlette.applications import Starlette
from starlette.exceptions import HTTPException
from starlette.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.routing import Route
from starlette.testclient import TestClient

from api.auth import User
from api.validate import validation_exception_handler, _ValidationException


def _http_exception(request, exc):
    from starlette.responses import JSONResponse
    return JSONResponse(
        {'error': exc.detail if hasattr(exc, 'detail') else ''},
        status_code=exc.status_code,
    )


class _FakeAuth(BaseHTTPMiddleware):
    def __init__(self, app, user=None):
        super().__init__(app)
        self._user = user or User({'id': 1, 'permissions': []})

    async def dispatch(self, request, call_next):
        request.scope['user'] = self._user
        request.scope['auth'] = None
        return await call_next(request)


def _make_app(user=None):
    from api.frontdesk import RisPatientEligibilityHandler
    return Starlette(
        routes=[
            Route('/ris/patients/{id}/eligibility', endpoint=RisPatientEligibilityHandler),
        ],
        middleware=[Middleware(_FakeAuth, user=user)],
        exception_handlers={
            HTTPException: _http_exception,
            _ValidationException: validation_exception_handler,
        },
    )


@pytest.fixture
def eligibility_patches():
    patchers = [
        patch('api.frontdesk.get_conn'),
        patch('api.frontdesk.FrontDesk'),
    ]
    started = [p.start() for p in patchers]
    yield {
        'get_conn': started[0],
        'FrontDesk': started[1],
    }
    for p in patchers:
        p.stop()


def _fd(eligibility_patches):
    fd = AsyncMock()
    eligibility_patches['FrontDesk'].return_value = fd
    return fd


class TestInsuranceEligibilityStub:
    """S3-14 — eligibility endpoint returns active for any patient."""

    def test_eligibility_returns_active(self, eligibility_patches):
        fd = _fd(eligibility_patches)
        fd.get_patient.return_value = {
            'id': 1, 'patient_id': 'MRN-001', 'name': 'Jane Doe',
        }

        client = TestClient(_make_app(User({'id': 1, 'permissions': ['PATIENT_READ']})))
        resp = client.get('/ris/patients/MRN-001/eligibility')

        assert resp.status_code == 200
        data = resp.json()['data']
        assert data['status'] == 'active'
        assert data['patient_id'] == 'MRN-001'
        assert data['provider'] == 'stub'

    def test_eligibility_unknown_patient_404(self, eligibility_patches):
        fd = _fd(eligibility_patches)
        fd.get_patient.return_value = None

        client = TestClient(_make_app(User({'id': 1, 'permissions': ['PATIENT_READ']})))
        resp = client.get('/ris/patients/NOPE/eligibility')
        assert resp.status_code == 404

    def test_eligibility_requires_patient_read(self, eligibility_patches):
        client = TestClient(_make_app(User({'id': 1, 'permissions': []})))
        resp = client.get('/ris/patients/MRN-001/eligibility')
        assert resp.status_code == 403

    def test_eligibility_includes_timestamp(self, eligibility_patches):
        fd = _fd(eligibility_patches)
        fd.get_patient.return_value = {
            'id': 1, 'patient_id': 'MRN-001', 'name': 'Jane Doe',
        }

        client = TestClient(_make_app(User({'id': 1, 'permissions': ['PATIENT_READ']})))
        resp = client.get('/ris/patients/MRN-001/eligibility')

        assert resp.status_code == 200
        data = resp.json()['data']
        assert 'checked_at' in data
