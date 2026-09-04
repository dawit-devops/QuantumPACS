"""F2 (GAP_AUDIT_TDD_PIPELINE.md): RIS RBAC matrix + IDOR generator.

Builds the RIS route catalog from `api.routes._V1_ROUTES` (the real wiring,
so a new RIS route is swept automatically) and generates:

- `gen_negative_cases()`: every RIS route/method -> (route, method) pairs
  for the RBAC negative sweep. Each is asserted 401 anonymous / 403 with
  no permissions in test_rbac_matrix_gen.py.
- `gen_idor_cases()`: RIS GET/PUT/DELETE handlers that address a resource
  by `{id}` path param -> (path_template, handler, method) for the IDOR
  parametrization (foreign tenant id must fail closed).

This lives in tests/ and runs in the CI suite; no production code depends
on it.
"""
from starlette.routing import Route


def _iter_ris_routes():
    from api.routes import _V1_ROUTES
    seen = set()
    for r in _V1_ROUTES:
        if not isinstance(r, Route):
            continue
        path = r.path
        if not path.startswith('/ris/'):
            continue
        methods = r.methods or ['GET']
        for m in methods:
            # OPTIONS (CORS preflight) and the kiosk check-in path
            # (public HMAC-token auth) are not RBAC-gated.
            if m == 'OPTIONS' or path.startswith('/ris/checkin/'):
                continue
            key = (path, m)
            if key in seen:
                continue
            seen.add(key)
            yield r, path, m


def gen_negative_cases():
    """(route_obj, path, method) for every RIS route/method the handler
    actually implements (an HTTPEndpoint with only `put` returns 405 for
    GET before the RBAC gate runs, so we only sweep implemented verbs)."""
    out = []
    for r, path, method in _iter_ris_routes():
        if hasattr(r.endpoint, method.lower()):
            out.append((r, path, method))
    return out


def gen_idor_cases():
    """(path_template, endpoint, method) for RIS routes addressing {id}.

    An IDOR-prone handler addresses a tenant-scoped resource by a path id.
    GET-by-id/PUT/DELETE on such a route is the classic cross-tenant
    manipulation vector; the sweep asserts a foreign id fails closed.
    Only methods the handler actually implements are emitted (Starlette
    HTTPEndpoint dispatch maps each verb to a method on the class).
    """
    out = []
    for r, path, method in _iter_ris_routes():
        if '{id}' not in path:
            continue
        if method not in ('GET', 'PUT', 'DELETE', 'POST'):
            continue
        # HTTPEndpoint implements each verb as `async def get/put/...`.
        if not hasattr(r.endpoint, method.lower()):
            continue
        out.append((path, r.endpoint, method))
    return out
