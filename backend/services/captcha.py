"""图形验证码（对外门面）。

实现拆成了**可替换的零件**，放在 :mod:`backend.extensions.captcha`：

    backend/extensions/captcha/image.py          渲染器：Pillow 画 PNG
    backend/extensions/captcha/store_memory.py   存储：进程内存（一次性 + 过期）
    backend/extensions/captcha/failures.py       登录失败计数（滑动窗口）

设计：
- 答案只保存在服务端，带过期时间且一次性使用
- 登录连续失败达到阈值后强制要求验证码，防止暴力破解
- ``X-Captcha-Id`` 响应头把验证码 id 交给前端，前端登录时回传

本模块保留了原有的函数名，历史代码与测试无需改动。
"""

from __future__ import annotations

from backend.core.logger import logger
from backend.extensions.captcha import (
    CaptchaChallenge,  # noqa: F401
    active_renderer,
    active_store,
    create_challenge,
    reset,
    tracker,
    verify,
)


def create_captcha() -> tuple[str, bytes]:
    """生成验证码，返回 ``(captcha_id, png_bytes)``。

    没有可用渲染器时抛 ``RuntimeError``（由接口层转成 503）。
    """
    result = create_challenge()
    if result is None:
        raise RuntimeError("验证码服务不可用")
    captcha_id, challenge = result
    return captcha_id, challenge.image


def verify_captcha(captcha_id: str | None, code: str | None) -> bool:
    """校验验证码；无论成功与否都会作废该验证码（一次性）。"""
    return verify(captcha_id, code)


# ---------------- 登录失败计数 ----------------


def record_login_failure(key: str) -> int:
    """记录一次登录失败，返回窗口期内的累计次数。"""
    return tracker.record(key)


def captcha_required(key: str) -> bool:
    """该 key（用户名 + IP）是否需要验证码。"""
    return tracker.required(key)


def clear_login_failures(key: str) -> None:
    """登录成功后清空失败计数。"""
    tracker.clear(key)


def status() -> dict:
    """当前验证码配置概况（供健康检查展示）。

    注意用 ``is not None`` 判断：存储对象可能实现了 ``__len__``，
    空的时候 ``if store:`` 会意外为假。
    """
    renderer = active_renderer()
    store = active_store()
    return {
        "renderer": renderer.name if renderer is not None else None,
        "store": store.name if store is not None else None,
        "trigger_failures": tracker.limit,
        "expire_seconds": tracker.window,
    }


logger.debug("验证码服务已初始化")

__all__ = [
    "CaptchaChallenge",
    "captcha_required",
    "clear_login_failures",
    "create_captcha",
    "record_login_failure",
    "reset",
    "status",
    "verify_captcha",
]
