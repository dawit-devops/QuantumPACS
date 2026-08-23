"""SMART-on-FHIR wrong-scope sweep generator (R2-06-09 hardening).

Reads the real FHIR route table from `api.routes._V1_ROUTES` and emits a
`(path, method, resource_type)` case for every route whose resource type is
governed by FhirScopeMiddleware._RESOURCE_SCOPES. Each case is asserted to
return 403 when the token carries a SMART scope for a *different* resource —
the security-critical negative that a valid but wrong scope must never pass.

Lives in tests/; no production code depends on it.
"""
from starlette.routing import Route

# Mirror the governed set in api.fhir_scope_middleware._RESOURCE_SCOPES.
_GOVERNED_RESOURCES = {
    'Patient', 'ServiceRequest', 'DiagnosticReport',
    'ImagingStudy', 'DocumentReference',
}


def _iter_fhir_routes():
    from api.routes import _V1_ROUTES
    seen = set()
    for r in _V1_ROUTES:
        if not isinstance(r, Route):
            continue
        path = r.path
        if not path.startswith('/fhir/'):
            continue
        # /fhir/admin/* is SYSTEM_ADMIN-only platform config — not
        # SMART-resource-governed; /fhir/metadata advertises scopes but is
        # not itself scope-gated.
        if path.startswith('/fhir/admin/'):
            continue
        if path == '/fhir/metadata':
            continue
        parts = path.strip('/').split('/')
        resource = parts[1] if len(parts) >= 2 else None
        if resource not in _GOVERNED_RESOURCES:
            continue
        for m in (r.methods or ['GET']):
            if m == 'OPTIONS':
                continue
            key = (path, m)
            if key in seen:
                continue
            seen.add(key)
            yield path, m, resource


def gen_smart_scope_cases():
    """(path, method, resource_type) for every governed FHIR route/method."""
    return list(_iter_fhir_routes())
