"""App-level rate limiting for the RIS surface (D5 / S1-04).

Reuses the login limiter's primitives (TokenBucket / RedisTokenBucket)
instead of forking them: an operator who configures Redis gets sliding-
window buckets shared across processes; without Redis it degrades to the
in-memory bucket per worker. Only the /api/v2/ris/* prefix is governed;
the kiosk self-check-in path keeps its own (tighter) budget so a busy
lobby cannot be starved by normal clinic traffic, and vice-versa.
"""
import time

from starlette.responses import JSONResponse

from api.ratelimit import RedisTokenBucket, TokenBucket
from config import config
from log import get_logger

log = get_logger(__name__)

RIS_PREFIX = '/api/v2/ris/'
KIOSK_PREFIX = '/api/v2/ris/checkin/'


class RisRateLimitMiddleware:
    """Starlette middleware enforcing per-tenant, per-IP budgets on RIS.

    key_prefix lets tests isolate their Redis keys; default 'ris'.
    """

    def __init__(self, app, key_prefix='ris'):
        self.app = app
        self.key_prefix = key_prefix
        self._buckets = {}
        self._kiosk_buckets = {}

    def _budget(self, kiosk=False):
        key = 'ris_rate_limit_kiosk_per_minute' if kiosk \
            else 'ris_rate_limit_per_minute'
        try:
            return max(1, int(config.get(key, '120')))
        except (TypeError, ValueError):
            return 120

    def _bucket(self, key, kiosk=False):
        cache = self._kiosk_buckets if kiosk else self._buckets
        if key not in cache:
            budget = self._budget(kiosk=kiosk)
            cache[key] = RedisTokenBucket(
                max_attempts=budget,
                window_seconds=60,
                lockout_attempts=0,
                lockout_seconds=0,
                key_prefix=f'{self.key_prefix}:{key}',
            )
        return cache[key]

    async def _limited(self, request, bucket):
        ip = request.client.host if request.client else 'unknown'
        try:
            tenant = getattr(request.user, 'tenant', None) or 'anonymous'
        except AssertionError:
            # AuthenticationMiddleware not installed (tests / bare mount):
            # treat as anonymous, still rate-limited per IP.
            tenant = 'anonymous'
        key = f'{tenant}:{ip}'
        ok, _ = await bucket.check(key)
        if ok:
            await bucket.record(key)
            return False
        return True

    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http':
            await self.app(scope, receive, send)
            return
        request = None
        from starlette.requests import Request
        request = Request(scope, receive)

        path = request.url.path
        if not path.startswith(RIS_PREFIX):
            await self.app(scope, receive, send)
            return

        if path.startswith(KIOSK_PREFIX):
            bucket = self._bucket('kiosk', kiosk=True)
        else:
            bucket = self._bucket('ris')

        if await self._limited(request, bucket):
            response = JSONResponse(
                {'detail': 'Rate limit exceeded'},
                status_code=429,
                headers={'Retry-After': '60'},
            )
            await response(scope, receive, send)
            return
        await self.app(scope, receive, send)
