"""RIS Communication Log API (CS7/CC-04) tests.

Patient-scoped correspondence trail: GET gated by PATIENT_READ, POST
(append-only) gated by ENCOUNTER_WRITE; direction/channel CHECKs enforced
at the schema layer.
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


class TestCommunicationsDb:
    @pytest.mark.asyncio
    async def test_create_returns_row(self, conn):
        from db.communications import Communications
        conn.set_fetchrow({'id': 'cm-1', 'direction': 'outbound'})
        row = await Communications(conn).create(
            patient_id='8675309', direction='outbound', channel='email',
            summary='Sent prep instructions', by='1', tenant_id='default',
        )
        assert row['id'] == 'cm-1'
        assert any('INSERT INTO communications' in c[1] for c in conn.calls)

    @pytest.mark.asyncio
    async def test_list_without_patient_is_empty(self, conn):
        from db.communications import Communications
        rows = await Communications(conn).list('default')
        assert rows == []
        assert conn.calls == []


class TestCommunicationsApi:
    def test_get_requires_patient_read(self, conn):
        from api.communications import CommunicationHandler
        app = _make_app(_user(), [('/ris/communications', CommunicationHandler,
                                   ['GET', 'POST'])])
        client = TestClient(app)
        resp = client.get('/ris/communications', params={'patient_id': '1'})
        assert resp.status_code == 403

    def test_get_requires_patient_id(self, conn):
        from api.communications import CommunicationHandler
        app = _make_app(_user(Permission.PATIENT_READ),
                        [('/ris/communications', CommunicationHandler,
                          ['GET', 'POST'])])
        client = TestClient(app)
        with patch('api.communications.get_conn', return_value=conn):
            resp = client.get('/ris/communications')
        assert resp.status_code in (400, 422)

    def test_post_requires_encounter_write(self, conn):
        from api.communications import CommunicationHandler
        app = _make_app(_user(Permission.PATIENT_READ),
                        [('/ris/communications', CommunicationHandler,
                          ['GET', 'POST'])])
        client = TestClient(app)
        resp = client.post('/ris/communications',
                           json={'patient_id': '1', 'direction': 'outbound',
                                 'summary': 'x'})
        assert resp.status_code == 403

    @patch('db.audit_log.AuditLog.log_event', new=AsyncMock(return_value=None))
    def test_post_logs_communication(self, conn):
        from api.communications import CommunicationHandler
        conn.set_fetchrow({'id': 'cm-1', 'direction': 'inbound'})
        app = _make_app(_user(Permission.ENCOUNTER_WRITE),
                        [('/ris/communications', CommunicationHandler,
                          ['GET', 'POST'])])
        client = TestClient(app)
        with patch('api.communications.get_conn', return_value=conn):
            resp = client.post('/ris/communications',
                               json={'patient_id': '8675309',
                                     'direction': 'inbound',
                                     'channel': 'phone',
                                     'summary': 'Called about results'})
        assert resp.status_code == 201
        assert resp.json()['data']['direction'] == 'inbound'

    def test_post_rejects_bad_direction(self, conn):
        from api.communications import CommunicationHandler
        app = _make_app(_user(Permission.ENCOUNTER_WRITE),
                        [('/ris/communications', CommunicationHandler,
                          ['GET', 'POST'])])
        client = TestClient(app)
        resp = client.post('/ris/communications',
                           json={'patient_id': '1', 'direction': 'sideways',
                                 'summary': 'x'})
        assert resp.status_code in (400, 422)
