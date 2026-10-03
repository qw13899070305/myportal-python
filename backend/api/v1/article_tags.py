"""文章标签接口（可拆卸扩展）。

``GET /articles/tags`` —— 全部标签名，供前端做筛选下拉。

**必须挂载在 ``GET /articles/{article_id}`` 之前**，否则 ``tags``
会被当成路径参数解析而报 422。
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.database import get_db
from backend.models.article import Tag

router = APIRouter()


@router.get("/tags", response_model=list[str])
async def list_tags(db: AsyncSession = Depends(get_db)):
    """全部标签（按名称排序）。"""
    result = await db.execute(select(Tag.name).order_by(Tag.name))
    return list(result.scalars().all())
