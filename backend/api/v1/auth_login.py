"""登录接口（可拆卸扩展）。

两个入口，行为一致：

- ``POST /auth/login``  —— 前端使用，JSON 或表单都行，**需要 CSRF**
- ``POST /auth/token``  —— OAuth2 密码模式，供 ``/docs`` 的 Authorize
  与命令行客户端使用，按规范**豁免 CSRF**

两者共用 :func:`backend.api.v1.auth_common.perform_login`。
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.v1.auth_common import parse_login_request, perform_login
from backend.core.csrf import verify_csrf
from backend.core.database import get_db
from backend.core.rate_limit import limiter
from backend.schemas.user import Token

router = APIRouter()


@router.post("/token", response_model=Token)
@limiter.limit("10/minute")
async def login_oauth2(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """OAuth2 密码模式入口（``/docs`` 的 Authorize 按钮、命令行客户端）。"""
    payload = await parse_login_request(request)
    return await perform_login(request, payload, db)


@router.post("/login", response_model=Token, dependencies=[Depends(verify_csrf)])
@limiter.limit("10/minute")
async def login(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """登录。

    连续失败达到阈值后会要求携带图形验证码
    （``captcha_id`` + ``captcha_code``）。
    """
    payload = await parse_login_request(request)
    return await perform_login(request, payload, db)
