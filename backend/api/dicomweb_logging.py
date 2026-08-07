"""DICOMweb request logging middleware.

Every DICOMweb service request (QIDO-RS, WADO-RS, WADO-URI, STOW-RS, frame
retrieval, archive export) is recorded as a `dicomweb.request` audit row so
the admin metrics tab can report request volume, kind mix, and error rates.

Pure ASGI (not BaseHTTPMiddleware) on purpose: STOW-RS streams the request
body part-by-part and WADO-RS streams multipart responses, and the
BaseHTTPMiddleware wrapper buffers both. Placed outside
AuthenticationMiddleware so rejected requests (401) are recorded too — the
actor stays null for those.
"""
import json
import time
import uuid

from db.conn import get_conn
from log import get_logger

log = get_logger(__name__)

# Path segments that end a QIDO-RS *query* (as opposed to a WADO-RS
# retrieval, which ends with a UID).
_LEVEL_SEGMENTS = frozenset({'studies', 'series', 'instances'})

# Kind mix shown in the admin metrics tab. STOW is the only write flow, so
# method disambiguates it; the rest are shape-based.
_KIND_BY_SHAPE = (
    ('/frames/', 'frames'),
    ('/archive', 'archive'),
)


def classify_request(method: str, path: str) -> str:
    """Map a DICOMweb request to the metric kind it counts as.

    `stow` for any POST (the store flow owns all write verbs), `wado` for
    retrievals that end in a UID, `qido` for level queries that end in a
    collection segment, plus the `frames`/`archive`/`wado_uri` specials.
    """
    if method == 'POST':
        return 'stow'
    for marker, kind in _KIND_BY_SHAPE:
        if marker in path:
            return kind
    if path.endswith('/wado'):
        return 'wado_uri'
    idx = path.find('/dicomweb/')
    if idx != -1:
        tail = path[idx + len('/dicomweb/'):].rstrip('/')
        last = tail.rsplit('/', 1)[-1]
        if method == 'GET' and last in _LEVEL_SEGMENTS:
            return 'qido'
    return 'wado'


class DicomWebLogMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope.get('type') != 'http':
            await self.app(scope, receive, send)
            return
        method = scope.get('method', 'GET')
        path = scope.get('path', '')
        if method == 'OPTIONS' or not self._is_dicomweb(path):
            await self.app(scope, receive, send)
            return

        status = {}
        start = time.monotonic()

        async def send_wrapper(message):
            if message.get('type') == 'http.response.start':
                status['code'] = message.get('status', 500)
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        except Exception:
            # The app-level exception handler turns this into a 500 response;
            # record that status rather than masking the original error.
            status.setdefault('code', 500)
            raise
        finally:
            await self._record(scope, method, path, status.get('code'), start)

    @staticmethod
    def _is_dicomweb(path):
        # Only the service routes; the /dicomweb/admin introspection pages are
        # management traffic, not DICOMweb service traffic.
        if not path.startswith('/api'):
            return False
        if '/dicomweb/admin' in path:
            return False
        return '/dicomweb/' in path or path.endswith('/wado')

    async def _record(self, scope, method, path, status_code, start):
        try:
            # AuthenticationMiddleware populates scope['user'] on the way
            # down; by the time we run, it reflects the authenticated actor
            # (or is absent for rejected requests).
            user = scope.get('user')
            actor = getattr(user, 'id', None)
            tenant = getattr(user, 'tenant', None)
            payload = json.dumps({
                'event': 'dicomweb.request',
                'actor': actor,
                'resource': {'type': 'dicomweb', 'id': classify_request(method, path)},
                'detail': {
                    'method': method,
                    'path': path,
                    'status': status_code,
                    'duration_ms': int((time.monotonic() - start) * 1000),
                    'kind': classify_request(method, path),
                },
                'tenant': tenant,
            })
            # Logs land on the main database: the tenant-scoped acquire
            # contextvar is already reset by the time this middleware (outer
            # to TenantMiddleware) runs.
            async with get_conn() as conn:
                await conn.execute(
                    'INSERT INTO logs (log, tenant, request_id, trace_id)'
                    ' VALUES ($1, $2, $3, $4)',
                    payload, tenant, None, str(uuid.uuid4()),
                )
        except Exception:
            # Never let audit-logging failure break the response path.
            log.warning('Failed to record DICOMweb request log: %s %s', method, path, exc_info=True)
