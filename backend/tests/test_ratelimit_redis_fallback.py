from unittest.mock import MagicMock, patch

import pytest

from api.ratelimit import RedisTokenBucket


@pytest.fixture(autouse=True)
def _no_redis():
    with patch('api.ratelimit._get_rate_redis', return_value=None):
        with patch('api.ratelimit._redis_available', False):
            yield


class TestRedisTokenBucketFallback:
    async def test_fallback_check_when_redis_unavailable(self):
        bucket = RedisTokenBucket(max_attempts=3, window_seconds=60)
        ok, msg = await bucket.check('fallback-ip')
        assert ok
        await bucket.record('fallback-ip')
        ok, _ = await bucket.check('fallback-ip')
        assert ok

    async def test_fallback_blocks_after_limit(self):
        bucket = RedisTokenBucket(max_attempts=2, window_seconds=60)
        for _ in range(2):
            await bucket.record('block-ip')
        ok, msg = await bucket.check('block-ip')
        assert not ok

    async def test_fallback_record_success_clears(self):
        bucket = RedisTokenBucket(max_attempts=2, window_seconds=60)
        await bucket.record('clear-ip')
        await bucket.record('clear-ip')
        assert bucket._fallback.remaining('clear-ip') == 0
        await bucket.record('clear-ip', success=True)
        assert bucket._fallback.remaining('clear-ip') == bucket.max_attempts

    async def test_fallback_remaining_still_works(self):
        bucket = RedisTokenBucket(max_attempts=5, window_seconds=60)
        assert await bucket.remaining('rem-ip') == 5
        await bucket.record('rem-ip')
        assert await bucket.remaining('rem-ip') == 4

    async def test_fallback_check_delegates_on_redis_error(self):
        mock_redis = MagicMock()
        mock_redis.zremrangebyscore = MagicMock(side_effect=ConnectionError('connection refused'))
        with patch('api.ratelimit._get_rate_redis', return_value=mock_redis):
            with patch('api.ratelimit._redis_available', True):
                bucket = RedisTokenBucket(max_attempts=1, window_seconds=60)
                ok, _ = await bucket.check('err-ip')
                assert ok
                await bucket.record('err-ip')
                ok, msg = await bucket.check('err-ip')
                assert not ok

    async def test_fallback_record_on_redis_error(self):
        mock_redis = MagicMock()
        mock_redis.zadd = MagicMock(side_effect=ConnectionError('connection refused'))
        with patch('api.ratelimit._get_rate_redis', return_value=mock_redis):
            with patch('api.ratelimit._redis_available', True):
                bucket = RedisTokenBucket(max_attempts=1, window_seconds=60)
                await bucket.record('err-ip')
                assert bucket._fallback.remaining('err-ip') == 0

    async def test_fallback_remaining_on_redis_error(self):
        mock_redis = MagicMock()
        mock_redis.zremrangebyscore = MagicMock(side_effect=ConnectionError('connection refused'))
        with patch('api.ratelimit._get_rate_redis', return_value=mock_redis):
            with patch('api.ratelimit._redis_available', True):
                bucket = RedisTokenBucket(max_attempts=3, window_seconds=60)
                remaining = await bucket.remaining('err-ip')
                assert remaining == 3

    async def test_fallback_lockout_still_works(self):
        bucket = RedisTokenBucket(max_attempts=10, window_seconds=60, lockout_attempts=2, lockout_seconds=60)
        await bucket.record('lock-ip')
        await bucket.record('lock-ip')
        ok, msg = await bucket.check('lock-ip')
        assert not ok
        assert '5 minutes' in msg

    async def test_different_ips_independent_in_fallback(self):
        bucket = RedisTokenBucket(max_attempts=1, window_seconds=60)
        await bucket.record('ip-a')
        ok, _ = await bucket.check('ip-b')
        assert ok
