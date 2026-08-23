"""Shared FHIR conformance harness (E3, GAP_AUDIT_TDD_PIPELINE.md).

Plan R2-05-03 wants one test harness shared by the PACS FHIR suite
(tests/integration/test_fhir.py) and the RIS FHIR suite
(tests/test_fhir_ris_read.py) instead of two bespoke `_make_app`
factories. Provides:

- `make_fhir_app`: Starlette app with the FHIR routes + a fake auth
  middleware, reusing the exact handlers the suites already import.
- `make_fhir_client`: TestClient wrapper.
- `assert_capability_statement`: CapabilityStatement conformance checks.
- `bundle_entries` / `next_link`: Bundle paging helpers.
- `scope_token`: SMART-on-FHIR scope-token helper (E2) — mint a JWT
  carrying smart_scopes, or return None when no scopes are requested so
  legacy-role behaviour is exercised.
"""
import pytest

from unittest.mock import AsyncMock, MagicMock, patch

from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.routing import Route
from starlette.testclient import TestClient

from api.auth import User


class _FakeAuth(BaseHTTPMiddleware):
    """Injects a user into the request scope, matching how the real
    AuthenticationMiddleware resolves identity. Optional `scopes` puts a
    smart_scopes claim into the scope for the E2 scope middleware."""

    def __init__(self, app, user=None, scopes=None):
        super().__init__(app)
        self._user = user or User({'id': 1, 'permissions': []})
        self._scopes = scopes

    async def dispatch(self, request, call_next):
        request.scope['user'] = self._user
        request.scope['auth'] = None
        if self._scopes is not None:
            request.scope['smart_scopes'] = self._scopes
        return await call_next(request)


def make_fhir_app(user=None, extra_routes=None, scopes=None,
                  fhir_scope_middleware=False):
    """Build a Starlette app with the core FHIR routes.

    extra_routes: additional Route objects appended after the defaults.
    scopes + fhir_scope_middleware: mount the E2 FhirScopeMiddleware so a
    suite can exercise SMART scope enforcement without re-implementing it.
    """
    from api.fhir import (
        FhirMetadata,
        FhirPatientRoot, FhirPatientResource,
        FhirImagingStudyRead, FhirImagingStudySearch,
        FhirDocumentReferenceRead, FhirDocumentReferenceSearch,
    )

    routes = [
        Route('/fhir/metadata', endpoint=FhirMetadata),
        Route('/fhir/Patient', endpoint=FhirPatientRoot),
        Route('/fhir/Patient/{id}', endpoint=FhirPatientResource),
        Route('/fhir/ImagingStudy', endpoint=FhirImagingStudySearch),
        Route('/fhir/ImagingStudy/{id}', endpoint=FhirImagingStudyRead),
        Route('/fhir/DocumentReference', endpoint=FhirDocumentReferenceSearch),
        Route('/fhir/DocumentReference/{id}', endpoint=FhirDocumentReferenceRead),
    ]
    if extra_routes:
        routes.extend(extra_routes)
    middleware = [Middleware(_FakeAuth, user=user, scopes=scopes)]
    if fhir_scope_middleware:
        from api.fhir_scope_middleware import FhirScopeMiddleware
        middleware.append(Middleware(FhirScopeMiddleware))
    return Starlette(routes=routes, middleware=middleware)


def make_fhir_client(user=None, extra_routes=None, scopes=None,
                     fhir_scope_middleware=False):
    """TestClient around make_fhir_app with the same knobs."""
    return TestClient(make_fhir_app(
        user=user, extra_routes=extra_routes, scopes=scopes,
        fhir_scope_middleware=fhir_scope_middleware,
    ))


def assert_capability_statement(resp, expected_types):
    """Validate a /fhir/metadata CapabilityStatement response.

    Checks resourceType, FHIR version, content-type and the advertised
    resource types (expected_types is a set of resource type names).
    """
    assert resp.status_code == 200
    assert resp.headers['content-type'] == 'application/fhir+json'
    body = resp.json()
    assert body['resourceType'] == 'CapabilityStatement'
    assert body['fhirVersion'] == '4.0.1'
    rest = body['rest'][0]
    types = {r['type'] for r in rest['resource']}
    assert types == expected_types


def bundle_entries(resp):
    """Return the Bundle.entry list from a search response."""
    body = resp.json()
    assert body['resourceType'] == 'Bundle', 'search must return a Bundle'
    return body.get('entry', [])


def next_link(resp):
    """Return the pagination URL for a Bundle, or None when absent."""
    body = resp.json()
    for link in body.get('link', []):
        if link.get('relation') == 'next':
            return link.get('url')
    return None


def scope_token(user, smart_scopes):
    """Mint a JWT carrying SMART scopes (E2) for a fake user dict.

    Returns None when smart_scopes is None so tests can exercise legacy
    role-gated tokens (no scopes claim) with the same call site.
    """
    if smart_scopes is None:
        return None
    from api.tokens import create_token
    return create_token(user, smart_scopes=smart_scopes)
