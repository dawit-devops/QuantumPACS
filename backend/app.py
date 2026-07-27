from contextlib import asynccontextmanager

import sentry_sdk
from sentry_sdk.integrations.starlette import StarletteIntegration
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.authentication import AuthenticationMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware
from starlette.responses import FileResponse, Response
from starlette.exceptions import HTTPException

import lifecycle
from api.auth import TokenAuth
from api.routes import routes
from api.response import server_error
from api.service_middleware import ServiceMiddleware
from api.tenant_middleware import TenantMiddleware
from api.fhir_audit_middleware import FhirAuditMiddleware
from api.telemetry import RequestIDMiddleware, record_request
from api.validate import validation_exception_handler, _ValidationException
from config import is_docker, config, assert_production_secret
from log import setup_logging, get_logger, tenant_var, user_id_var
from services.interfaces import ServiceRegistry

setup_logging()
log = get_logger(__name__)

if config.get('sentry_dsn'):
    sentry_sdk.init(
        dsn=config['sentry_dsn'],
        integrations=[StarletteIntegration()],
    )


class CustomMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        import time
        
        if request.method == 'OPTIONS':
            response = Response(status_code=200)
            cors_origin = config.get('cors_origins', '*')
            response.headers['Access-Control-Allow-Origin'] = cors_origin
            response.headers['Access-Control-Allow-Methods'] = 'OPTIONS,GET,POST,PUT,DELETE'
            response.headers['Access-Control-Allow-Headers'] = 'Origin,Accept,X-Auth-Pacs,Content-Type,X-Requested-With'
            return response
        
        start = time.monotonic()
        try:
            response = await call_next(request)
        except Exception:
            log.exception('Unhandled error processing %s %s', request.method, request.url.path)
            elapsed = time.monotonic() - start
            record_request(request.method, request.url.path, 500, elapsed)
            cors_origin = config.get('cors_origins', '*')
            resp = server_error('Internal server error', status_code=500)
            resp.headers['Access-Control-Allow-Origin'] = cors_origin
            return resp
        elapsed = time.monotonic() - start

        user = getattr(request, 'user', None)
        if user and user.is_authenticated:
            if hasattr(user, 'id') and user.id:
                user_id_var.set(str(user.id))
            if hasattr(user, 'tenant') and user.tenant:
                tenant_var.set(user.tenant)

        path = request.url.path
        if path.startswith('/api') and response.status_code < 500:
            log.info('%s %s -> %s (%.3fs)', request.method, path, response.status_code, elapsed)
        elif response.status_code >= 500:
            log.error('%s %s -> %s (%.3fs)', request.method, path, response.status_code, elapsed)
        elif response.status_code >= 400:
            log.warning('%s %s -> %s (%.3fs)', request.method, path, response.status_code, elapsed)
        record_request(request.method, path, response.status_code, elapsed)

        if is_docker and not path.startswith('/api') and response.status_code == 404:
            response = FileResponse('./static/index.html')

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


async def server_error_handler(request, exc):
    log.exception('Unhandled server error: %s %s', request.method, request.url.path)
    resp = server_error('Internal server error', status_code=500)
    cors_origin = config.get('cors_origins', '*')
    resp.headers['Access-Control-Allow-Origin'] = cors_origin
    return resp


@asynccontextmanager
async def lifespan(app):
    assert_production_secret()
    registry = ServiceRegistry()
    app.state.services = registry
    await lifecycle.setup()
    yield
    await lifecycle.teardown()


app = Starlette(
    routes=routes,
    middleware=[
        Middleware(AuthenticationMiddleware, backend=TokenAuth(), on_error=TokenAuth.on_auth_error),
        Middleware(TenantMiddleware),
        Middleware(FhirAuditMiddleware),
        Middleware(ServiceMiddleware),
        Middleware(TrustedHostMiddleware, allowed_hosts=config.get('allowed_hosts', 'localhost,127.0.0.1').split(',')),
        Middleware(RequestIDMiddleware),
        Middleware(CustomMiddleware),
    ],
    exception_handlers={
        HTTPException: http_exception,
        _ValidationException: validation_exception_handler,
        Exception: server_error_handler,
    },
    lifespan=lifespan,
)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host='localhost', port=8080)
