"""socket.io 事件扩展包。

每个事件一个文件，**删掉某个文件就少一个事件**，其它事件照常工作：

======================  ============================================
模块                     事件
======================  ============================================
``connection.py``        connect / disconnect / join
``message.py``           send_message  -> 广播 chat_message
``revoke.py``            revoke_message -> 广播 message_revoked
======================  ============================================

事件通过 ``@sio.event`` 装饰器注册，所以"导入模块"本身就是注册动作。
"""

from __future__ import annotations

import importlib
import pkgutil

from backend.core.logger import logger

#: 已成功加载的事件模块
LOADED: list[str] = []
#: 被跳过的事件模块（缺依赖 / 写错了）
SKIPPED: list[str] = []


def discover(package: str = __name__) -> int:
    """导入包内所有事件模块，返回成功加载的数量。

    单个模块导入失败只记日志，不影响其它事件。
    """
    root = importlib.import_module(package)
    loaded = 0
    for module_info in pkgutil.iter_modules(root.__path__):
        if module_info.name.startswith("_"):
            continue
        full_name = f"{package}.{module_info.name}"
        try:
            importlib.import_module(full_name)
            LOADED.append(full_name)
            loaded += 1
        except Exception as exc:
            logger.warning(f"跳过 socket.io 事件模块 {full_name}: {exc}")
            SKIPPED.append(full_name)
    logger.debug(f"socket.io 事件加载完成：{loaded} 个（跳过 {len(SKIPPED)} 个）")
    return loaded


__all__ = ["LOADED", "SKIPPED", "discover"]
