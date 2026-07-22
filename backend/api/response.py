"""Standardized HTTP response factories for consistent API envelope format.
All endpoints should use these helpers instead of raw JSONResponse."""
from starlette.responses import JSONResponse


def ok(data=None, status=200):
    return JSONResponse(data if data is not None else {}, status_code=status)


def created(data=None):
    return JSONResponse(data if data is not None else {}, status_code=201)


def no_content():
    return JSONResponse({}, status_code=204)


def not_found(message='Not found'):
    return JSONResponse({'error': message}, status_code=404)


def validation_error(message='Validation error'):
    return JSONResponse({'error': message}, status_code=400)


def server_error(message='Internal server error', status_code=500):
    return JSONResponse({'error': message}, status_code=status_code)


def unauthorized(message='Unauthorized'):
    return JSONResponse({'error': message}, status_code=401)


def forbidden(message='Forbidden'):
    return JSONResponse({'error': message}, status_code=403)
