import pytest
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.responses import JSONResponse
from starlette.routing import Route
from starlette.testclient import TestClient

from services.interfaces import ServiceRegistry, MetadataService, StorageService


async def _health_endpoint(request):
    svc = request.state.services
    meta = svc.get_or_none(MetadataService)
    storage = svc.get_or_none(StorageService)
    return JSONResponse({
        'metadata_available': meta is not None,
        'storage_available': storage is not None,
    })


async def _registry_info(request):
    svc = request.state.services
    try:
        svc.get(MetadataService)
        meta_ok = True
    except KeyError:
        meta_ok = False
    return JSONResponse({'metadata_accessible': meta_ok})


@pytest.fixture
def registry():
    return ServiceRegistry()


@pytest.fixture
def app(registry):
    from api.service_middleware import ServiceMiddleware
    app = Starlette(
        routes=[
            Route('/api/health-svc', endpoint=_health_endpoint),
            Route('/api/registry-check', endpoint=_registry_info),
        ],
        middleware=[
            Middleware(ServiceMiddleware),
        ],
    )
    app.state.services = registry
    return app


@pytest.fixture
def client(app):
    return TestClient(app)


class TestServiceMiddleware:
    def test_services_available_on_request_state(self, client, registry):
        resp = client.get('/api/health-svc')
        assert resp.status_code == 200
        data = resp.json()
        assert 'metadata_available' in data
        assert 'storage_available' in data

    def test_services_returns_none_for_unregistered(self, client, registry):
        resp = client.get('/api/health-svc')
        data = resp.json()
        assert data['metadata_available'] is False
        assert data['storage_available'] is False

    def test_registered_service_is_accessible(self, client, registry):
        class FakeMeta:
            async def get_patient(self, pid):
                return {'id': pid}
            async def get_study(self, sid):
                return {'id': sid}
            async def get_series(self, sid):
                return {'id': sid}
            async def add_file(self, fd):
                return {'id': 'f1'}
            async def get_file(self, fid):
                return {'id': fid}
            async def search_studies(self, q):
                return {'data': [], 'total': 0}

        registry.register(MetadataService, FakeMeta())
        resp = client.get('/api/registry-check')
        assert resp.status_code == 200
        assert resp.json()['metadata_accessible'] is True

    def test_missing_service_raises_keyerror(self, client, registry):
        resp = client.get('/api/registry-check')
        assert resp.status_code == 200
        assert resp.json()['metadata_accessible'] is False

    def test_middleware_does_not_break_unmatched_routes(self, client):
        resp = client.get('/not-found')
        assert resp.status_code in (404,)