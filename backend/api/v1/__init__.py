"""API v1 路由聚合（两级可拆卸）。

设计原则：**每个模块都是可以单独摘掉的零件**。

1. **整组**：``CORE_ROUTERS`` 是基本盘（缺了直接报错），
   ``EXTRA_ROUTERS`` 是扩展能力（缺了只记日志，应用照常启动）
2. **组内**：``auth.py`` / ``articles.py`` / ``files.py`` 各自再用
   ``include_optional`` 组合自己的子零件（登录、注册、上传、下载……）

两级用的是同一套加载器 :mod:`backend.api.v1._loader`，
所以「已挂载 / 被跳过」只有一份记录，不会出现两处状态不一致。

所有子模块都**不带 prefix**，前缀统一在这里声明，
避免出现 ``/users/users`` 这类前缀重复。
"""

from __future__ import annotations

from fastapi import APIRouter

from backend.api.v1._loader import (
    LOADED,
    SKIPPED,
    include_optional,
    include_required,
    summary,
)
from backend.core.logger import logger

#: (模块路径, 前缀, 标签)
CORE_ROUTERS: list[tuple[str, str, list[str]]] = [
    # 认证组：组内再拆成 登录/注册/令牌/资料/验证码/头像/CSRF 等零件
    ("backend.api.v1.auth", "/auth", ["认证"]),
    ("backend.api.v1.users", "/users", ["用户"]),
    # 文件组：组内再拆成 列表/上传/下载/编辑 等零件
    ("backend.api.v1.files", "/files", ["文件"]),
    # 文章组：组内再拆成 列表/CRUD/标签/收藏夹 等零件
    ("backend.api.v1.articles", "/articles", ["文章"]),
    ("backend.api.v1.chat", "/chat", ["聊天"]),
    ("backend.api.v1.chat_api", "/chat", ["聊天"]),
    ("backend.api.v1.admin", "/admin", ["管理"]),
]

#: 扩展路由：任意一个导入失败都会被跳过，不影响其它功能
EXTRA_ROUTERS: list[tuple[str, str, list[str]]] = [
    # 文件相关
    ("backend.api.v1.file_preview", "/files", ["文件-预览"]),
    ("backend.api.v1.trash", "/trash", ["回收站"]),
    ("backend.api.v1.share", "/share", ["分享"]),
    # 文章相关
    ("backend.api.v1.comments", "/articles", ["评论"]),
    ("backend.api.v1.article_likes", "/articles", ["点赞收藏"]),
    ("backend.api.v1.article_review", "/articles", ["文章审核"]),
    ("backend.api.v1.article_delete", "/articles", ["文章管理"]),
    ("backend.api.v1.withdraw", "/articles", ["文章管理"]),
    ("backend.api.v1.categories", "/categories", ["分类"]),
    ("backend.api.v1.search_api", "/search", ["搜索"]),
    # 通知
    ("backend.api.v1.notifications", "/notifications", ["通知"]),
    # 后台
    ("backend.api.v1.admin_users", "/admin", ["管理-用户"]),
    ("backend.api.v1.admin_chat", "/admin", ["管理-聊天"]),
    ("backend.api.v1.admin_config", "/admin", ["管理-配置"]),
    ("backend.api.v1.admin_cleanup", "/admin/files", ["管理-清理"]),
    ("backend.api.v1.audit", "/audit", ["审计"]),
    # 健康检查
    ("backend.api.v1.health", "/health", ["健康检查"]),
]


def _include(
    parent: APIRouter,
    module_path: str,
    prefix: str,
    tags: list[str],
    *,
    required: bool,
) -> bool:
    """兼容旧调用方式的薄封装（真正的实现在 ``_loader``）。"""
    if required:
        return include_required(parent, module_path, prefix, tags)
    return include_optional(parent, module_path, prefix, tags)


router = APIRouter()

for _path, _prefix, _tags in CORE_ROUTERS:
    include_required(router, _path, _prefix, _tags)

for _path, _prefix, _tags in EXTRA_ROUTERS:
    include_optional(router, _path, _prefix, _tags)

logger.info(f"API 模块加载完成：{summary()}")

__all__ = [
    "CORE_ROUTERS",
    "EXTRA_ROUTERS",
    "LOADED",
    "SKIPPED",
    "_include",
    "router",
]
