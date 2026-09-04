"""Per-user preference documents (migration 102) — §3 configurable-widget
substrate.

Self-service exactly like /account/profile: authentication identifies the
actor, no permission grant — every authenticated user may manage their OWN
preference document (dashboard_layout is the first consumer). Top-level keys
merge, so independent features never clobber each other's section.
"""
import json
from unittest.mock import AsyncMock, MagicMock, patch

from starlette.applications import Starlette
from starlette.exceptions import HTTPException
from starlette.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.routing import Route
import pytest
from starlette.testclient import TestClient

from api.account import PreferencesHandler
from api.auth import User
from api.validate import validation_exception_handler, _ValidationException


class _FakeAuth(BaseHTTPMiddleware):
    def __init__(self, app, user=None):
        super().__init__(app)
        self._user = user

    async def dispatch(self, request, call_next):
        request.scope['user'] = self._user
        request.scope['auth'] = None
        return await call_next(request)


def _http_exception(request, exc):
    from starlette.responses import JSONResponse

    return JSONResponse({'error': exc.detail}, status_code=exc.status_code)


def _make_app():
    return Starlette(
        routes=[Route('/account/preferences', endpoint=PreferencesHandler)],
        middleware=[Middleware(_FakeAuth, user=User({'id': 7}))],
        exception_handlers={
            HTTPException: _http_exception,
            _ValidationException: validation_exception_handler,
        },
    )


def _prefs_ctx(row=None, merged=None):
    mock_conn = MagicMock()
    mock_users = MagicMock()
    mock_users.get_preferences = AsyncMock(return_value=row)
    mock_users.merge_preferences = AsyncMock(return_value=merged)
    mock_audit = MagicMock()
    mock_audit.log_event = AsyncMock()
    ctx = (
        patch('api.account.get_conn', return_value=MagicMock(
            __aenter__=AsyncMock(return_value=mock_conn),
            __aexit__=AsyncMock(return_value=None),
        )),
        patch('api.account.Users', return_value=mock_users),
        patch('api.account.AuditLog', return_value=mock_audit),
        mock_users,
        mock_audit,
    )
    return ctx, mock_users


class TestPreferencesEndpoint:
    def test_get_returns_stored_document(self):
        (patches, _) = _prefs_ctx(row={'dashboard_layout': {'order': ['a']}})
        with patches[0], patches[1], patches[2]:
            client = TestClient(_make_app())
            resp = client.get('/account/preferences')
        assert resp.status_code == 200
        assert resp.json()['data']['dashboard_layout'] == {'order': ['a']}

    def test_get_defaults_to_empty_document(self):
        (patches, _) = _prefs_ctx(row={})
        with patches[0], patches[1], patches[2]:
            client = TestClient(_make_app())
            resp = client.get('/account/preferences')
        assert resp.status_code == 200
        assert resp.json()['data'] == {}

    def test_put_merges_top_level_keys(self):
        merged = {'theme': 'dark', 'dashboard_layout': {'cols': 3}}
        (patches, users) = _prefs_ctx(merged=merged)
        with patches[0], patches[1], patches[2]:
            client = TestClient(_make_app())
            resp = client.put(
                '/account/preferences',
                json={'dashboard_layout': {'cols': 3}},
            )
        assert resp.status_code == 200
        assert resp.json()['data'] == merged
        # Only the posted section reaches the store — merge keeps siblings.
        patch_doc = users.merge_preferences.await_args.args[1]
        assert list(patch_doc.keys()) == ['dashboard_layout']

    def test_put_rejects_oversized_documents(self):
        (patches, users) = _prefs_ctx(merged={})
        with patches[0], patches[1], patches[2]:
            client = TestClient(_make_app())
            resp = client.put(
                '/account/preferences',
                json={'blob': 'x' * 70_000},
            )
        # House validation_error() is a 400 (same as the checklist gate).
        assert resp.status_code == 400
        users.merge_preferences.assert_not_awaited()


class TestPreferencesDbLayer:
    @pytest.mark.asyncio
    async def test_merge_sql_is_top_level_jsonb_concat(self):
        from db.users import Users

        u = Users(MagicMock())
        u.fetchrow = AsyncMock(return_value={'preferences': '{}'})
        await u.merge_preferences(7, {'dashboard_layout': {'cols': 3}})
        sql = u.fetchrow.await_args.args[0]
        # Top-level concat: sibling sections of the document survive.
        assert "preferences || $2::jsonb" in sql
        assert 'WHERE id = $1' in sql
        params = u.fetchrow.await_args.args[1:]
        assert params[0] == 7
        assert json.loads(params[1]) == {'dashboard_layout': {'cols': 3}}

    @pytest.mark.asyncio
    async def test_get_preferences_decodes_jsonb_and_defaults_empty(self):
        from db.users import Users

        u = Users(MagicMock())
        u.fetchone = AsyncMock(return_value={'preferences': '{"k": 1}'})
        assert await u.get_preferences(7) == {'k': 1}
        # NULL column → empty document, missing row → None (404 upstream).
        u.fetchone = AsyncMock(return_value={'preferences': None})
        assert await u.get_preferences(7) == {}
        u.fetchone = AsyncMock(return_value=None)
        assert await u.get_preferences(7) is None


class TestMigration102UserPreferences:
    def _load(self):
        import importlib.util
        from pathlib import Path

        migration = (
            Path(__file__).resolve().parents[1]
            / 'migrations' / 'versions' / '102_user_preferences.py'
        )
        spec = importlib.util.spec_from_file_location('mig102', migration)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    def test_revision_chain_follows_101(self):
        mod = self._load()
        assert mod.revision == '102'
        assert mod.down_revision == '101'

    def test_upgrade_adds_column_and_keeps_rollback_additive(self):
        """Rollback stays a documented no-op like migration 100's additive
        columns — dropping would destroy saved layouts."""
        mod = self._load()
        executed = []

        class _FakeOp:
            def execute(self, stmt):
                executed.append(str(stmt))

        with pytest.MonkeyPatch.context() as mp:
            mp.setattr(mod, 'op', _FakeOp())
            mod.upgrade()
            before = len(executed)
            mod.downgrade()
        sql = '\n'.join(executed[:before])
        assert 'ADD COLUMN IF NOT EXISTS preferences' in sql
        assert 'JSONB' in sql
        assert len(executed) == before  # downgrade emits nothing
