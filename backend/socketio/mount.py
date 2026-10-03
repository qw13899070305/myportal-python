"""socket.io 挂载（可拆卸扩展）。

``socketio_path=None`` 表示「挂载点下的所有请求都交给 socket.io 处理」。

这样写是为了不依赖 Starlette 版本对 ``Mount`` 是否剥离路径前缀的行为：
新版 Starlette 只设置 ``root_path``、保留完整 ``path``，
若按默认的 ``socketio_path="socket.io"`` 去匹配，会因为
``path`` 是 ``/ws/socket.io/`` 而全部 404。
"""

from __future__ import annotations

import socketio
from fastapi import FastAPI

from backend.core.logger import logger

#: 挂载点，前端连接 ``/ws/socket.io``
SOCKETIO_MOUNT_PATH = "/ws"


def mount_socketio(app: FastAPI, path: str = SOCKETIO_MOUNT_PATH) -> bool:
    """挂载 socket.io；缺少 python-socketio 时静默跳过。"""
    try:
        from backend.socketio.handlers import sio
    except Exception as exc:
        logger.warning(f"未挂载 socket.io（{exc}）；实时聊天将只能用原生 WebSocket")
        return False

    app.mount(path, socketio.ASGIApp(sio, socketio_path=None))
    logger.info(f"已挂载 socket.io: {path}/socket.io")
    return True
