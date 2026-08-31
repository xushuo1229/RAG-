"""内存滑动窗口限流（无需外部依赖，替代 Redis 限流）。"""
import time
from collections import defaultdict, deque


class SlidingWindowLimiter:
    def __init__(self, limit: int, window: float):
        self.limit = limit
        self.window = window
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    def allow(self, key: str) -> bool:
        now = time.monotonic()
        q = self._hits[key]
        while q and now - q[0] > self.window:
            q.popleft()
        if len(q) >= self.limit:
            return False
        q.append(now)
        return True


# 问答接口：每位用户每分钟最多 20 次
question_limiter = SlidingWindowLimiter(limit=20, window=60)