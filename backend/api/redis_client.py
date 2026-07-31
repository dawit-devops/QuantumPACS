import asyncio
from config import config
from log import get_logger

log = get_logger(__name__)

_pool = None
_redis_available = False
_connect_lock = asyncio.Lock()
_clients: dict = {}


async def get_client(db=0):
    global _pool, _redis_available
    if _pool is not None:
        if db not in _clients:
            _clients[db] = _make_client(db)
        return _clients[db]
    async with _connect_lock:
        if _pool is not None:
            if db not in _clients:
                _clients[db] = _make_client(db)
            return _clients[db]
        try:
            import redis.asyncio as aioredis
            host = config.get('redis_host', 'localhost')
            port = int(config.get('redis_port', '6379'))
            password = config.get('redis_password') or None
            from redis.asyncio.connection import ConnectionPool as _AsyncPool
            _pool = _AsyncPool(
                host=host, port=port, password=password,
                socket_connect_timeout=2,
                socket_timeout=2,
                max_connections=50,
            )
            r = aioredis.Redis(connection_pool=_pool)
            await r.ping()
            _redis_available = True
            log.info('Connected to Redis at %s:%s (pool)', host, port)
        except Exception as e:
            _pool = None
            _redis_available = False
            log.warning('Redis unavailable, falling back: %s', e)
    if _pool is not None and db not in _clients:
        _clients[db] = _make_client(db)
    return _clients.get(db)


def _make_client(db):
    import redis.asyncio as aioredis
    return aioredis.Redis(connection_pool=_pool, db=db)


def is_available():
    return _redis_available


async def close_client():
    global _pool, _redis_available
    if _pool is not None:
        try:
            await _pool.aclose()
        except Exception:
            pass
        _pool = None
        _redis_available = False
