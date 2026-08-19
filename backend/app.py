from contextlib import asynccontextmanager
from http import HTTPStatus
import time

import sentry_sdk
from sentry_sdk.integrations.starlette import StarletteIntegration
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.authentication import AuthenticationMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware
from starlette.responses import FileResponse, Response
from starlette.exceptions import HTTPException

import lifecycle
import api.ws as ws_module
import api.auth as auth_module
import api.telemetry as telemetry_module
import api.admin as admin_module
from api.auth import TokenAuth
from api.routes import routes
from api.response import server_error, apply_cors_headers, api_error
from api.tenant_middleware import TenantMiddleware
from api.fhir_audit_middleware import FhirAuditMiddleware
from api.telemetry import RequestIDMiddleware, http_requests_in_progress, record_request
from api.tracing_middleware import TracingMiddleware
from api.dicomweb_logging import DicomWebLogMiddleware
from api.validate import validation_exception_handler, _ValidationException
from config import is_docker, config, assert_production_secret
from exceptions import ConfigurationError
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

sentry_sdk.init(
    dsn=config.get('sentry_dsn', ''),
    traces_sample_rate=float(config.get('sentry_traces_sample_rate', '1.0')),
    integrations=[StarletteIntegration()],
)

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        response.headers['Content-Security-Policy'] = "default-src 'self'"
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        response.headers['X-Permitted-Cross-Domain-Policies'] = 'none'
        return response


class CustomMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        start = time.monotonic()
        path = request.url.path
        if request.method == 'OPTIONS' and path.startswith('/api'):
            resp = Response(status_code=200)
            record_request(request.method, path, 200, time.monotonic() - start)
            return resp
        http_requests_in_progress.labels(method=request.method, path=path).inc()
        # Maintenance write-gate (super_admin review P1-2): while the flag is
        # active every non-read /api write returns a readable 503. Auth grants
        # and the maintenance control itself stay reachable (exempt list) so
        # users can still log in/out and the operator can turn it back off.
        if (
            request.method not in ('GET', 'HEAD', 'OPTIONS')
            and path.startswith('/api')
            and admin_module.maintenance_active()
            and not admin_module.maintenance_exempt(path)
        ):
            resp = api_error(
                'MAINTENANCE',
                'System is in maintenance mode — writes are paused. Please retry later.',
                status=503,
            )
            http_requests_in_progress.labels(method=request.method, path=path).dec()
            record_request(request.method, path, 503, 0.0)
            return apply_cors_headers(request, resp)
        try:
            response = await call_next(request)
        except Exception:
            log.exception('Unhandled error processing %s %s', request.method, request.url.path)
            elapsed = time.monotonic() - start
            http_requests_in_progress.labels(method=request.method, path=request.url.path).dec()
            record_request(request.method, request.url.path, 500, elapsed)
            resp = server_error('Internal server error', status_code=500)
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

        if is_docker() and not path.startswith('/api') and response.status_code == 404:
            response = FileResponse('./static/index.html')

        return response


class CSRFMiddleware(BaseHTTPMiddleware):
    _PUBLIC_PATHS = frozenset({
        '/api/login', '/api/v2/login',
        '/api/auth/refresh', '/api/v2/auth/refresh',
        '/api/health', '/api/v2/health',
        '/api/auth/logout', '/api/v2/auth/logout',
        '/api/oauth/login', '/api/v2/oauth/login',
        '/api/oauth/callback', '/api/v2/oauth/callback',
        '/api/oauth/token', '/api/v2/oauth/token',
    })

    async def dispatch(self, request, call_next):
        path = request.url.path
        if request.method in ('POST', 'PUT', 'DELETE') and path.startswith('/api'):
            # DICOMweb and FHIR are machine-to-machine APIs (modalities, RIS,
            # other PACS, SMART apps) authenticated by bearer token — browsers
            # don't drive them, so the anti-CSRF cookie dance does not apply
            # (it would break plain STOW-RS and FHIR clients that cannot mint
            # an X-CSRF-Token).
            is_machine = (
                path.startswith('/api/dicomweb') or path.startswith('/api/v2/dicomweb')
                or path.startswith('/api/fhir') or path.startswith('/api/v2/fhir')
            )
            if path not in self._PUBLIC_PATHS and not is_machine:
                # Double-submit cookie pattern: the client reads the
                # csrf_token cookie (non-HttpOnly) and echoes it in the
                # X-CSRF-Token header. The middleware verifies they match.
                # Fallback to '1' for backwards compat with clients that
                # haven't updated yet.
                cookie_token = request.cookies.get('csrf_token', '1')
                header_token = request.headers.get('X-CSRF-Token', '')
                if header_token != cookie_token:
                    from api.response import forbidden
                    return forbidden('CSRF token missing or invalid')
        response = await call_next(request)
        set_cookie = response.headers.get('set-cookie')
        if set_cookie and 'SameSite' not in set_cookie:
            response.headers['set-cookie'] = set_cookie.replace('; path=', '; SameSite=Strict; path=')
        return response


async def http_exception(request, exc):
    # HTTPException.detail is optional — guard code raises bare
    # HTTPException(403) — so an empty detail must fall back to a generic
    # description instead of emitting an envelope with an empty error string.
    # starlette >= 1.x also defaults detail to the status phrase, which is
    # equally generic and safe to replace.
    detail = getattr(exc, 'detail', None)
    if not detail or detail == HTTPStatus(exc.status_code).phrase:
        detail = 'Request failed'
    resp = server_error(str(detail), status_code=exc.status_code)
    return apply_cors_headers(request, resp)


async def server_error_handler(request, exc):
    log.exception('Unhandled server error: %s %s', request.method, request.url.path)
    resp = server_error('Internal server error', status_code=500)
    return apply_cors_headers(request, resp)


@asynccontextmanager
async def lifespan(app):
    try:
        assert_production_secret()
    except ConfigurationError:
        log.critical('SECURITY: Using default secret. Set SECRET env var or config.local.yaml secret.')
        raise
    lifecycle.set_app(app)
    ws_module.set_app(app)
    telemetry_module.set_app(app)
    import db
    db.register_tables()
    from es import es as _es_mod
    from storage.storage import Storage as _Storage
    from db.files import set_es_indexer as _set_files_es, set_storage_provider as _set_files_storage
    from db.replica import set_storage_provider as _set_replica_storage, set_storage_default_config
    _set_files_es(lambda data, delete=False, reset=False, tenant_slug='': (
        _es_mod.delete(data, tenant_slug) if delete else
        _es_mod.reset_index() if reset else
        _es_mod.index_file(data, tenant_slug)
    ))
    _set_files_storage(lambda replica: _Storage.get(replica))
    _set_replica_storage(lambda replica: _Storage.get(replica))
    set_storage_default_config(lambda type_: _Storage.default_config_by_type(type_))
    registry = ServiceRegistry()
    app.state.services = registry
    app.state.lifecycle = lifecycle.LifecycleState()
    app.state.ws_state = ws_module.WSState()
    app.state.auth_state = auth_module.AuthState()
    app.state.telemetry_state = telemetry_module.TelemetryState()
    await lifecycle.setup(services=registry)
    await _register_services(registry)
    # Durable maintenance flag: load once at startup so the write-gate mirror
    # survives restarts without a per-request DB hit.
    await admin_module.load_maintenance_state()
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
        Middleware(DicomWebLogMiddleware),
        Middleware(AuthenticationMiddleware, backend=TokenAuth(), on_error=TokenAuth.on_auth_error),
        Middleware(TenantMiddleware),
        Middleware(FhirAuditMiddleware),
        Middleware(TrustedHostMiddleware, allowed_hosts=config.get('allowed_hosts', 'localhost,127.0.0.1').split(',')),
        Middleware(RequestIDMiddleware),
        Middleware(CORSMiddleware, allow_origins=config.get('cors_origins', 'http://localhost:5173').split(','), allow_methods=['OPTIONS', 'GET', 'POST', 'PUT', 'DELETE'], allow_headers=['Origin', 'Accept', 'X-Auth-Pacs', 'Content-Type', 'X-Requested-With', 'X-API-Key', 'X-CSRF-Token', 'X-Tenant-ID'], allow_credentials=True),
        Middleware(SecurityHeadersMiddleware),
        Middleware(CSRFMiddleware),
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
