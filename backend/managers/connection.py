"""WebSocket 连接管理。

同一个用户可以同时打开多个页面/标签页，因此按用户维护一个连接集合。
方法名保持向后兼容（``connect`` / ``disconnect`` / ``send_personal`` / ``broadcast``），
另外增加了 ``register``（用于已经 accept 过的连接）。
"""

import json
from collections import defaultdict

from fastapi import WebSocket

from backend.core.logger import logger


class ConnectionManager:
    def __init__(self) -> None:
        self.active_connections: dict[int, set[WebSocket]] = defaultdict(set)

    # ---------------- 生命周期 ----------------

    async def connect(self, user_id: int, websocket: WebSocket) -> None:
        """接受连接并登记。"""
        await websocket.accept()
        self.register(user_id, websocket)

    def register(self, user_id: int, websocket: WebSocket) -> None:
        """登记一个已经 accept 过的连接。"""
        self.active_connections[user_id].add(websocket)
        logger.info(
            f"用户 {user_id} 建立 WebSocket 连接，当前在线用户数 {len(self.active_connections)}"
        )

    def disconnect(self, user_id: int, websocket: WebSocket | None = None) -> None:
        """注销连接；不传 websocket 时移除该用户的全部连接。"""
        if websocket is None:
            self.active_connections.pop(user_id, None)
        else:
            sockets = self.active_connections.get(user_id)
            if sockets is not None:
                sockets.discard(websocket)
                if not sockets:
                    self.active_connections.pop(user_id, None)
        logger.info(
            f"用户 {user_id} 断开 WebSocket 连接，当前在线用户数 {len(self.active_connections)}"
        )

    # ---------------- 发送 ----------------

    @staticmethod
    def _dumps(payload) -> str:
        """允许直接传 dict（自动转 JSON）或已经序列化好的字符串。"""
        if isinstance(payload, str):
            return payload
        return json.dumps(payload, ensure_ascii=False, default=str)

    async def send_personal(self, user_id: int, message) -> None:
        """给某个用户的所有连接推送消息。"""
        text = self._dumps(message)
        dead: list[WebSocket] = []
        for websocket in list(self.active_connections.get(user_id, ())):
            try:
                await websocket.send_text(text)
            except Exception:
                dead.append(websocket)
        for websocket in dead:
            self.disconnect(user_id, websocket)

    async def broadcast(self, message, exclude_user_id: int | None = None) -> None:
        """给所有在线用户推送消息。"""
        for user_id in list(self.active_connections):
            if user_id == exclude_user_id:
                continue
            await self.send_personal(user_id, message)

    # ---------------- 查询 ----------------

    @property
    def online_user_ids(self) -> list[int]:
        return list(self.active_connections)

    @property
    def online_count(self) -> int:
        return len(self.active_connections)


manager = ConnectionManager()
