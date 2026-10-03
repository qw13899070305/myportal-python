"""前端静态资源挂载（可拆卸扩展）。

把 Vue 的构建产物挂到根路径，并处理 history 路由的深层链接回退。
摘掉这个模块，``main.py`` 会退化成只暴露 API 与 ``/`` 提示页。
"""

from __future__ import annotations

import re
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from backend.core.config import BASE_DIR, settings
from backend.core.logger import logger

#: 形如 logo.png / app.abc123.js 的请求视为静态资源，找不到就返回真正的 404
_LOOKS_LIKE_ASSET = re.compile(r"\.[A-Za-z0-9]{1,8}$")

#: 这些前缀属于后端（API / 实时通信），**不能**回退到 index.html。
#: 否则写错的接口路径会返回 200 + HTML，前端只会看到 JSON 解析失败，
#: 手机上根本查不出问题；HEAD 请求也会被静态回退吞掉。
_BACKEND_PREFIXES = ("api/", "ws/")

#: 按顺序查找前端构建产物
STATIC_CANDIDATES: tuple[Path, ...] = (
    BASE_DIR / "frontend" / "dist",
    BASE_DIR / "backend" / "static",
)


class SPAStaticFiles(StaticFiles):
    """支持前端 history 路由的静态文件服务。

    前端使用 ``createWebHistory()``，用户刷新 ``/articles/1`` 这类深层链接时
    服务端并不存在对应文件，这里回退到 ``index.html`` 交给前端路由处理；
    带扩展名的资源请求仍然返回真正的 404。
    """

    async def get_response(self, path: str, scope):
        try:
            return await super().get_response(path, scope)
        except StarletteHTTPException as exc:
            if (
                exc.status_code == 404
                and not _LOOKS_LIKE_ASSET.search(path)
                and not path.startswith(_BACKEND_PREFIXES)
            ):
                return await super().get_response("index.html", scope)
            raise


def find_static_dir(
    candidates: tuple[Path, ...] = STATIC_CANDIDATES,
) -> Path | None:
    """返回第一个含有 index.html 的目录。"""
    for candidate in candidates:
        if (candidate / "index.html").is_file():
            return candidate
    return None


def mount_frontend(app: FastAPI, candidates: tuple[Path, ...] = STATIC_CANDIDATES) -> bool:
    """挂载前端构建产物；没有构建产物时注册一个提示用的根路由。"""
    static_dir = find_static_dir(candidates)
    if static_dir is not None:
        app.mount("/", SPAStaticFiles(directory=static_dir, html=True), name="static")
        logger.info(f"已挂载前端静态资源: {static_dir}")
        return True

    @app.get("/", tags=["健康检查"])
    async def root():
        return {
            "message": f"{settings.APP_NAME} 后端服务运行中（前端未构建）",
            "docs": "/docs",
        }

    return False
