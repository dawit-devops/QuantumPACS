"""Simple in-memory token-bucket rate limiter for login endpoint.

Limits to N attempts per IP per window_seconds.
Not for distributed deployment — state is process-local.
"""
import time
from collections import defaultdict


class TokenBucket:
    def __init__(self, max_attempts=5, window_seconds=60, lockout_attempts=10, lockout_seconds=300):
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

    def record(self, ip):
        now = time.monotonic()
        self._attempts[ip].append(now)
        if len(self._attempts[ip]) >= self.lockout_attempts:
            self._lockouts[ip] = now + self.lockout_seconds

    def remaining(self, ip):
        self._prune(ip)
        return max(0, self.max_attempts - len(self._attempts[ip]))


login_bucket = TokenBucket()
