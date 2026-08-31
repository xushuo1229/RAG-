"""测试 app/core/rate_limit.py：滑动窗口限流器。"""
import time as time_module

from app.core.rate_limit import SlidingWindowLimiter


def test_limit_not_reached():
    """同一 key 在前 N 次允许，超过 limit 后禁止。"""
    limiter = SlidingWindowLimiter(limit=3, window=60)
    assert limiter.allow("user1") is True
    assert limiter.allow("user1") is True
    assert limiter.allow("user1") is True
    assert limiter.allow("user1") is False


def test_keys_independent():
    """不同 key 的计数互不影响。"""
    limiter = SlidingWindowLimiter(limit=1, window=60)
    assert limiter.allow("a") is True
    assert limiter.allow("b") is True


def test_expired_window_allows_again(monkeypatch):
    """窗口滑动后，过期的旧记录被清除，允许再次访问。"""
    limiter = SlidingWindowLimiter(limit=1, window=60)
    assert limiter.allow("a") is True

    # 用极早的时间戳替换窗口内记录，并模拟时间前进到 61 秒
    limiter._hits["a"].clear()
    limiter._hits["a"].append(0.0)
    monkeypatch.setattr(time_module, "monotonic", lambda: 61.0)

    assert limiter.allow("a") is True