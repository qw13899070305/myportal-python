"""socket.io 实时聊天（对外门面）。

前端 ``frontend/src/pages/chat/Chat.vue`` 通过
``io('/', { path: '/ws/socket.io' })`` 连接，令牌放在 ``auth.token`` 里。

真正的实现拆成了几个可以单独摘掉的部分：

- :mod:`backend.socketio.server` —— ``sio`` 实例与允许的来源
- :mod:`backend.socketio.auth`   —— 握手令牌解析
- :mod:`backend.socketio.events` —— 事件扩展包（每个事件一个文件）
  - ``connection.py``  connect / disconnect / join
  - ``message.py``     send_message
  - ``revoke.py``      revoke_message

本模块只负责：创建 ``sio`` -> 发现并加载事件 -> 对外暴露 ``sio``。
删掉某个事件文件，其余事件照常工作。
"""

from __future__ import annotations

from backend.core.logger import logger
from backend.socketio import events
from backend.socketio.server import allowed_origins, sio  # noqa: F401  对外转发

#: 导入事件模块即完成注册（``@sio.event`` 装饰器在导入时执行）
events.discover()

if events.SKIPPED:  # pragma: no cover - 仅在事件模块有问题时进入
    logger.warning(f"socket.io 有 {len(events.SKIPPED)} 个事件模块被跳过")

__all__ = ["allowed_origins", "events", "sio"]
