from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession
from backend.core.database import AsyncSessionLocal, get_db
from backend.core.security import get_current_user
from backend.models.user import User
from backend.models.chat import ChatMessage
from sqlalchemy import select, func
from typing import Optional
import json

router = APIRouter()

@router.get("/messages")
async def get_messages(
    page: int = 1,
    size: int = 20,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # 计算总数
    total_query = select(func.count(ChatMessage.id))
    total_result = await db.execute(total_query)
    total = total_result.scalar()

    # 查询消息，按时间倒序
    stmt = select(ChatMessage).order_by(ChatMessage.created_at.desc()).offset((page - 1) * size).limit(size)
    result = await db.execute(stmt)
    messages = result.scalars().all()

    # 转为字典列表并反转顺序为时间正序
    items = [
        {
            "id": m.id,
            "user_id": m.user_id,
            "username": m.user.username if m.user else "未知",
            "content": m.content,
            "created_at": m.created_at.isoformat()
        }
        for m in reversed(messages)
    ]

    return {"total": total, "items": items}

@router.websocket("/ws")
async def websocket_chat(websocket: WebSocket, token: str = None):
    # 连接后首消息鉴权（不再从 URL 参数中取 token）
    await websocket.accept()
    try:
        # 等待客户端发送认证消息
        data = await websocket.receive_text()
        auth_msg = json.loads(data)
        token = auth_msg.get("token")
        if not token:
            await websocket.close(code=4001, reason="缺少认证令牌")
            return

        # 验证 token
        from backend.core.security import verify_token, get_current_user
        payload = verify_token(token)
        user_id = payload.get("sub")
        if not user_id:
            await websocket.close(code=4001, reason="无效令牌")
            return

        async with AsyncSessionLocal() as db:
            from backend.models.user import User
            from sqlalchemy import select
            from sqlalchemy.orm import selectinload
            result = await db.execute(select(User).options(selectinload(User.roles)).where(User.id == int(user_id)))
            user = result.scalar_one_or_none()
            if not user:
                await websocket.close(code=4001, reason="用户不存在")
                return

            # 认证通过，进入消息循环
            while True:
                raw = await websocket.receive_text()
                msg_data = json.loads(raw)
                content = msg_data.get("content", "").strip()
                if not content or len(content) > 2000:
                    continue

                new_msg = ChatMessage(user_id=user.id, content=content)
                db.add(new_msg)
                await db.commit()
                await db.refresh(new_msg)

                response = {
                    "type": "message",
                    "id": new_msg.id,
                    "user_id": new_msg.user_id,
                    "username": user.username,
                    "content": new_msg.content,
                    "created_at": new_msg.created_at.isoformat()
                }
                await websocket.send_text(json.dumps(response))
    except WebSocketDisconnect:
        pass
    except Exception as e:
        # 生产环境应记录日志并安全关闭
        await websocket.close(code=4000, reason="服务器错误")