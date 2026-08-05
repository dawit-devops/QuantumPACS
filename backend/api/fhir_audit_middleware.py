import time

from starlette.middleware.base import BaseHTTPMiddleware

from db.conn import get_conn
from db.fhir_audit import FhirAudit
from log import get_logger

log = get_logger(__name__)


class FhirAuditMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        if not request.url.path.startswith('/fhir'):
            return await call_next(request)

        start = time.monotonic()
        response = await call_next(request)
        elapsed_ms = int((time.monotonic() - start) * 1000)

        user = getattr(request, 'user', None)
        user_id = 0
        if user and user.is_authenticated and hasattr(user, 'id') and user.id:
            user_id = user.id

        path_parts = request.path_params or {}
        resource_type = path_parts.get('resource_type', '')
        resource_id = path_parts.get('id', '')

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
