from unittest.mock import AsyncMock, MagicMock, patch

from starlette.applications import Starlette
from starlette.exceptions import HTTPException
from starlette.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.routing import Route
from starlette.testclient import TestClient

from api.auth import User
from api.replicas import ReplicasHandlers, ReplicaHandlers
from api.validate import validation_exception_handler, _ValidationException


class _FakeAuth(BaseHTTPMiddleware):
    def __init__(self, app, user=None):
        super().__init__(app)
        self._user = user or User({'id': 1, 'permissions': ['REPLICA_WRITE', 'REPLICA_READ', 'REPLICA_DELETE']})

    async def dispatch(self, request, call_next):
        request.scope['user'] = self._user
        request.scope['auth'] = None
        return await call_next(request)


def _mock_conn():
    conn = MagicMock()
    conn.fetch = AsyncMock(return_value=[])
    conn.fetchrow = AsyncMock(return_value=None)
    conn.fetchval = AsyncMock(return_value=0)
    conn.execute = AsyncMock(return_value=None)
    return conn


def _patch_get_conn(module, mock_conn):
    return patch(f'{module}.get_conn', return_value=MagicMock(
        __aenter__=AsyncMock(return_value=mock_conn),
        __aexit__=AsyncMock(return_value=None),
    ))


def _http_exception(request, exc):
    from starlette.responses import JSONResponse
    return JSONResponse({'error': exc.detail}, status_code=exc.status_code)


def _make_app(routes, user=None):
    return Starlette(
        routes=routes,
        middleware=[Middleware(_FakeAuth, user=user)],
        exception_handlers={
            HTTPException: _http_exception,
            _ValidationException: validation_exception_handler,
        },
    )


class TestReplicasList:
    def _make_app(self, user=None):
        return _make_app([Route('/replicas', endpoint=ReplicasHandlers)], user)

    def test_list(self):
        mock_conn = _mock_conn()
        mock_conn.fetch = AsyncMock(side_effect=[
            [{'id': 1, 'type': 'local', 'location': '/data', 'delay': 0,
              'master': True, 'status': 'ok', 'total': 100, 'meta': None}],
            [],
        ])
        with _patch_get_conn('api.replicas', mock_conn):
            client = TestClient(self._make_app())
            resp = client.get('/replicas')
        assert resp.status_code == 200
        assert len(resp.json()['data']) == 1

    def test_missing_permission(self):
        user = User({'id': 1, 'permissions': []})
        client = TestClient(self._make_app(user=user))
        resp = client.get('/replicas')
        assert resp.status_code == 403

    def test_create(self):
        mock_conn = _mock_conn()
        mock_conn.transaction = MagicMock()
        mock_conn.transaction.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_conn.transaction.return_value.__aexit__ = AsyncMock(return_value=None)
        mock_conn.fetchval = AsyncMock(side_effect=[1, None])
        with _patch_get_conn('api.replicas', mock_conn), \
             patch('api.replicas.ReplicaFiles.add_replica', new_callable=AsyncMock):
            client = TestClient(self._make_app())
            resp = client.post('/replicas', json={'type': 'local'})
        assert resp.status_code == 201
        assert resp.json()['id'] == 1

    def test_create_missing_type(self):
        with _patch_get_conn('api.replicas', _mock_conn()):
            client = TestClient(self._make_app())
            resp = client.post('/replicas', json={})
        assert resp.status_code == 422

    def test_create_invalid_type(self):
        with _patch_get_conn('api.replicas', _mock_conn()):
            client = TestClient(self._make_app())
            resp = client.post('/replicas', json={'type': 'invalid'})
        assert resp.status_code == 422


class TestReplicaSingle:
    def _make_app(self, user=None):
        return _make_app([Route('/replicas/{id}', endpoint=ReplicaHandlers)], user)

    def test_update_master(self):
        mock_conn = _mock_conn()
        with _patch_get_conn('api.replicas', mock_conn), \
             patch('api.replicas.Replica.set_master', new_callable=AsyncMock):
            client = TestClient(self._make_app())
            resp = client.post('/replicas/1', json={'master': True})
        assert resp.status_code == 200

    def test_update_delay(self):
        mock_conn = _mock_conn()
        with _patch_get_conn('api.replicas', mock_conn), \
             patch('api.replicas.Replica.update_delay', new_callable=AsyncMock):
            client = TestClient(self._make_app())
            resp = client.post('/replicas/1', json={'delay': 60})
        assert resp.status_code == 200

    def test_update_both(self):
        mock_conn = _mock_conn()
        with _patch_get_conn('api.replicas', mock_conn), \
             patch('api.replicas.Replica.set_master', new_callable=AsyncMock), \
             patch('api.replicas.Replica.update_delay', new_callable=AsyncMock):
            client = TestClient(self._make_app())
            resp = client.post('/replicas/1', json={'master': True, 'delay': 30})
        assert resp.status_code == 200

    def test_delete(self):
        mock_conn = _mock_conn()
        with _patch_get_conn('api.replicas', mock_conn), \
             patch('api.replicas.Replica.delete', new_callable=AsyncMock):
            client = TestClient(self._make_app())
            resp = client.delete('/replicas/1')
        assert resp.status_code == 200

    def test_delete_missing_permission(self):
        user = User({'id': 1, 'permissions': ['REPLICA_READ']})
        client = TestClient(self._make_app(user=user))
        resp = client.delete('/replicas/1')
        assert resp.status_code == 403
