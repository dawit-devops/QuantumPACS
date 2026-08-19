"""F-01 — worklist per_page clamping to prevent bulk PHI dump.

A user with WORKLIST_READ can request per_page=999999999 and dump the
entire tenant's PHI schedule in one call (CWE-770/CWE-200). Every sibling
endpoint clamps (frontdesk: 200, ris_orders: 100) — worklist must too.
"""
from unittest.mock import AsyncMock, patch

from starlette.applications import Starlette
from starlette.exceptions import HTTPException
from starlette.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.routing import Route
from starlette.testclient import TestClient

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


def _worklist_app(permissions=None):
    from api.worklist import WorklistHandler
    return Starlette(
        routes=[
            Route('/worklist', endpoint=WorklistHandler),
        ],
        middleware=[Middleware(_FakeAuth, user=User({'id': 1, 'permissions': permissions or []}))],
        exception_handlers={
            HTTPException: _http_exception,
            _ValidationException: validation_exception_handler,
        },
    )


class TestWorklistPaginationClamp:
    """F-01 — per_page must be clamped to prevent bulk PHI dump."""

    def test_per_page_capped_at_200(self):
        """A per_page of 999999 must be silently capped to 200."""
        with patch('api.worklist.get_conn') as conn_ctx, \
             patch('api.worklist.Worklist') as wl_cls:
            conn_ctx.return_value.__aenter__.return_value = AsyncMock()
            wl = AsyncMock()
            wl.search = AsyncMock(return_value=(
                [{'id': f'w{i}'} for i in range(200)], 200))
            wl_cls.return_value = wl
            client = TestClient(_worklist_app(['WORKLIST_READ']))
            resp = client.get('/worklist?per_page=999999')
            assert resp.status_code == 200
            data = resp.json()
            # The response must report the clamped value
            assert data['per_page'] <= 200
            # The DB query must have received the clamped value
            called_per_page = wl.search.call_args.kwargs.get('per_page') or \
                              wl.search.call_args[1].get('per_page')
            assert called_per_page <= 200

    def test_per_page_rejects_non_numeric(self):
        """Non-numeric per_page must be a validation error, not a 500."""
        client = TestClient(_worklist_app(['WORKLIST_READ']))
        resp = client.get('/worklist?per_page=abc')
        assert resp.status_code in (400, 422)

    def test_per_page_negative_is_rejected(self):
        """Negative per_page must be clamped to 1 (not negative)."""
        with patch('api.worklist.get_conn') as conn_ctx, \
             patch('api.worklist.Worklist') as wl_cls:
            conn_ctx.return_value.__aenter__.return_value = AsyncMock()
            wl = AsyncMock()
            wl.search = AsyncMock(return_value=([], 0))
            wl_cls.return_value = wl
            client = TestClient(_worklist_app(['WORKLIST_READ']))
            resp = client.get('/worklist?per_page=-1')
            assert resp.status_code == 200
            assert resp.json()['per_page'] >= 1

    def test_per_page_defaults_to_20(self):
        """Missing per_page defaults to 20 (not unbounded)."""
        with patch('api.worklist.get_conn') as conn_ctx, \
             patch('api.worklist.Worklist') as wl_cls:
            conn_ctx.return_value.__aenter__.return_value = AsyncMock()
            wl = AsyncMock()
            wl.search = AsyncMock(return_value=([], 0))
            wl_cls.return_value = wl
            client = TestClient(_worklist_app(['WORKLIST_READ']))
            resp = client.get('/worklist')
            assert resp.status_code == 200
            assert resp.json()['per_page'] == 20
