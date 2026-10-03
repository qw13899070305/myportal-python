"""子路由加载器（可拆卸机制的核心零件）。

单独放一个模块是为了**避免循环导入**：``backend/api/v1/__init__.py``
要导入各个路由模块，而各路由模块（例如 ``auth.py``）又想用同一套
「可选加载」逻辑来组合自己的子模块。把加载器独立出来，双方都能安全引用。

两级可拆卸：

1. **组内**：``auth.py`` 用 ``include_optional`` 组合
   ``auth_login`` / ``auth_register`` ……，缺一个不影响其它
2. **整组**：``backend/api/v1/__init__.py`` 用同一套逻辑组合所有组，
   扩展组缺了只记日志
"""

from __future__ import annotations

import importlib
from collections.abc import Iterable

from fastapi import APIRouter

from backend.core.logger import logger

#: 全局记录：实际挂载成功 / 被跳过的模块（供健康检查与测试断言）
LOADED: list[str] = []
SKIPPED: list[str] = []


def _short(module_path: str) -> str:
    """``backend.api.v1.auth_login`` -> ``auth_login``"""
    return module_path.rsplit(".", 1)[-1]


def include(
    parent: APIRouter,
    module_path: str,
    prefix: str = "",
    tags: Iterable[str] | None = None,
    *,
    required: bool = False,
) -> bool:
    """导入子模块并把它挂到 ``parent`` 上。

    - ``required=True``：导入失败直接抛异常（基本盘，问题要尽早暴露）
    - ``required=False``：导入失败只记一条日志并跳过（扩展件，可拆卸）
    """
    tag_list = list(tags or [])
    try:
        module = importlib.import_module(module_path)
    except Exception as exc:
        if required:
            raise
        logger.warning(f"跳过不可用的 API 模块 {module_path}: {exc}")
        SKIPPED.append(module_path)
        return False

    sub_router = getattr(module, "router", None)
    if sub_router is None:
        message = f"{module_path} 没有定义 router"
        if required:
            raise RuntimeError(message)
        logger.warning(f"跳过 API 模块：{message}")
        SKIPPED.append(module_path)
        return False

    parent.include_router(sub_router, prefix=prefix, tags=tag_list)
    LOADED.append(module_path)
    return True


def include_optional(
    parent: APIRouter,
    module_path: str,
    prefix: str = "",
    tags: Iterable[str] | None = None,
) -> bool:
    """挂载一个可摘掉的扩展模块。"""
    return include(parent, module_path, prefix, tags, required=False)


def include_required(
    parent: APIRouter,
    module_path: str,
    prefix: str = "",
    tags: Iterable[str] | None = None,
) -> bool:
    """挂载一个必须存在的核心模块。"""
    return include(parent, module_path, prefix, tags, required=True)


def include_group(
    parent: APIRouter,
    parts: Iterable[tuple[str, str, list[str]]],
    *,
    required: bool = False,
) -> int:
    """批量挂载 ``[(模块, 前缀, 标签), ...]``，返回成功的数量。"""
    count = 0
    for module_path, prefix, tags in parts:
        if include(parent, module_path, prefix, tags, required=required):
            count += 1
    return count


def summary() -> str:
    """给启动日志用的一句话总结。"""
    text = f"{len(LOADED)} 个 API 模块已挂载"
    if SKIPPED:
        text += f"，{len(SKIPPED)} 个被跳过（{', '.join(_short(m) for m in SKIPPED)}）"
    return text


__all__ = [
    "LOADED",
    "SKIPPED",
    "include",
    "include_group",
    "include_optional",
    "include_required",
    "summary",
]
