"""连接相关事件：connect / disconnect / join。

职责：
- 握手时校验 Origin 与访问令牌
- 把用户信息写入 socket.io 会话，供其它事件读取
- 广播上下线
"""

from __future__ import annotations

import jwt

from backend.core.database import AsyncSessionLocal
from backend.core.logger import logger
from backend.models.user import User
from backend.socketio.auth import decode_user_id, extract_token
from backend.socketio.server import origin_allowed, sio


@sio.event
async def connect(sid, environ, auth=None):
    """校验 Origin 与令牌，通过后把用户写入 socket.io 会话。"""
    origin = environ.get("HTTP_ORIGIN") or environ.get("HTTP_REFERER", "")
    if origin and not origin_allowed(origin):
        logger.warning(f"socket.io 拒绝来源: {origin}")
        raise ConnectionRefusedError("origin not allowed")

    token = extract_token(environ, auth)
    if not token:
        raise ConnectionRefusedError("authentication failed")

    try:
        user_id = decode_user_id(token)
    except (jwt.PyJWTError, TypeError, ValueError):
        raise ConnectionRefusedError("invalid token") from None

    async with AsyncSessionLocal() as db:
        user = await db.get(User, user_id)
        if user is None or not user.is_active:
            raise ConnectionRefusedError("user not found or disabled")
        username = user.username

    await sio.save_session(sid, {"user_id": user_id, "username": username})
    logger.info(f"socket.io 用户 {username} 已连接 (sid={sid})")
    await sio.emit(
        "user_joined",
        {"user_id": user_id, "username": username},
        skip_sid=sid,
    )
    return True


@sio.event
async def disconnect(sid):
    """断开连接：只记日志，会话由 socket.io 自行清理。"""
    session = await sio.get_session(sid)
    user_id = (session or {}).get("user_id")
    logger.info(f"socket.io 连接断开 (sid={sid}, user_id={user_id})")


@sio.event
async def join(sid, data=None):
    """把当前用户标记为已加入聊天室（前端可用来拉在线列表）。"""
    session = await sio.get_session(sid)
    user_id = (session or {}).get("user_id")
    if user_id:
        await sio.emit("user_joined", {"user_id": user_id}, skip_sid=sid)
    return {"ok": True}
