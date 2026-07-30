"""Token-bucket rate limiter for login endpoint.

Limits to N attempts per IP per window_seconds.
Uses Redis-based sliding window when available, falls back to in-memory TokenBucket.
"""
import time
from collections import defaultdict

from log import get_logger

log = get_logger(__name__)

_redis = None
_redis_available = False

try:
    import redis.asyncio as _aioredis

    def _get_rate_redis():
        global _redis, _redis_available
        if _redis is not None:
            return _redis
        try:
            from config import config as cfg
            host = cfg.get('redis_host', 'localhost')
            port = int(cfg.get('redis_port', '6379'))
            password = cfg.get('redis_password') or None
            _redis = _aioredis.Redis(
                host=host, port=port, password=password, db=3,
                socket_connect_timeout=1,
                socket_timeout=1,
            )
            _redis_available = True
        except Exception:
            _redis_available = False
        return _redis

except ImportError:
    def _get_rate_redis():
        return None


class TokenBucket:
    def __init__(self, max_attempts=50, window_seconds=60, lockout_attempts=100, lockout_seconds=300):
        self.max_attempts = max_attempts
        self.window_seconds = window_seconds
        self.lockout_attempts = lockout_attempts
        self.lockout_seconds = lockout_seconds
        self._attempts = defaultdict(list)
        self._lockouts = {}

    def _prune(self, ip):
        now = time.monotonic()
        cutoff = now - self.window_seconds
        self._attempts[ip] = [t for t in self._attempts[ip] if t > cutoff]

    def _is_locked_out(self, ip):
        lockout_until = self._lockouts.get(ip)
        if lockout_until and time.monotonic() < lockout_until:
            return True
        if lockout_until:
            del self._lockouts[ip]
        return False

    def check(self, ip):
        self._prune(ip)
        if self._is_locked_out(ip):
            return False, 'Too many attempts. Try again in 5 minutes.'
        if len(self._attempts[ip]) >= self.max_attempts:
            return False, 'Too many attempts. Try again later.'
        return True, None

    def record(self, ip, success=False):
        if success:
            self._attempts[ip].clear()
            self._lockouts.pop(ip, None)
            return
        now = time.monotonic()
        self._attempts[ip].append(now)
        if len(self._attempts[ip]) >= self.lockout_attempts:
            self._lockouts[ip] = now + self.lockout_seconds

    async def record_db(self, ip, conn, success=False):
        self.record(ip, success=success)
        try:
            await conn.execute(
                'INSERT INTO login_attempts (ip, endpoint, success) VALUES ($1, $2, $3)',
                ip, 'login', success,
            )
        except Exception as e:
            log.warning('Failed to record login attempt: %s', e)

    def remaining(self, ip):
        self._prune(ip)
        return max(0, self.max_attempts - len(self._attempts[ip]))


class RedisTokenBucket:
    def __init__(self, max_attempts=50, window_seconds=60, lockout_attempts=100, lockout_seconds=300):
        self.max_attempts = max_attempts
        self.window_seconds = window_seconds
        self.lockout_attempts = lockout_attempts
        self.lockout_seconds = lockout_seconds
        self._fallback = TokenBucket(max_attempts, window_seconds, lockout_attempts, lockout_seconds)

    def _rkey(self, ip):
        return f'ratelimit:login:{ip}'

    def _lkey(self, ip):
        return f'ratelimit:login:lockout:{ip}'

    async def check(self, ip):
        r = _get_rate_redis()
        if r is None or not _redis_available:
            return self._fallback.check(ip)
        try:
            now = time.time()
            cutoff = now - self.window_seconds
            await r.zremrangebyscore(self._rkey(ip), '-inf', cutoff)
            locked = await r.get(self._lkey(ip))
            if locked:
                return False, 'Too many attempts. Try again in 5 minutes.'
            count = await r.zcard(self._rkey(ip))
            if count >= self.max_attempts:
                return False, 'Too many attempts. Try again later.'
            return True, None
        except Exception as e:
            log.warning('Redis rate-limit check failed, falling back: %s', e)
            return self._fallback.check(ip)

    async def record(self, ip, success=False):
        r = _get_rate_redis()
        if r is None or not _redis_available:
            self._fallback.record(ip, success=success)
            return
        try:
            if success:
                await r.delete(self._rkey(ip), self._lkey(ip))
                return
            now = time.time()
            await r.zadd(self._rkey(ip), {str(now): now})
            await r.expire(self._rkey(ip), self.window_seconds + 10)
            count = await r.zcard(self._rkey(ip))
            if count >= self.lockout_attempts:
                await r.setex(self._lkey(ip), self.lockout_seconds, '1')
        except Exception as e:
            log.warning('Redis rate-limit record failed, falling back: %s', e)
            self._fallback.record(ip, success=success)

    async def record_db(self, ip, conn, success=False):
        await self.record(ip, success=success)
        try:
            await conn.execute(
                'INSERT INTO login_attempts (ip, endpoint, success) VALUES ($1, $2, $3)',
                ip, 'login', success,
            )
        except Exception as e:
            log.warning('Failed to record login attempt: %s', e)

    async def remaining(self, ip):
        r = _get_rate_redis()
        if r is None or not _redis_available:
            return self._fallback.remaining(ip)
        try:
            now = time.time()
            cutoff = now - self.window_seconds
            await r.zremrangebyscore(self._rkey(ip), '-inf', cutoff)
            count = await r.zcard(self._rkey(ip))
            return max(0, self.max_attempts - count)
        except Exception as e:
            log.warning('Redis rate-limit remaining failed, falling back: %s', e)
            return self._fallback.remaining(ip)


login_bucket = RedisTokenBucket()
password_bucket = RedisTokenBucket(max_attempts=3, window_seconds=300)
