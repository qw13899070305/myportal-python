"""令牌接口（可拆卸扩展）。

- ``POST /auth/refresh`` —— 用刷新令牌换新令牌对，旧刷新令牌立即作废（轮换）
- ``POST /auth/logout``  —— 把当前访问令牌加入黑名单，退出后立即失效
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.v1.auth_common import AUTH_HEADERS, issue_tokens
from backend.core.blacklist import add_token_to_blacklist, is_token_blacklisted
from backend.core.database import get_db
from backend.core.logger import logger
from backend.core.rate_limit import limiter
from backend.core.security import get_current_user, oauth2_scheme
from backend.core.tokens import decode_token, remaining_ttl, subject_of
from backend.models.user import User, get_user_by_id
from backend.schemas.common import Message
from backend.schemas.user import RefreshRequest, Token

router = APIRouter()


@router.post("/refresh", response_model=Token)
@limiter.limit("20/minute")
async def refresh_token(
    request: Request,
    payload: RefreshRequest,
    db: AsyncSession = Depends(get_db),
):
    """用刷新令牌换取新的令牌对；旧刷新令牌立即作废（令牌轮换）。"""
    data = decode_token(payload.refresh_token, expected_type="refresh")

    jti = data.get("jti", "")
    if await is_token_blacklisted(jti):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="刷新令牌已失效，请重新登录",
            headers=AUTH_HEADERS,
        )

    user = await get_user_by_id(db, subject_of(data))
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户不存在或已被禁用",
            headers=AUTH_HEADERS,
        )

    await add_token_to_blacklist(jti, remaining_ttl(data))
    return issue_tokens(user)


@router.post("/logout", response_model=Message)
async def logout(
    current_user: User = Depends(get_current_user),
    access_token: str = Depends(oauth2_scheme),
):
    """退出登录：把当前访问令牌加入黑名单。"""
    payload = decode_token(access_token, expected_type="access")
    await add_token_to_blacklist(payload.get("jti", ""), remaining_ttl(payload))
    logger.info(f"用户退出登录: {current_user.username}")
    return Message(message="已退出登录")
