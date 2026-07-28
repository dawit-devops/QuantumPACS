import pytest
from starlette.routing import Route, Mount
from starlette.testclient import TestClient

from api.routes import routes


class TestAPIVersioning:
    def test_v1_routes_exist(self):
        paths = _collect_paths(routes)
        assert any(p.endswith('/login') for p in paths)
        assert any('files' in p for p in paths)
        assert any('patients' in p for p in paths)

    def test_v2_aliases_for_api_routes(self):
        paths = _collect_paths(routes)
        v1_paths = {p for p in paths if p.startswith('/api/')}
        v2_paths = {p for p in paths if p.startswith('/api/v2/')}
        assert len(v1_paths) > 0
        assert len(v2_paths) > 0

    def test_v2_has_dashboard_metrics(self):
        paths = _collect_paths(routes)
        assert any('/api/v2/dashboard/metrics' == p for p in paths)

    def test_v2_has_health(self):
        paths = _collect_paths(routes)
        assert any('/api/v2/health' == p for p in paths)

    def test_v2_has_metrics(self):
        paths = _collect_paths(routes)
        assert any('/api/v2/metrics' == p for p in paths)

    def test_v2_has_oauth_aliases(self):
        paths = _collect_paths(routes)
        assert any(p.endswith('/api/v2/oauth/login') for p in paths)
        assert any(p.endswith('/api/v2/oauth/callback') for p in paths)

    def test_v2_has_dicomweb_aliases(self):
        paths = _collect_paths(routes)
        assert any('/api/v2/dicomweb/studies' == p for p in paths)

    def test_v2_has_fhir_aliases(self):
        paths = _collect_paths(routes)
        assert any('/api/v2/fhir/metadata' == p for p in paths)
        assert any('/api/v2/fhir/Patient' == p for p in paths)

    def test_health_endpoint_responds_on_v2(self):
        from api.telemetry import health_endpoint
        from starlette.applications import Starlette
        from starlette.routing import Route, Mount, Router
        routes = [Mount('/api', app=Router([Route('/v2/health', endpoint=health_endpoint)]))]
        app = Starlette(routes=routes)
        client = TestClient(app, raise_server_exceptions=False)
        response = client.get('/api/v2/health')
        assert response.status_code in (200, 503)

    def test_health_endpoint_responds_on_v1(self):
        from api.telemetry import health_endpoint
        from starlette.applications import Starlette
        from starlette.routing import Route, Mount, Router
        routes = [Mount('/api', app=Router([Route('/health', endpoint=health_endpoint)]))]
        app = Starlette(routes=routes)
        client = TestClient(app, raise_server_exceptions=False)
        response = client.get('/api/health')
        assert response.status_code in (200, 503)


def _collect_paths(routes_list, prefix=''):
    paths = []
    for r in routes_list:
        if isinstance(r, Mount):
            sub = _collect_paths(r.routes, prefix + r.path)
            paths.extend(sub)
        elif isinstance(r, Route):
            paths.append(prefix + r.path)
    return paths
