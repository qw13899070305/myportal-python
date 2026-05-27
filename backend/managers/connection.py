from fastapi import WebSocket
from backend.core.logger import logger

class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[int, WebSocket] = {}

    async def connect(self, user_id: int, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[user_id] = websocket
        logger.info(f"用户 {user_id} 上线，当前在线: {len(self.active_connections)}")

    def disconnect(self, user_id: int):
        self.active_connections.pop(user_id, None)
        logger.info(f"用户 {user_id} 下线，当前在线: {len(self.active_connections)}")

    async def send_personal(self, user_id: int, message: str):
        ws = self.active_connections.get(user_id)
        if ws:
            try:
                await ws.send_text(message)
            except Exception:
                self.disconnect(user_id)

    async def broadcast(self, message: str, exclude_user_id: int = None):
        dead = []
        for uid, ws in self.active_connections.items():
            if uid == exclude_user_id:
                continue
            try:
                await ws.send_text(message)
            except Exception:
                dead.append(uid)
        for uid in dead:
            self.disconnect(uid)

manager = ConnectionManager()