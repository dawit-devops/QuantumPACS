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
from api.telemetry import RequestIDMiddleware, http_requests_in_progress, record_request
from api.tracing_middleware import TracingMiddleware
from api.validate import validation_exception_handler, _ValidationException
from config import is_docker, config, assert_production_secret
from log import setup_logging, get_logger, tenant_var, user_id_var
from services.interfaces import (
    AuthService,
    MetadataService,
    NotificationService,
    SearchService,
    ServiceRegistry,
    StorageService,
)

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
        start = time.monotonic()
        path = request.url.path
        if request.method == 'OPTIONS' and path.startswith('/api'):
            cors_origin = config.get('cors_origins', '*')
            resp = Response(status_code=200)
            resp.headers['Access-Control-Allow-Origin'] = cors_origin
            resp.headers['Access-Control-Allow-Methods'] = 'OPTIONS,GET,POST,DELETE'
            resp.headers['Access-Control-Allow-Headers'] = 'Origin,Accept,X-Auth-Pacs,Content-Type,X-Requested-With'
            record_request(request.method, path, 200, time.monotonic() - start)
            return resp
        http_requests_in_progress.labels(method=request.method, path=path).inc()
        try:
            response = await call_next(request)
        except Exception:
            log.exception('Unhandled error processing %s %s', request.method, request.url.path)
            elapsed = time.monotonic() - start
            http_requests_in_progress.labels(method=request.method, path=request.url.path).dec()
            record_request(request.method, request.url.path, 500, elapsed)
            cors_origin = config.get('cors_origins', '*')
            resp = server_error('Internal server error', status_code=500)
            resp.headers['Access-Control-Allow-Origin'] = cors_origin
            return resp
        elapsed = time.monotonic() - start
        http_requests_in_progress.labels(method=request.method, path=request.url.path).dec()

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
    await lifecycle.setup(services=registry)
    await _register_services(registry)
    yield
    await lifecycle.teardown()


async def _register_services(registry):
    from db.conn import get_conn
    from db.replica import Replica
    from es import es as es_mod
    from services.auth.db_auth_service import DatabaseAuthService
    from services.metadata.pg_metadata import PgMetadataService
    from services.notification.redis_notification_service import RedisNotificationService
    from services.search.es_search_adapter import EsSearchServiceAdapter
    from services.storage.local_storage_adapter import StorageServiceAdapter
    from storage.storage import Storage

    registry.register(MetadataService, PgMetadataService(conn_provider=get_conn))
    registry.register(SearchService, EsSearchServiceAdapter(es_module=es_mod))
    registry.register(AuthService, DatabaseAuthService(conn_provider=get_conn))
    registry.register(NotificationService, RedisNotificationService())

    try:
        async with get_conn() as conn:
            replica = await Replica(conn).master()
        if replica:
            storage = await Storage.get(replica)
            registry.register(StorageService, StorageServiceAdapter(storage))
        else:
            log.warning('No master replica configured; StorageService not registered')
    except Exception:
        log.warning('Failed to register StorageService', exc_info=True)


app = Starlette(
    routes=routes,
    middleware=[
        Middleware(TracingMiddleware),
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
