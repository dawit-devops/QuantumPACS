"""E2: SMART-on-FHIR scope enforcement middleware.

Maps resource type + HTTP method to the required SMART scope string
and checks it against the `smart_scopes` claim in the JWT. Tokens
without a `smart_scopes` claim (legacy role-gated tokens) pass through
unchanged — the existing `requires_permission` decorator handles them.

Scope grammar follows the SMART App Launch 2.0 specification:
    {context}/{resource}.{operation}
where context = 'patient' | 'user' | 'system' (patient-level only for now),
operation = 'read' | 'write' | '*'.
"""
from starlette.responses import JSONResponse

# Resource-to-scope mapping: the FHIR resource type -> read/write scope suffix.
# The context (patient/) is prepended by the middleware.
_RESOURCE_SCOPES = {
    'Patient': 'Patient',
    'ServiceRequest': 'ServiceRequest',
    'DiagnosticReport': 'DiagnosticReport',
    'ImagingStudy': 'ImagingStudy',
    'DocumentReference': 'DocumentReference',
}

_READ_METHODS = {'GET', 'HEAD', 'OPTIONS'}
_WRITE_METHODS = {'POST', 'PUT', 'PATCH', 'DELETE'}


def _required_scope(resource_type: str, method: str) -> str | None:
    """Return the required scope string, or None if the resource/method
    combination is not governed (falls through to legacy role check)."""
    scope_resource = _RESOURCE_SCOPES.get(resource_type)
    if not scope_resource:
        return None
    if method in _READ_METHODS:
        return f'patient/{scope_resource}.read'
    if method in _WRITE_METHODS:
        return f'patient/{scope_resource}.write'
    return None


def _extract_resource_type(path: str) -> str | None:
    """Infer the FHIR resource type from the URL path.

    Expects paths like /fhir/Patient/{id} or /fhir/ServiceRequest.
    Strips the /fhir/ prefix and takes the next segment.
    """
    parts = path.strip('/').split('/')
    if len(parts) >= 2 and parts[0] == 'fhir':
        return parts[1]
    return None


class FhirScopeMiddleware:
    """SMART-on-FHIR scope check. Runs before the FHIR handler.

    Reads `smart_scopes` from the request scope (populated by the auth
    middleware from the JWT). When the token carries explicit scopes, the
    handler requires a matching scope. Tokens with no scopes claim pass
    through (legacy behaviour).
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http':
            await self.app(scope, receive, send)
            return

        from starlette.requests import Request
        request = Request(scope, receive)

        path = request.url.path
        resource_type = _extract_resource_type(path)
        if not resource_type:
            await self.app(scope, receive, send)
            return

        token_scopes = scope.get('smart_scopes') or None
        if token_scopes is None:
            # No scopes claim — legacy token, let the handler check
            # permissions as before.
            await self.app(scope, receive, send)
            return

        required = _required_scope(resource_type, request.method)
        if required is None:
            await self.app(scope, receive, send)
            return

        if required in token_scopes:
            await self.app(scope, receive, send)
            return

        # Try wildcard: e.g. patient/Patient.* covers both read and write.
        wildcard = required.rsplit('.', 1)[0] + '.*'
        if wildcard in token_scopes:
            await self.app(scope, receive, send)
            return

        response = JSONResponse(
            {'resourceType': 'OperationOutcome',
             'issue': [{
                 'severity': 'error',
                 'code': 'forbidden',
                 'details': {
                     'text': f'Insufficient scope. Required: {required}'
                 },
             }]},
            status_code=403,
        )
        await response(scope, receive, send)