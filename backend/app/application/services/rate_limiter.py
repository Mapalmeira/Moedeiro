import math
import time
from functools import lru_cache


class RateLimitExceededError(Exception):
    def __init__(self, retry_after: int):
        self.retry_after = retry_after


class RateLimiter:
    def __init__(self):
        from limits.storage import MemoryStorage
        from limits.strategies import MovingWindowRateLimiter

        self._strategy = MovingWindowRateLimiter(MemoryStorage())

    def check(self, rate: str, namespace: str, key: str) -> None:
        rate_limit = self._parse(rate)
        if self._strategy.hit(rate_limit, namespace, key):
            return
        window = self._strategy.get_window_stats(rate_limit, namespace, key)
        raise RateLimitExceededError(max(1, math.ceil(window.reset_time - time.time())))

    @staticmethod
    @lru_cache
    def _parse(rate: str):
        from limits import parse

        return parse(rate)
