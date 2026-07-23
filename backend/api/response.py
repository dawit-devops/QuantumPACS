"""Standardized HTTP response factories for consistent API envelope format.
All endpoints should use these helpers instead of raw JSONResponse."""
import json
import uuid
from datetime import date, datetime
from typing import Any, Optional
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


def paginated(data, total, page=1, per_page=20, request=None):
    total_pages = max(1, (total + per_page - 1) // per_page)
    path = request.url.path if request else ''
    result = {
        'data': data,
        'meta': {
            'page': page,
            'per_page': per_page,
            'total': total,
            'total_pages': total_pages,
        },
        'links': {
            'self': f'{path}?page={page}&per_page={per_page}',
            'first': f'{path}?page=1&per_page={per_page}',
            'last': f'{path}?page={total_pages}&per_page={per_page}',
        },
    }
    if page > 1:
        result['links']['prev'] = f'{path}?page={page - 1}&per_page={per_page}'
    if page < total_pages:
        result['links']['next'] = f'{path}?page={page + 1}&per_page={per_page}'
    return _JSONResponse(result, status_code=200)


def api_error(code, message, details=None, status=400):
    body = {
        'error': {
            'code': code,
            'message': message,
        }
    }
    if details:
        body['error']['details'] = details
    if status >= 500:
        body['error']['request_id'] = str(uuid.uuid4())[:8]
    return _JSONResponse(body, status_code=status)
