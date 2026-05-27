from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from backend.core.security import verify_token
from backend.core.config import settings
from backend.managers.connection import manager

router = APIRouter()

@router.websocket("/ws")
async def websocket_chat(websocket: WebSocket):
    token = websocket.headers.get("sec-websocket-protocol")
    if not token:
        await websocket.close(code=4001, reason="未提供认证令牌")
        return
    try:
        payload = verify_token(token)
        user_id = int(payload.get("sub"))
    except:
        await websocket.close(code=4001, reason="令牌无效")
        return

    await manager.connect(user_id, websocket)
    try:
        while True:
            data = await websocket.receive_text()
            if len(data) > settings.CHAT_MESSAGE_MAX_LENGTH:
                await manager.send_personal(user_id, "消息过长")
                continue
            await manager.broadcast(f"用户 {user_id}: {data}", exclude_user_id=user_id)
            await manager.send_personal(user_id, f"我: {data}")
    except WebSocketDisconnect:
        manager.disconnect(user_id)
    except Exception:
        manager.disconnect(user_id)