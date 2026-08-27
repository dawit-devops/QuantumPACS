"""RIS Study Bookmarks API (R-08) tests.

Bookmarks/collections: PATIENT_READ lists, PATIENT_WRITE creates +
deletes. Tests pin permission gates, user scoping, create serialization,
collection filtering, and delete.
"""

import pytest

from unittest.mock import patch

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
    return User({'id': 50, 'permissions': list(perms), 'tenant': tenant})


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


def _handlers():
    from api.bookmarks import (
        BookmarkCollectionsHandler, StudyBookmarksHandler,
        StudyBookmarkDeleteHandler,
    )
    return [
        ('/ris/bookmark-collections', BookmarkCollectionsHandler,
         ['GET', 'POST']),
        ('/ris/bookmarks', StudyBookmarksHandler, ['GET', 'POST']),
        ('/ris/bookmarks/{id}', StudyBookmarkDeleteHandler, ['DELETE']),
    ]


class TestBookmarkDb:
    @pytest.mark.asyncio
    async def test_create_collection_returns_row(self, conn):
        from db.ris_bookmarks import BookmarkCollections
        conn.set_fetchrow({'id': 'bc-1', 'user_id': '50',
                           'name': 'Teaching Cases'})
        row = await BookmarkCollections(conn).create(
            user_id='50', name='Teaching Cases', description='', by='50',
            tenant_id='default',
        )
        assert row['id'] == 'bc-1'
        assert any('INSERT INTO bookmark_collections' in c[1]
                   for c in conn.calls)

    @pytest.mark.asyncio
    async def test_create_bookmark_returns_row(self, conn):
        from db.ris_bookmarks import StudyBookmarks
        conn.set_fetchrow({'id': 'bm-1', 'user_id': '50',
                           'study_uid': '1.2.3.4', 'collection_id': 'bc-1'})
        row = await StudyBookmarks(conn).create(
            user_id='50', study_uid='1.2.3.4', study_desc='Chest CT',
            collection_id='bc-1', notes='', tenant_id='default',
        )
        assert row['id'] == 'bm-1'
        assert any('INSERT INTO study_bookmarks' in c[1] for c in conn.calls)

    @pytest.mark.asyncio
    async def test_list_bookmarks_scoped_to_user(self, conn):
        from db.ris_bookmarks import StudyBookmarks
        conn.set_fetch([{'id': 'bm-1', 'user_id': '50'}])
        rows = await StudyBookmarks(conn).list('default', user_id='50')
        assert rows[0]['id'] == 'bm-1'
        sql = conn.calls[-1][1]
        assert 'user_id' in sql

    @pytest.mark.asyncio
    async def test_list_bookmarks_by_collection(self, conn):
        from db.ris_bookmarks import StudyBookmarks
        conn.set_fetch([{'id': 'bm-1', 'collection_id': 'bc-1'}])
        rows = await StudyBookmarks(conn).list(
            'default', user_id='50', collection_id='bc-1')
        assert rows[0]['id'] == 'bm-1'
        sql = conn.calls[-1][1]
        assert 'collection_id' in sql


class TestBookmarkApi:
    def test_get_collections_requires_patient_read(self, conn):
        app = _make_app(_user(), _handlers())
        client = TestClient(app)
        resp = client.get('/ris/bookmark-collections')
        assert resp.status_code == 403

    def test_post_collection_requires_patient_write(self, conn):
        app = _make_app(_user(Permission.PATIENT_READ), _handlers())
        client = TestClient(app)
        resp = client.post('/ris/bookmark-collections', json={'name': 'X'})
        assert resp.status_code == 403

    def test_post_collection_creates(self, conn):
        conn.set_fetchrow({'id': 'bc-1', 'user_id': '50', 'name': 'Teaching'})
        app = _make_app(_user(Permission.PATIENT_WRITE), _handlers())
        client = TestClient(app)
        with patch('api.bookmarks.get_conn', return_value=conn):
            resp = client.post('/ris/bookmark-collections',
                               json={'name': 'Teaching'})
        assert resp.status_code == 201
        assert resp.json()['data']['name'] == 'Teaching'

    def test_post_bookmark_creates(self, conn):
        conn.set_fetchrow({'id': 'bm-1', 'user_id': '50',
                           'study_uid': '1.2.3.4'})
        app = _make_app(_user(Permission.PATIENT_WRITE), _handlers())
        client = TestClient(app)
        with patch('api.bookmarks.get_conn', return_value=conn):
            resp = client.post('/ris/bookmarks', json={
                'study_uid': '1.2.3.4', 'study_desc': 'Chest CT',
                'notes': 'Rare finding',
            })
        assert resp.status_code == 201
        assert resp.json()['data']['study_uid'] == '1.2.3.4'

    def test_delete_bookmark(self, conn):
        conn.set_fetchrow({'id': 'bm-1', 'user_id': '50',
                           'study_uid': '1.2.3.4'})
        app = _make_app(_user(Permission.PATIENT_WRITE), _handlers())
        client = TestClient(app)
        with patch('api.bookmarks.get_conn', return_value=conn):
            resp = client.delete('/ris/bookmarks/bm-1')
        assert resp.status_code == 200
        assert resp.json()['status'] == 'deleted'
        assert any('DELETE FROM study_bookmarks' in c[1] for c in conn.calls)

    def test_delete_missing_is_404(self, conn):
        conn.set_fetchrow(None)
        app = _make_app(_user(Permission.PATIENT_WRITE), _handlers())
        client = TestClient(app)
        with patch('api.bookmarks.get_conn', return_value=conn):
            resp = client.delete('/ris/bookmarks/nope')
        assert resp.status_code == 404