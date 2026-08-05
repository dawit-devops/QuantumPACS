import asyncio
from config import config
from log import get_logger

log = get_logger(__name__)

_redis = None
_redis_available = False
_connect_lock = asyncio.Lock()


async def get_client():
    global _redis, _redis_available
    if _redis is not None:
        return _redis
    async with _connect_lock:
        if _redis is not None:
            return _redis
        try:
            import redis.asyncio as aioredis
            host = config.get('redis_host', 'localhost')
            port = int(config.get('redis_port', '6379'))
            password = config.get('redis_password') or None
            _redis = aioredis.Redis(
                host=host, port=port, password=password, db=0,
                socket_connect_timeout=2,
                socket_timeout=2,
                retry_on_timeout=False,
            )
            await _redis.ping()
            _redis_available = True
            log.info('Connected to Redis at %s:%s', host, port)
        except Exception as e:
            _redis = None
            _redis_available = False
            log.warning('Redis unavailable, falling back: %s', e)
    return _redis


def is_available():
    return _redis_available


async def close_client():
    global _redis, _redis_available
    if _redis is not None:
        try:
            await _redis.aclose()
        except Exception:
            pass
        _redis = None
        _redis_available = False
