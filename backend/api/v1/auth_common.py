"""认证接口的公共内核（不放路由）。

注册、登录、令牌、资料四个子模块共用这里的逻辑：

- :func:`issue_tokens` —— 签发访问 + 刷新令牌对
- :func:`parse_login_request` —— 同时解析 JSON 与表单两种登录请求体
- :func:`verify_captcha_if_needed` —— 需要验证码时先校验
- :func:`perform_login` —— 登录主流程（两个入口共用）
"""

from __future__ import annotations

from fastapi import HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.logger import logger
from backend.core.password import get_password_hash, verify_password
from backend.core.tokens import create_access_token, create_refresh_token
from backend.models.user import User, get_user_by_username
from backend.schemas.user import LoginRequest, Token
from backend.services import captcha as captcha_service
from backend.services.audit import log_action, safe_log_action

#: 401 响应统一带上这个头
AUTH_HEADERS = {"WWW-Authenticate": "Bearer"}

# 用户不存在时也执行一次哈希校验，抹平"存在/不存在"的响应耗时差异
DUMMY_HASH = get_password_hash("dummy-password-for-timing-equalization")


def issue_tokens(user: User) -> Token:
    """给用户签发一对新令牌。"""
    subject = {"sub": str(user.id)}
    return Token(
        access_token=create_access_token(subject),
        refresh_token=create_refresh_token(subject),
    )


async def parse_login_request(request: Request) -> LoginRequest:
    """同时支持表单（OAuth2 / docs 的 Authorize）与 JSON 两种提交方式。"""
    content_type = request.headers.get("content-type", "").lower()

    if "application/json" in content_type:
        try:
            data = await request.json()
        except Exception:
            raise HTTPException(status_code=400, detail="请求体不是合法的 JSON") from None
        if not isinstance(data, dict):
            raise HTTPException(status_code=400, detail="请求体格式错误")
        payload = LoginRequest(
            username=str(data.get("username", "")),
            password=str(data.get("password", "")),
            captcha_id=data.get("captcha_id"),
            captcha_code=data.get("captcha_code"),
        )
    else:
        form = await request.form()
        payload = LoginRequest(
            username=str(form.get("username", "")),
            password=str(form.get("password", "")),
            captcha_id=form.get("captcha_id"),
            captcha_code=form.get("captcha_code"),
        )

    if not payload.username or not payload.password:
        raise HTTPException(status_code=400, detail="用户名和密码不能为空")
    return payload


def failure_key(request: Request, payload: LoginRequest) -> str:
    """失败计数的 key：用户名 + 客户端 IP。"""
    client_host = request.client.host if request.client else ""
    return f"{payload.username}|{client_host}"


async def verify_captcha_if_needed(request: Request, payload: LoginRequest) -> str:
    """需要验证码时先校验它，返回用于统计失败次数的 key。"""
    key = failure_key(request, payload)
    if captcha_service.captcha_required(key) and not captcha_service.verify_captcha(
        payload.captcha_id, payload.captcha_code
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="需要验证码，请填写正确的验证码后重试",
        )
    return key


async def perform_login(request: Request, payload: LoginRequest, db: AsyncSession) -> Token:
    """登录主流程（``/auth/login`` 与 ``/auth/token`` 共用）。"""
    key = await verify_captcha_if_needed(request, payload)

    user = await get_user_by_username(db, payload.username)
    if user is None:
        # 耗时对齐，避免用户名枚举
        verify_password(payload.password, DUMMY_HASH)
        captcha_service.record_login_failure(key)
        await safe_log_action(
            db,
            action="login_failed",
            detail=f"用户名不存在: {payload.username}",
            request=request,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
            headers=AUTH_HEADERS,
        )

    if not verify_password(payload.password, user.hashed_password):
        captcha_service.record_login_failure(key)
        await safe_log_action(
            db,
            action="login_failed",
            user_id=user.id,
            detail="密码错误",
            request=request,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
            headers=AUTH_HEADERS,
        )

    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="账号已被禁用")

    captcha_service.clear_login_failures(key)
    await log_action(db, action="login", user_id=user.id, detail="登录成功", request=request)
    await db.commit()
    logger.info(f"用户登录成功: {user.username}")
    return issue_tokens(user)


__all__ = [
    "AUTH_HEADERS",
    "DUMMY_HASH",
    "failure_key",
    "issue_tokens",
    "parse_login_request",
    "perform_login",
    "verify_captcha_if_needed",
]
