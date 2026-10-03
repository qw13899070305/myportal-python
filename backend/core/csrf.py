"""CSRF 防护（双提交 Cookie）。

设计说明
--------
本项目主要使用 ``Authorization: Bearer`` 令牌认证——跨站请求无法自定义
请求头，因此这类请求**天然不受 CSRF 影响**，无需校验。

会被校验的是**未携带令牌的写操作**（登录、注册、提交申请），
它们才是登录型 CSRF（把受害者登录到攻击者账号）的入口。

用法::

    @router.post("/login", dependencies=[Depends(verify_csrf)])
    async def login(...): ...

前端在写请求里带上 ``X-CSRF-Token`` 请求头，值来自 ``GET /api/v1/auth/csrf-token``。
OAuth2 的 ``/auth/token`` 入口按规范豁免（供命令行/文档的 Authorize 使用）。
"""

from fastapi import Request
from fastapi_csrf_protect import CsrfProtect

from backend.core.config import settings

csrf_protect = CsrfProtect()


@csrf_protect.load_config
def _csrf_config():
    return [
        ("secret_key", settings.SECRET_KEY),
        ("cookie_key", "myportal_csrf"),
        ("header_name", "X-CSRF-Token"),
        # lax 足以阻止跨站表单提交，同时不影响站内跳转
        ("cookie_samesite", "lax"),
        # 全站 HTTPS 时应设为 true；用 HTTP 部署时必须保持 false，
        # 否则浏览器不会回传 Cookie，登录会直接 403
        ("cookie_secure", settings.COOKIE_SECURE),
        ("max_age", 60 * 60 * 8),
    ]


def _has_bearer_token(request: Request) -> bool:
    header = request.headers.get("Authorization", "")
    return header.lower().startswith("bearer ")


async def verify_csrf(request: Request) -> None:
    """对未携带 Bearer 令牌的请求执行 CSRF 校验。

    校验失败会抛 ``CsrfProtectError``（在 ``main.py`` 中统一转成 403）。
    """
    if not settings.CSRF_ENABLED:
        return
    if _has_bearer_token(request):
        # 令牌认证的请求不需要 CSRF 保护
        return
    await csrf_protect.validate_csrf(request)
