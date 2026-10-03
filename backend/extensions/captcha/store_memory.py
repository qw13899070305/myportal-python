"""验证码答案的内存存储（默认实现）。

特点：一次性消费、带过期时间、有容量上限防止内存无限增长。
单进程部署够用；多副本部署请再加一个 Redis 实现并把 priority 调高。
"""

from __future__ import annotations

import time

from backend.extensions.captcha.base import CaptchaStore
from backend.extensions.registry import get_registry


class MemoryCaptchaStore(CaptchaStore):
    name = "memory"
    priority = 0

    #: 最多同时保留多少个验证码
    max_entries = 5000

    def __init__(self) -> None:
        #: captcha_id -> (答案, 过期时间戳)
        self._data: dict[str, tuple[str, float]] = {}

    def _purge(self) -> None:
        now = time.time()
        for key in [k for k, (_, expire_at) in self._data.items() if expire_at <= now]:
            self._data.pop(key, None)
        # 防止内存无限增长
        if len(self._data) > self.max_entries:
            overflow = len(self._data) - self.max_entries
            for key in list(self._data)[:overflow]:
                self._data.pop(key, None)

    def save(self, captcha_id: str, code: str, ttl: int) -> None:
        self._purge()
        self._data[captcha_id] = (code, time.time() + ttl)

    def take(self, captcha_id: str) -> str | None:
        entry = self._data.pop(captcha_id, None)
        if entry is None:
            return None
        code, expire_at = entry
        if expire_at <= time.time():
            return None
        return code

    def clear(self) -> None:
        self._data.clear()

    def size(self) -> int:
        """当前保存的验证码数量。

        注意：这里刻意**不实现** ``__len__``——一旦有了 ``__len__``，
        空的存储会在 ``if store:`` 里变成假值，非常容易踩坑。
        """
        return len(self._data)


get_registry("captcha_store").register(MemoryCaptchaStore())
