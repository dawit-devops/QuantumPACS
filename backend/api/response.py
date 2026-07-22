"""Standardized HTTP response factories for consistent API envelope format.
All endpoints should use these helpers instead of raw JSONResponse."""
import json
from datetime import date, datetime
from typing import Any
from starlette.responses import JSONResponse as _StarletteJSONResponse


def _default(obj):
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    raise TypeError(f'Object of type {type(obj)} is not JSON serializable')


class _JSONResponse(_StarletteJSONResponse):
    def render(self, content: Any) -> bytes:
        return json.dumps(
            content,
            ensure_ascii=False,
            allow_nan=False,
            indent=None,
            separators=(',', ':'),
            default=_default,
        ).encode('utf-8')


def ok(data=None, status=200):
    return _JSONResponse(data if data is not None else {}, status_code=status)


def created(data=None):
    return _JSONResponse(data if data is not None else {}, status_code=201)


def no_content():
    return _JSONResponse({}, status_code=204)


def not_found(message='Not found'):
    return _JSONResponse({'error': message}, status_code=404)


def validation_error(message='Validation error'):
    return _JSONResponse({'error': message}, status_code=400)


def server_error(message='Internal server error', status_code=500):
    return _JSONResponse({'error': message}, status_code=status_code)


def unauthorized(message='Unauthorized'):
    return _JSONResponse({'error': message}, status_code=401)


def forbidden(message='Forbidden'):
    return _JSONResponse({'error': message}, status_code=403)
