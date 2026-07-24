import time

import sentry_sdk
from sentry_sdk.integrations.starlette import StarletteIntegration
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.authentication import AuthenticationMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware
from starlette.responses import FileResponse
from starlette.exceptions import HTTPException

import lifecycle
from api.auth import TokenAuth
from api.routes import routes
from api.response import server_error
from api.validate import validation_exception_handler, _ValidationException
from config import is_docker, config
from log import setup_logging, get_logger

setup_logging()
log = get_logger(__name__)

if config.get('sentry_dsn'):
    sentry_sdk.init(
        dsn=config['sentry_dsn'],
        integrations=[StarletteIntegration()],
    )


class CustomMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        start = time.monotonic()
        response = await call_next(request)
        elapsed = time.monotonic() - start

        if is_docker and not request.url.path.startswith('/api') and response.status_code == 404:
            response = FileResponse('./static/index.html')

        if response.status_code >= 500:
            log.error('%s %s -> %s (%.3fs)', request.method, request.url.path, response.status_code, elapsed)
        elif response.status_code >= 400:
            log.warning('%s %s -> %s (%.3fs)', request.method, request.url.path, response.status_code, elapsed)
        else:
            log.info('%s %s -> %s (%.3fs)', request.method, request.url.path, response.status_code, elapsed)

        cors_origin = config.get('cors_origins', '*')
        response.headers['Access-Control-Allow-Origin'] = cors_origin
        response.headers['Access-Control-Allow-Methods'] = 'OPTIONS,GET,POST,DELETE'
        response.headers['Access-Control-Allow-Headers'] = 'Origin,Accept,X-Auth-Pacs,Content-Type,X-Requested-With'
        return response


async def http_exception(request, exc):
    resp = server_error(exc.detail if hasattr(exc, 'detail') else '', status_code=exc.status_code)
    cors_origin = config.get('cors_origins', '*')
    resp.headers['Access-Control-Allow-Origin'] = cors_origin
    return resp


async def startup():
    await lifecycle.setup()


app = Starlette(
    routes=routes,
    middleware=[
        Middleware(AuthenticationMiddleware, backend=TokenAuth(), on_error=TokenAuth.on_auth_error),
        Middleware(TrustedHostMiddleware, allowed_hosts=config.get('allowed_hosts', 'localhost,127.0.0.1').split(',')),
        Middleware(CustomMiddleware),
    ],
    exception_handlers={
        HTTPException: http_exception,
        _ValidationException: validation_exception_handler,
    },
    on_startup=[startup],
)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host='localhost', port=8080)
