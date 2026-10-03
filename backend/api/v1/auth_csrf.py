"""CSRF 令牌接口（可拆卸扩展）。

``GET /auth/csrf-token`` 签发双提交 Cookie 令牌，
前端在未登录的写请求（登录 / 注册 / 申请）里通过
``X-CSRF-Token`` 请求头回传。

真正的校验逻辑在 :mod:`backend.core.csrf`，本文件只负责签发。
把本文件删掉后，``/auth/csrf-token`` 会 404，前端的写请求会因为
拿不到令牌而被 ``verify_csrf`` 拒绝——所以要么一起摘掉
（``CSRF_ENABLED=false``），要么保留。
"""

from fastapi import APIRouter, Request, Response

from backend.core.csrf import csrf_protect
from backend.core.rate_limit import limiter

router = APIRouter()


@router.get("/csrf-token")
@limiter.limit("60/minute")
async def get_csrf_token(request: Request, response: Response):
    """签发 CSRF 令牌（同时把签名写入 Cookie）。"""
    token, signed = csrf_protect.generate_csrf_tokens()
    csrf_protect.set_csrf_cookie(signed, response)
    return {"csrf_token": token}
