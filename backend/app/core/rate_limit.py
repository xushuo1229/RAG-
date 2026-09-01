"""内存滑动窗口限流（无需外部依赖，替代 Redis 限流）。"""
import time
from collections import defaultdict, deque


class SlidingWindowLimiter:
    """进程内的滑动窗口限流器，适合单机部署。"""

    _PRUNE_EVERY = 1000  # 每处理 1000 次请求做一次内存清理，避免 key 无界累积

    def __init__(self, limit: int, window: float):
        self.limit = limit
        self.window = window
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._ops = 0

    def allow(self, key: str) -> bool:
        """判断某 key 在当前窗口内是否还能放行；能则记一次并通过。"""
        now = time.monotonic()
        q = self._hits[key]
        while q and now - q[0] > self.window:
            q.popleft()
        if len(q) >= self.limit:
            return False
        q.append(now)

        self._ops += 1
        if self._ops >= self._PRUNE_EVERY:
            self._ops = 0
            self._prune(now)
        return True

    def _prune(self, now: float) -> None:
        """清理已过期/为空的 key，防止长时间运行后内存持续增长。"""
        stale = [k for k, q in self._hits.items() if not q or now - q[-1] > self.window]
        for k in stale:
            del self._hits[k]


# 问答接口：每位用户每分钟最多 20 次
question_limiter = SlidingWindowLimiter(limit=20, window=60)