"""D5 (GAP_AUDIT_TDD_PIPELINE.md): app-level rate limiting for RIS surface.

Tests that the RisRateLimitMiddleware rejects bursts beyond budget on
RIS routes, leaves non-RIS routes untouched, and exempts the kiosk.
Existing login-ratelimit behaviour is unchanged.
"""
import uuid
import pytest
from unittest.mock import patch, AsyncMock
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.routing import Route
from starlette.testclient import TestClient
from starlette.responses import JSONResponse

from api.ratelimit_middleware import RisRateLimitMiddleware


async def _ok(request):
    return JSONResponse({'ok': True})


def _make_app(extra_middleware=None):
    """Test app with the RIS rate-limit middleware and a dummy RIS route.

    key_prefix is unique per call so real-Redis keys never bleed across
    tests (this environment runs a live Redis on localhost)."
    """
    prefix = f'rl-{uuid.uuid4().hex[:8]}'
    mw = [Middleware(RisRateLimitMiddleware, key_prefix=prefix)]
    if extra_middleware:
        mw.extend(extra_middleware)
    return Starlette(
        routes=[
            Route('/api/v2/ris/patients', endpoint=_ok),
            Route('/api/v2/ris/checkin/abc123', endpoint=_ok),
            Route('/api/v2/dicom/studies', endpoint=_ok),
            Route('/health', endpoint=_ok),
        ],
        middleware=mw,
    )


class TestRisRateLimitMiddleware:
    def test_burst_beyond_budget_returns_429(self):
        app = _make_app()
        client = TestClient(app)
        # Default budget is 3/min for testing (overridden in some tests).
        with patch.dict('api.ratelimit_middleware.config',
                        {'ris_rate_limit_per_minute': '3',
                         'ris_rate_limit_kiosk_per_minute': '5'},
                        clear=False):
            for _ in range(3):
                resp = client.get('/api/v2/ris/patients')
                assert resp.status_code == 200, 'burst within budget'
            # 4th request exceeds the 3/min budget
            resp = client.get('/api/v2/ris/patients')
            assert resp.status_code == 429
            assert 'Retry-After' in resp.headers
            assert resp.json()['detail'] == 'Rate limit exceeded'

    def test_non_ris_route_untouched(self):
        app = _make_app()
        client = TestClient(app)
        with patch.dict('api.ratelimit_middleware.config',
                        {'ris_rate_limit_per_minute': '1',
                         'ris_rate_limit_kiosk_per_minute': '5'},
                        clear=False):
            # First RIS request passes (budget=1, count=0 < 1)
            resp = client.get('/api/v2/ris/patients')
            assert resp.status_code == 200
            # Second exceeds the budget
            resp = client.get('/api/v2/ris/patients')
            assert resp.status_code == 429
            # Non-RIS route is not rate-limited by this middleware
            resp = client.get('/api/v2/dicom/studies')
            assert resp.status_code == 200
            resp = client.get('/health')
            assert resp.status_code == 200

    def test_kiosk_exempt_from_standard_budget(self):
        app = _make_app()
        client = TestClient(app)
        with patch.dict('api.ratelimit_middleware.config',
                        {'ris_rate_limit_per_minute': '1',
                         'ris_rate_limit_kiosk_per_minute': '5'},
                        clear=False):
            # Kiosk uses its own budget — 4 requests should all pass
            for _ in range(4):
                resp = client.get('/api/v2/ris/checkin/abc123')
                assert resp.status_code == 200, 'kiosk has own budget'

    def test_429_retry_after_header_present(self):
        app = _make_app()
        client = TestClient(app)
        with patch.dict('api.ratelimit_middleware.config',
                        {'ris_rate_limit_per_minute': '1',
                         'ris_rate_limit_kiosk_per_minute': '5'},
                        clear=False):
            client.get('/api/v2/ris/patients')
            resp = client.get('/api/v2/ris/patients')
            assert resp.status_code == 429
            retry = resp.headers.get('Retry-After')
            assert retry is not None
            assert int(retry) > 0