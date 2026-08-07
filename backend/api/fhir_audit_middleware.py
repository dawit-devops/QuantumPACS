import time

from starlette.middleware.base import BaseHTTPMiddleware

from db.conn import get_conn
from db.fhir_audit import FhirAudit
from log import get_logger

log = get_logger(__name__)


class FhirAuditMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        path = request.url.path
        # Routes mount under /api (Mount('/api', Router(routes))), so match
        # the full prefix — checking '/fhir' alone never fired, silently
        # dropping every FHIR audit record.
        if not (path.startswith('/api/fhir') or path.startswith('/fhir')):
            return await call_next(request)

        start = time.monotonic()
        response = await call_next(request)
        elapsed_ms = int((time.monotonic() - start) * 1000)

        user = getattr(request, 'user', None)
        user_id = 0
        if user and user.is_authenticated and hasattr(user, 'id') and user.id:
            user_id = user.id

        parts = [p for p in path.split('/') if p]
        resource_type = ''
        try:
            # '/api/fhir/Patient/{id}' -> parts[2]; '/fhir/Patient/{id}' -> parts[1];
            # '/api/v2/fhir/Patient/{id}' -> parts[3]
            if parts[0] == 'api' and parts[1] == 'v2':
                resource_type = parts[3] if len(parts) > 3 else ''
            elif parts[0] == 'api' and parts[1] == 'fhir':
                resource_type = parts[2] if len(parts) > 2 else ''
            elif parts[0] == 'fhir':
                resource_type = parts[1] if len(parts) > 1 else ''
        except IndexError:
            resource_type = ''
        resource_id = request.path_params.get('id', '')

        try:
            async with get_conn() as conn:
                audit = FhirAudit(conn)
                await audit.log_request({
                    'user_id': user_id,
                    'method': request.method,
                    'path': request.url.path,
                    'query_params': str(request.url.query),
                    'resource_type': resource_type,
                    'resource_id': resource_id,
                    'status_code': response.status_code,
                    'duration_ms': elapsed_ms,
                    'ip_address': request.client.host if request.client else '',
                })
        except Exception:
            log.exception('Failed to write FHIR audit record')
            pass

        return response
