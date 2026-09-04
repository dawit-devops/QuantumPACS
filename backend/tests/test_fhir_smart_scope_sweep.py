"""R2-06-09: SMART-on-FHIR wrong-scope sweep.

Parametrized over the real FHIR route table (tests/fhir_scope_gen.py): every
governed FHIR route/method must reject a token whose SMART scope is for a
*different* resource — a valid-but-wrong scope must never pass the
FhirScopeMiddleware. Complements test_fhir_smart_scopes.py (hand-picked
single-resource cases) with the full generated net.
"""
import pytest

from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.routing import Route
from starlette.testclient import TestClient

from api.auth import User
from tests.fhir_scope_gen import gen_smart_scope_cases


class _FakeAuthWithScope(BaseHTTPMiddleware):
    def __init__(self, app, scopes):
        super().__init__(app)
        self._scopes = scopes

    async def dispatch(self, request, call_next):
        request.scope['user'] = User({'id': 1, 'permissions': ['*'], 'admin': True})
        request.scope['auth'] = None
        request.scope['smart_scopes'] = self._scopes
        return await call_next(request)


def _make_app(path, endpoint, method, scopes):
    from api.fhir_scope_middleware import FhirScopeMiddleware
    return Starlette(
        routes=[Route(path, endpoint=endpoint, methods=[method])],
        middleware=[
            Middleware(_FakeAuthWithScope, scopes=scopes),
            Middleware(FhirScopeMiddleware),
        ],
    )


# Scope for a resource that is never the one under test.
_OTHER_SCOPES = {
    'Patient': ['patient/ServiceRequest.read'],
    'ServiceRequest': ['patient/Patient.read'],
    'DiagnosticReport': ['patient/ImagingStudy.read'],
    'ImagingStudy': ['patient/Patient.read'],
    'DocumentReference': ['patient/Patient.read'],
}

SMART_CASES = gen_smart_scope_cases()


@pytest.mark.parametrize("path,method,resource", SMART_CASES,
                         ids=[f"{m} {p}" for p, m, _ in SMART_CASES])
def test_wrong_resource_scope_is_forbidden(path, method, resource):
    """A SMART token scoped to a different resource must 403 — never reach
    the handler body."""
    from api.routes import _V1_ROUTES
    route = next(r for r in _V1_ROUTES
                 if getattr(r, 'path', None) == path and
                 method in (r.methods or ['GET']))

    scopes = _OTHER_SCOPES.get(resource, [])
    if method not in ('GET', 'HEAD'):
        # Write verbs need a *read* scope at minimum to be a mismatch.
        scopes = [s.replace('.read', '.read') for s in scopes]

    client = TestClient(_make_app(path, route.endpoint, method, scopes))
    resp = client.request(
        method,
        path.replace('{id}', 'P-1'),
        json={} if method in ('POST', 'PUT', 'PATCH') else None,
    )
    assert resp.status_code == 403, (
        f'{method} {path} with a {resource}-mismatched scope must 403, '
        f'got {resp.status_code}'
    )
    body = resp.json()
    detail = body.get('issue', [{}])[0].get('details', {}).get('text', '')
    assert 'Insufficient scope' in detail, (
        f'{method} {path} must return an OperationOutcome with scope detail'
    )
