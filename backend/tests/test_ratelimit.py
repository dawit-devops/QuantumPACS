from unittest.mock import patch


from api.ratelimit import TokenBucket


class TestTokenBucket:
    def test_allows_within_limit(self):
        b = TokenBucket(max_attempts=3, window_seconds=60)
        for _ in range(3):
            ok, msg = b.check('1.2.3.4')
            assert ok
            b.record('1.2.3.4')

    def test_blocks_after_limit(self):
        b = TokenBucket(max_attempts=2, window_seconds=60)
        for _ in range(2):
            ok, _ = b.check('5.6.7.8')
            b.record('5.6.7.8')
        ok, msg = b.check('5.6.7.8')
        assert not ok
        assert 'later' in msg

    def test_different_ips_independent(self):
        b = TokenBucket(max_attempts=1, window_seconds=60)
        ok, _ = b.check('ip-a')
        b.record('ip-a')
        ok, _ = b.check('ip-b')
        assert ok

    def test_remaining_decreases(self):
        b = TokenBucket(max_attempts=5, window_seconds=60)
        assert b.remaining('rem-ip') == 5
        b.record('rem-ip')
        assert b.remaining('rem-ip') == 4

    def test_remaining_floor_zero(self):
        b = TokenBucket(max_attempts=2, window_seconds=60)
        b.record('floor-ip')
        b.record('floor-ip')
        assert b.remaining('floor-ip') == 0

    def test_lockout_after_threshold(self):
        b = TokenBucket(max_attempts=3, window_seconds=60, lockout_attempts=2, lockout_seconds=60)
        for _ in range(2):
            ok, _ = b.check('lock-ip')
            b.record('lock-ip')
        ok, msg = b.check('lock-ip')
        assert not ok
        assert '5 minutes' in msg

    def test_window_expires(self):
        with patch('api.ratelimit.time.monotonic') as mock_time:
            mock_time.return_value = 1000.0
            b = TokenBucket(max_attempts=1, window_seconds=60, lockout_attempts=10)
            ok, _ = b.check('exp-ip')
            b.record('exp-ip')
            assert b.remaining('exp-ip') == 0
            mock_time.return_value = 1061.0
            assert b.remaining('exp-ip') == 1
