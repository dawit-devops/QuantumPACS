from contextlib import contextmanager
from unittest.mock import AsyncMock, patch

from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.routing import Route
from starlette.testclient import TestClient
from starlette.exceptions import HTTPException

from api.auth import User
from api.validate import validation_exception_handler, _ValidationException


def _http_exception(request, exc):
    from starlette.responses import JSONResponse
    return JSONResponse(
        {'error': exc.detail if hasattr(exc, 'detail') else ''},
        status_code=exc.status_code,
    )


class _FakeAuth(BaseHTTPMiddleware):
    def __init__(self, app, user=None):
        super().__init__(app)
        self._user = user or User({'id': 1, 'permissions': []})

    async def dispatch(self, request, call_next):
        request.scope['user'] = self._user
        request.scope['auth'] = None
        return await call_next(request)


def _make_app(user=None):
    from api.reading_presets import ReadingPresetsHandler, ReadingPresetHandler
    return Starlette(
        routes=[
            Route('/reading-presets', endpoint=ReadingPresetsHandler),
            Route('/reading-presets/{id}', endpoint=ReadingPresetHandler),
        ],
        middleware=[Middleware(_FakeAuth, user=user)],
        exception_handlers={
            HTTPException: _http_exception,
            _ValidationException: validation_exception_handler,
        },
    )


RAD = User({'id': 50, 'permissions': ['REPORT_READ', 'REPORT_WRITE']})
READ_ONLY = User({'id': 51, 'permissions': ['REPORT_READ']})
NO_PERMS = User({'id': 52, 'permissions': []})


@contextmanager
def _audit_ok():
    with patch('api.reading_presets.AuditLog') as audit_cls:
        audit_cls.return_value.log_event = AsyncMock()
        yield


@contextmanager
def _conn(fetchrow=None, fetch=None, fetchval=None, execute=None):
    conn = AsyncMock()
    if fetchrow is not None:
        conn.fetchrow = fetchrow
    if fetch is not None:
        conn.fetch = fetch
    if fetchval is not None:
        conn.fetchval = fetchval
    if execute is not None:
        conn.execute = execute
    conn.__aenter__ = AsyncMock(return_value=conn)
    conn.__aexit__ = AsyncMock(return_value=False)
    with patch('api.reading_presets.get_conn', return_value=conn):
        yield conn


def _preset_row(preset_id='p1', preset_type='window_level', modality='CT',
                name='Bone', config=None, is_default=True, user_id=50):
    return {
        'id': preset_id, 'user_id': user_id, 'preset_type': preset_type,
        'modality': modality, 'name': name,
        'config': config or {'window_center': 400, 'window_width': 2000},
        'is_default': is_default, 'created_at': None, 'updated_at': None,
    }


class TestReadingPresetsList:
    def test_requires_report_read(self):
        client = TestClient(_make_app(NO_PERMS))
        assert client.get('/reading-presets').status_code == 403

    def test_lists_my_presets(self):
        client = TestClient(_make_app(RAD))
        async def fake_fetch(q, *a):
            return [_preset_row(), _preset_row(preset_id='p2', preset_type='layout',
                                               name='2x2', config={'rows': 2, 'cols': 2},
                                               is_default=False)]
        with _conn(fetch=fake_fetch):
            resp = client.get('/reading-presets?modality=CT')
        assert resp.status_code == 200
        data = resp.json()['data']
        assert len(data) == 2
        # default sorts first
        assert data[0]['name'] == 'Bone'


class TestReadingPresetsCreate:
    def test_create_requires_report_write(self):
        client = TestClient(_make_app(READ_ONLY))
        resp = client.post('/reading-presets', json={
            'preset_type': 'window_level', 'modality': 'CT', 'name': 'Bone',
            'config': {'window_center': 400, 'window_width': 2000},
        })
        assert resp.status_code == 403

    def test_create_success(self):
        client = TestClient(_make_app(RAD))
        created = _preset_row(name='Bone', is_default=False)
        async def fake_fetch(q, *a):
            return [created]
        with _conn(fetch=fake_fetch), _audit_ok(), \
             patch('api.reading_presets.ReadingPresets') as mock_cls:
            mock = AsyncMock()
            mock.create.return_value = created
            mock.list_for_user.return_value = [created]
            mock_cls.return_value = mock
            resp = client.post('/reading-presets', json={
                'preset_type': 'window_level', 'modality': 'CT', 'name': 'Bone',
                'config': {'window_center': 400, 'window_width': 2000},
            })
        assert resp.status_code == 201
        assert resp.json()['data']['name'] == 'Bone'
        args = mock.create.await_args.args
        assert args[1] == 'window_level'

    def test_create_clears_other_defaults(self):
        client = TestClient(_make_app(RAD))
        created = _preset_row(name='Bone', is_default=True)
        async def fake_fetch(q, *a):
            return [created]
        with _conn(fetch=fake_fetch), _audit_ok(), \
             patch('api.reading_presets.ReadingPresets') as mock_cls:
            mock = AsyncMock()
            mock.create.return_value = created
            mock.list_for_user.return_value = [created]
            mock_cls.return_value = mock
            client.post('/reading-presets', json={
                'preset_type': 'window_level', 'modality': 'CT', 'name': 'Bone',
                'config': {'window_center': 400, 'window_width': 2000},
                'is_default': True,
            })
        # When a new default is set, the handler clears other defaults first.
        assert mock.create.await_args.args[5] is True


class TestReadingPresetUpdate:
    def test_update_requires_report_write(self):
        client = TestClient(_make_app(READ_ONLY))
        assert client.put('/reading-presets/p1', json={'name': 'X'}).status_code == 403

    def test_update_success(self):
        client = TestClient(_make_app(RAD))
        preset = _preset_row()
        updated = _preset_row(name='Soft')
        async def fake_fetchrow(q, *a):
            return preset
        with _conn(fetchrow=fake_fetchrow), _audit_ok(), \
             patch('api.reading_presets.ReadingPresets') as mock_cls:
            mock = AsyncMock()
            mock.get.return_value = preset
            mock.update.return_value = updated
            mock_cls.return_value = mock
            resp = client.put('/reading-presets/p1', json={
                'name': 'Soft', 'config': {'window_center': 40, 'window_width': 400},
            })
        assert resp.status_code == 200
        assert resp.json()['data']['name'] == 'Soft'

    def test_update_rejects_other_users_preset(self):
        client = TestClient(_make_app(RAD))
        async def fake_fetchrow(q, *a):
            return _preset_row(user_id=999)
        with _conn(fetchrow=fake_fetchrow):
            resp = client.put('/reading-presets/p1', json={'name': 'X'})
        assert resp.status_code == 403


class TestReadingPresetDelete:
    def test_delete_success(self):
        client = TestClient(_make_app(RAD))
        async def fake_fetchrow(q, *a):
            return _preset_row()
        with _conn(fetchrow=fake_fetchrow), _audit_ok(), \
             patch('api.reading_presets.ReadingPresets') as mock_cls:
            mock = AsyncMock()
            mock.get.return_value = _preset_row()
            mock_cls.return_value = mock
            resp = client.delete('/reading-presets/p1')
        assert resp.status_code == 200
        assert resp.json()['data']['deleted'] is True

    def test_delete_404(self):
        client = TestClient(_make_app(RAD))
        with _conn(fetchrow=AsyncMock(return_value=None)):
            resp = client.delete('/reading-presets/nope')
        assert resp.status_code == 404
