"""验证码扩展包。

由三类可替换零件组成：

======================  ==================================================
零件                     可选项
======================  ==================================================
``image.py``            渲染器：Pillow 画图（``priority=10``）
``store_memory.py``     存储：进程内存（``priority=0``）
``failures.py``         登录失败计数（滑动窗口）
======================  ==================================================

渲染器和存储都通过全局注册表挑选**优先级最高**的一个：

- 想换成滑块验证 → 新增一个 ``slider.py`` 实现 ``CaptchaRenderer`` 并给更高 priority
- 想多副本共享验证码 → 新增 ``store_redis.py`` 实现 ``CaptchaStore`` 并给更高 priority
- 删掉 ``image.py`` → 没有可用渲染器，接口层返回 503，其余功能不受影响
"""

from __future__ import annotations

import secrets

from backend.core.config import settings
from backend.core.logger import logger
from backend.extensions.captcha.base import (
    CaptchaChallenge,
    CaptchaRenderer,
    CaptchaStore,
)
from backend.extensions.captcha.failures import LoginFailureTracker, tracker
from backend.extensions.registry import discover_extensions

#: 导入包内所有零件（base / failures 只提供基类和计数器，不需要注册）
_skip = {"base", "failures"}
renderers = discover_extensions(__name__, "captcha_renderer", "验证码渲染器", skip=_skip)
stores = discover_extensions(__name__, "captcha_store", "验证码存储", skip=_skip)


def active_renderer() -> CaptchaRenderer | None:
    """当前生效的渲染器（优先级最高的）。"""
    return next(iter(renderers.sorted_items(key=lambda item: -item.priority)), None)


def active_store() -> CaptchaStore | None:
    """当前生效的存储（优先级最高的）。"""
    return next(iter(stores.sorted_items(key=lambda item: -item.priority)), None)


def create_challenge() -> tuple[str, CaptchaChallenge] | None:
    """生成验证码，返回 ``(captcha_id, challenge)``；没有渲染器时返回 None。"""
    renderer = active_renderer()
    store = active_store()
    if renderer is None or store is None:
        logger.error("没有可用的验证码渲染器或存储，无法生成验证码")
        return None

    challenge = renderer.create()
    captcha_id = secrets.token_urlsafe(16)
    store.save(captcha_id, challenge.code, settings.CAPTCHA_EXPIRE_SECONDS)
    return captcha_id, challenge


def verify(captcha_id: str | None, code: str | None) -> bool:
    """校验验证码；无论成功与否都会作废（一次性）。"""
    if not captcha_id or not code:
        return False
    store = active_store()
    if store is None:
        return False
    expected = store.take(captcha_id)
    if expected is None:
        return False
    return secrets.compare_digest(expected, str(code).strip().upper())


def reset() -> None:
    """清空全部状态（测试用）。"""
    store = active_store()
    if store is not None:
        store.clear()
    tracker.clear_all()


__all__ = [
    "CaptchaChallenge",
    "CaptchaRenderer",
    "CaptchaStore",
    "LoginFailureTracker",
    "active_renderer",
    "active_store",
    "create_challenge",
    "renderers",
    "reset",
    "stores",
    "tracker",
    "verify",
]
