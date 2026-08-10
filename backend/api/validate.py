"""Request body parsing with Pydantic v2 validation.
Usage: data = await parse_body(MySchema, request)
Returns validated model or raises _ValidationException caught by middleware."""
import json

from pydantic import ValidationError

from api.response import api_error, apply_cors_headers

# R2-M6: hard cap on request bodies (1MB). Without one, request.json()
# buffers an attacker-controlled stream fully into memory on every
# unauthenticated-ish endpoint (login, refresh, OAuth token).
MAX_BODY_BYTES = 1024 * 1024


async def read_body(request) -> bytes:
    """Read the request body with a hard cap. Raises _BodyTooLargeException
    (→ 413) beyond MAX_BODY_BYTES. The read is cached into request._body so
    later request.body()/request.json() calls reuse it instead of re-reading
    the (already consumed) stream."""
    if hasattr(request, '_body'):
        body = request._body or b''
        if len(body) > MAX_BODY_BYTES:
            raise _BodyTooLargeException()
        return body
    chunks = []
    size = 0
    async for chunk in request.stream():
        size += len(chunk)
        if size > MAX_BODY_BYTES:
            raise _BodyTooLargeException()
        chunks.append(chunk)
    body = b''.join(chunks)
    request._body = body
    return body


async def parse_body(model_class, request):
    try:
        raw = await read_body(request)
    except _BodyTooLargeException:
        raise
    try:
        data = json.loads(raw) if raw else {}
    except (json.JSONDecodeError, UnicodeDecodeError):
        # Empty or malformed JSON bodies (e.g. a client that only sends
        # cookies) must yield a validation error, never an unhandled 500.
        data = {}
    if not isinstance(data, dict):
        # A JSON array/string body would crash model_class(**data) with a
        # TypeError — treat it as unparsable, not as a 500.
        data = {}
    try:
        return model_class(**data)
    except ValidationError as e:
        errors = e.errors()
        details = [
            {
                'field': '.'.join(str(p) for p in err['loc']),
                'message': err['msg'],
                'type': err.get('type', ''),
            }
            for err in errors
        ]
        raise _ValidationException(details)


class _ValidationException(Exception):
    def __init__(self, details, status=422):
        self.details = details
        self.status = status


class _BodyTooLargeException(_ValidationException):
    def __init__(self):
        super().__init__(
            [{
                'field': 'body',
                'message': f'Request body exceeds {MAX_BODY_BYTES // (1024 * 1024)}MB limit',
                'type': 'body_too_large',
            }],
            status=413,
        )


def validation_exception_handler(request, exc):
    return apply_cors_headers(
        request,
        api_error(
            'VALIDATION_ERROR',
            'Request validation failed',
            details=exc.details,
            status=exc.status,
        ),
    )
