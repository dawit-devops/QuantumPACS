"""DICOMweb reverse proxy to the dcm4chee archive (ADR-028 Phase 3).

When `dicom_proxy=true`, the /dicomweb/* surface forwards QIDO-RS, WADO-RS,
frames, WADO-URI, and STOW-RS to the archive so dcm4chee owns pixel storage
and DICOM-level conformance. QuantumPACS still enforces authz (the
per-route permission decorators run before the proxy) and keeps
`/dicomweb/admin*` and the ZIP archive endpoint local.

Tenant scoping is intentionally NOT applied to proxied QIDO-RS: the archive
is a shared store (ADR-028 R7); per-tenant isolation stays in the
QuantumPACS application layer. Dev runs a single tenant, so this is a
documented, accepted limitation.
"""
import json

import httpx
from starlette.responses import Response, StreamingResponse

from config import config
from log import get_logger

log = get_logger(__name__)

# Local archive: generous timeouts so large WADO-RS retrieves are not cut
# mid-stream, but a dead archive still surfaces quickly on connect.
_TIMEOUT = httpx.Timeout(connect=10.0, read=600.0, write=600.0, pool=60.0)

# Headers that carry the DICOMweb negotiation/body contract. Auth cookies
# and CSRF nonces are QuantumPACS-only and must NOT leak to the archive.
_FORWARD_REQUEST_HEADERS = frozenset({
    'accept', 'content-type', 'content-length', 'transfer-syntax',
    'accept-encoding', 'range',
})


def proxy_enabled() -> bool:
    """Whether /dicomweb/* is proxied to dcm4chee (ADR-028 `dicom_proxy`)."""
    return str(config.get('dicom_proxy', 'false')).lower() in ('1', 'true', 'yes', 'on')


def _strip_mount(path: str) -> str:
    """Turn the request path back into the DICOMweb-relative form.

    Routes are mounted under /api (plus /v2 aliases); the archive expects
    the bare PS3.18 paths (/dicomweb/... and /wado).
    """
    for prefix in ('/api/v2', '/api'):
        if path.startswith(prefix):
            return path[len(prefix):] or '/'
    return path


def _archive_path(path: str, ae: str, method: str = 'GET') -> str:
    """Map a QP DICOMweb path onto the archive's REST surface.

    /dicomweb/studies/... -> /aets/{ae}/rs/studies/... (QIDO/WADO-RS/STOW)
    /wado                 -> /aets/{ae}/wado              (WADO-URI)

    Study-scoped STOW-RS is /dicomweb/studies/{uid}/instances in the QP
    surface, but dcm4chee (PS3.18 §10.5) serves it at
    /aets/{ae}/rs/studies/{uid} — the extra /instances segment must be
    dropped or the archive answers 405. Guarded on POST so a future GET
    QIDO-RS /studies/{uid}/instances route is not silently rewritten into
    a study retrieve.
    """
    base = str(config.get('dcm4chee_url', 'http://localhost:8082/dcm4chee-arc')).rstrip('/')
    if path.startswith('/dicomweb/'):
        rel = path[len('/dicomweb'):]
        if (method == 'POST' and rel.endswith('/instances')
                and rel.count('/') == 3):
            # /studies/{uid}/instances (POST STOW-RS) -> /studies/{uid}
            rel = rel[:-len('/instances')]
        return f'{base}/aets/{ae}/rs{rel}'
    if path == '/wado':
        return f'{base}/aets/{ae}/wado'
    raise ValueError(f'No archive route for {path}')


class _RequestBodyStream(httpx.AsyncByteStream):
    """Stream the client request body into httpx without buffering it.

    STOW-RS payloads can be hundreds of MB (capped by max_stow_size_mb in
    the local path); the proxy must not materialize them in memory.
    """

    def __init__(self, request):
        self._stream = request.stream()

    async def __aiter__(self):
        async for chunk in self._stream:
            yield chunk


async def _send(request, client):
    ae = config.get('dcm4chee_ae', 'DCM4CHEE')
    url = _archive_path(_strip_mount(request.url.path), ae, method=request.method)

    headers = {}
    for name in _FORWARD_REQUEST_HEADERS:
        value = request.headers.get(name)
        if value:
            headers[name] = value

    params = request.query_params
    # dcm4chee's WADO-URI (PS3.18 §6.3) requires the DICOMweb requestType
    # property; the QP surface historically omitted it (its local WADO-URI
    # only needed studyUID/seriesUID/objectUID).
    if _strip_mount(request.url.path) == '/wado' and 'requestType' not in params:
        params = params.multi_items() + [('requestType', 'WADO')]

    req = client.build_request(
        request.method,
        url,
        params=params,
        headers=headers,
        content=_RequestBodyStream(request) if request.method in ('POST', 'PUT') else None,
    )
    return await client.send(req, stream=True)


async def proxy_request(request):
    """Forward a DICOMweb request to the archive and stream the reply back."""
    try:
        # The client must outlive the response stream: exiting the async
        # context manager closes the connection while StreamingResponse is
        # still iterating, truncating the body (ReadError after ~16KB).
        client = httpx.AsyncClient(timeout=_TIMEOUT, follow_redirects=False)
        try:
            upstream = await _send(request, client)
        except Exception:
            await client.aclose()
            raise

        response_headers = {}
        for name in ('content-type', 'content-length', 'content-disposition'):
            value = upstream.headers.get(name)
            if value:
                response_headers[name] = value

        async def _stream():
            try:
                async for chunk in upstream.aiter_bytes():
                    yield chunk
            finally:
                await upstream.aclose()
                await client.aclose()

        return StreamingResponse(
            _stream(),
            status_code=upstream.status_code,
            headers=response_headers,
        )
    except httpx.ConnectError as exc:
        log.error('dcm4chee proxy connect failed: %s', exc)
        body = {'error': {'code': 'ARCHIVE_UNAVAILABLE', 'message': 'dcm4chee archive is unreachable'}}
        return Response(json.dumps(body), status_code=502, media_type='application/json')
    except httpx.HTTPError as exc:
        log.error('dcm4chee proxy request failed: %s', exc)
        body = {'error': {'code': 'PROXY_ERROR', 'message': f'dcm4chee proxy error: {exc}'}}
        return Response(json.dumps(body), status_code=502, media_type='application/json')
    except ValueError as exc:
        log.error('dcm4chee proxy route error: %s', exc)
        body = {'error': {'code': 'NOT_FOUND', 'message': 'No archive route for this request'}}
        return Response(json.dumps(body), status_code=404, media_type='application/json')