"""登录失败计数（独立零件）。

滑动窗口统计「某个 key（用户名 + IP）在窗口期内失败了几次」，
达到 ``CAPTCHA_TRIGGER_FAILURES`` 次就要求验证码。

和验证码本身解耦：就算不启用验证码，这个计数器也可以
单独用来做告警或临时封禁。
"""

from __future__ import annotations

import time

from backend.core.config import settings


class LoginFailureTracker:
    """滑动窗口失败计数器。"""

    def __init__(self, window_seconds: int | None = None, threshold: int | None = None):
        self.window_seconds = window_seconds
        self.threshold = threshold
        #: key -> 失败时间戳列表
        self._buckets: dict[str, list[float]] = {}

    # ---------------- 配置 ----------------

    @property
    def window(self) -> int:
        return (
            self.window_seconds
            if self.window_seconds is not None
            else settings.CAPTCHA_EXPIRE_SECONDS
        )

    @property
    def limit(self) -> int:
        return self.threshold if self.threshold is not None else settings.CAPTCHA_TRIGGER_FAILURES

    # ---------------- 读写 ----------------

    def _recent(self, key: str) -> list[float]:
        now = time.time()
        bucket = [t for t in self._buckets.get(key, []) if now - t < self.window]
        if bucket:
            self._buckets[key] = bucket
        else:
            self._buckets.pop(key, None)
        return bucket

    def record(self, key: str) -> int:
        """记录一次失败，返回窗口期内的累计次数。"""
        bucket = self._recent(key)
        bucket.append(time.time())
        self._buckets[key] = bucket
        return len(bucket)

    def count(self, key: str) -> int:
        """窗口期内的失败次数。"""
        return len(self._recent(key))

    def required(self, key: str) -> bool:
        """是否已达到要求验证码的阈值。"""
        return self.count(key) >= self.limit

    def clear(self, key: str) -> None:
        """清空某个 key 的计数（登录成功后调用）。"""
        self._buckets.pop(key, None)

    def clear_all(self) -> None:
        self._buckets.clear()


#: 全局共享的失败计数器
tracker = LoginFailureTracker()

__all__ = ["LoginFailureTracker", "tracker"]
