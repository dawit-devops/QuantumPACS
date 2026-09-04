"""RIS Encounters API (CS6/CC-03) tests.

Patient-scoped contact log: GET gated by PATIENT_READ, POST gated by
ENCOUNTER_WRITE; type CHECK enforced at the schema layer.
"""

import pytest

from unittest.mock import AsyncMock, patch

from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.routing import Route
from starlette.testclient import TestClient

from api.auth import User
from api.permissions import Permission


class _FakeAuth(BaseHTTPMiddleware):
    def __init__(self, app, user=None):
        super().__init__(app)
        self._user = user or User({'id': 1, 'permissions': []})

    async def dispatch(self, request, call_next):
        request.scope['user'] = self._user
        request.scope['auth'] = None
        return await call_next(request)


def _make_app(user, handlers):
    from starlette.exceptions import HTTPException
    from api.validate import validation_exception_handler, _ValidationException

    def _http_exception(request, exc):
        from starlette.responses import JSONResponse
        return JSONResponse(
            {'error': exc.detail if hasattr(exc, 'detail') else ''},
            status_code=exc.status_code,
        )

    return Starlette(
        routes=[Route(path, endpoint=h, methods=m) for path, h, m in handlers],
        middleware=[Middleware(_FakeAuth, user=user)],
        exception_handlers={
            HTTPException: _http_exception,
            _ValidationException: validation_exception_handler,
        },
    )


def _user(*perms, tenant='default'):
    return User({'id': 1, 'permissions': list(perms), 'tenant': tenant})


class _Conn:
    def __init__(self):
        self.calls = []
        self._fetch = []
        self._fetchrow = None

    def set_fetch(self, rows):
        self._fetch = rows

    def set_fetchrow(self, row):
        self._fetchrow = row

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def execute(self, sql, *args):
        self.calls.append(('execute', sql, args))

    async def fetch(self, sql, *args):
        self.calls.append(('fetch', sql, args))
        return self._fetch

    async def fetchrow(self, sql, *args):
        self.calls.append(('fetchrow', sql, args))
        return self._fetchrow


@pytest.fixture
def conn():
    return _Conn()


class TestEncounterDb:
    @pytest.mark.asyncio
    async def test_create_returns_row(self, conn):
        from db.encounters import Encounters
        conn.set_fetchrow({'id': 'enc-1', 'encounter_type': 'call'})
        row = await Encounters(conn).create(
            patient_id='8675309', encounter_type='call',
            summary='Discussed follow-up', by='1', tenant_id='default',
        )
        assert row['id'] == 'enc-1'
        assert any('INSERT INTO encounters' in c[1] for c in conn.calls)

    @pytest.mark.asyncio
    async def test_list_without_patient_is_empty(self, conn):
        from db.encounters import Encounters
        rows = await Encounters(conn).list('default')
        assert rows == []
        assert conn.calls == []

    @pytest.mark.asyncio
    async def test_list_orders_by_occurred_at(self, conn):
        from db.encounters import Encounters
        conn.set_fetch([{'id': 'enc-1'}])
        rows = await Encounters(conn).list('default', patient_id='1')
        assert rows[0]['id'] == 'enc-1'
        sql = conn.calls[-1][1]
        assert 'ORDER BY occurred_at DESC' in sql


class TestEncounterApi:
    def test_get_requires_patient_read(self, conn):
        from api.encounters import EncounterHandler
        app = _make_app(_user(), [('/ris/encounters', EncounterHandler,
                                   ['GET', 'POST'])])
        client = TestClient(app)
        resp = client.get('/ris/encounters', params={'patient_id': '1'})
        assert resp.status_code == 403

    def test_get_requires_patient_id(self, conn):
        from api.encounters import EncounterHandler
        app = _make_app(_user(Permission.PATIENT_READ),
                        [('/ris/encounters', EncounterHandler,
                          ['GET', 'POST'])])
        client = TestClient(app)
        with patch('api.encounters.get_conn', return_value=conn):
            resp = client.get('/ris/encounters')
        assert resp.status_code in (400, 422)

    def test_post_requires_encounter_write(self, conn):
        from api.encounters import EncounterHandler
        app = _make_app(_user(Permission.PATIENT_READ),
                        [('/ris/encounters', EncounterHandler,
                          ['GET', 'POST'])])
        client = TestClient(app)
        resp = client.post('/ris/encounters',
                           json={'patient_id': '1',
                                 'encounter_type': 'call', 'summary': 'x'})
        assert resp.status_code == 403

    @patch('db.audit_log.AuditLog.log_event', new=AsyncMock(return_value=None))
    def test_post_creates_encounter(self, conn):
        from api.encounters import EncounterHandler
        conn.set_fetchrow({'id': 'enc-1', 'encounter_type': 'call'})
        app = _make_app(_user(Permission.ENCOUNTER_WRITE),
                        [('/ris/encounters', EncounterHandler,
                          ['GET', 'POST'])])
        client = TestClient(app)
        with patch('api.encounters.get_conn', return_value=conn):
            resp = client.post('/ris/encounters',
                               json={'patient_id': '8675309',
                                     'encounter_type': 'call',
                                     'summary': 'Discussed follow-up'})
        assert resp.status_code == 201
        assert resp.json()['data']['encounter_type'] == 'call'

    def test_post_rejects_bad_type(self, conn):
        from api.encounters import EncounterHandler
        app = _make_app(_user(Permission.ENCOUNTER_WRITE),
                        [('/ris/encounters', EncounterHandler,
                          ['GET', 'POST'])])
        client = TestClient(app)
        resp = client.post('/ris/encounters',
                           json={'patient_id': '1',
                                 'encounter_type': 'telepathy',
                                 'summary': 'x'})
        assert resp.status_code in (400, 422)
