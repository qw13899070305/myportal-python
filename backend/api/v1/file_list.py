"""文件列表接口（可拆卸扩展）。

- ``GET /files/``            分页列表（普通用户只看自己的，管理员看全部）
- ``GET /files/categories``  每个分类的文件数（给客户端的分类标签用）
- ``GET /files/list``        上传目录下的文件名列表（兼容旧接口）
- ``GET /files/recent``      当前用户最近上传

分类规则在 :mod:`backend.core.filetypes`：按文件名实时派生，不存库。
``category`` 查询参数传的是**机器键**（``image`` / ``document`` …），
中文标签由客户端自己翻译。

**必须挂载在 ``GET /files/{file_id}`` 之前**，否则 ``categories`` / ``list`` /
``recent`` 会被当成路径参数解析而报 422。
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.config import settings
from backend.core.database import get_db
from backend.core.filetypes import (
    CATEGORY_OTHER,
    all_categories,
    category_of,
    extensions_of,
)
from backend.core.security import get_current_user, is_admin
from backend.models.file import FileItem
from backend.models.user import User
from backend.schemas.file import FileListOut, FileOut

router = APIRouter()


def _visibility(current_user: User, mine: bool) -> list:
    """权限范围：普通用户只看自己的，管理员默认看全部（``mine=1`` 可只看自己）。"""
    if mine or not is_admin(current_user):
        return [FileItem.uploader_id == current_user.id]
    return []


def _category_condition(category: str):
    """把分类键翻译成一个 SQL 条件。

    分类是派生出来的，所以在 SQL 里按扩展名匹配；``other`` 取反集
    （无扩展名或不在任何分类里的都算 other）。
    """
    if category == CATEGORY_OTHER:
        known = [ext for key in all_categories() for ext in extensions_of(key)]
        return ~or_(*[FileItem.name.ilike(f"%{ext}") for ext in known])

    extensions = extensions_of(category)
    if not extensions:
        raise HTTPException(
            status_code=400,
            detail=f"未知的分类 {category}，可用：{'、'.join(all_categories())}",
        )
    return or_(*[FileItem.name.ilike(f"%{ext}") for ext in extensions])


@router.get("/", response_model=FileListOut)
async def list_files(
    search: str = Query("", max_length=100),
    category: str = Query("", max_length=20, description="分类键，空表示全部"),
    page: int = Query(1, ge=1),
    size: int = Query(settings.PAGE_SIZE_DEFAULT, ge=1, le=settings.PAGE_SIZE_MAX),
    limit: int | None = Query(default=None, ge=1, le=settings.PAGE_SIZE_MAX),
    mine: bool = Query(default=False, description="只看自己上传的文件"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """文件列表（支持分类筛选）。"""
    if limit is not None:  # 兼容旧前端的 limit 参数
        size = limit

    conditions = [FileItem.deleted.is_(False), *_visibility(current_user, mine)]
    if search.strip():
        pattern = f"%{search.strip()}%"
        conditions.append(or_(FileItem.name.ilike(pattern), FileItem.content_type.ilike(pattern)))
    if category.strip():
        conditions.append(_category_condition(category.strip().lower()))

    total = await db.scalar(select(func.count()).select_from(FileItem).where(*conditions)) or 0
    result = await db.execute(
        select(FileItem)
        .where(*conditions)
        .order_by(FileItem.upload_time.desc(), FileItem.id.desc())
        .offset((page - 1) * size)
        .limit(size)
    )
    return FileListOut(total=total, items=result.scalars().all())


@router.get("/categories")
async def category_counts(
    search: str = Query("", max_length=100),
    mine: bool = Query(default=False, description="只统计自己上传的文件"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """每个分类的文件数（含 ``all`` 总数），供客户端的分类标签显示徽标。

    统计口径与 ``GET /files/`` 完全一致（同样的权限与搜索条件），
    这样"标签上的数字"和"点进去看到的列表"不会对不上。
    """
    conditions = [FileItem.deleted.is_(False), *_visibility(current_user, mine)]
    if search.strip():
        pattern = f"%{search.strip()}%"
        conditions.append(or_(FileItem.name.ilike(pattern), FileItem.content_type.ilike(pattern)))

    # 分类是派生的，统计放在 Python 里做：SQL 里再写一遍规则就等于两处维护
    names = (await db.execute(select(FileItem.name).where(*conditions))).scalars().all()

    counts = {key: 0 for key in all_categories()}
    for name in names:
        counts[category_of(name)] += 1

    return {
        "total": len(names),
        "items": [{"key": key, "count": counts[key]} for key in all_categories()],
    }


@router.get("/list")
async def list_filenames(current_user: User = Depends(get_current_user)):
    """兼容旧接口：返回上传目录下的文件名列表。"""
    upload_dir = settings.UPLOAD_DIR.resolve()
    if not upload_dir.is_dir():
        return {"code": 200, "data": []}
    names = sorted(p.name for p in upload_dir.iterdir() if p.is_file())
    return {"code": 200, "data": names}


@router.get("/recent", response_model=list[FileOut])
async def recent_files(
    limit: int = Query(5, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """当前用户最近上传的文件（个人中心用）。"""
    result = await db.execute(
        select(FileItem)
        .where(FileItem.deleted.is_(False), FileItem.uploader_id == current_user.id)
        .order_by(FileItem.upload_time.desc(), FileItem.id.desc())
        .limit(limit)
    )
    return result.scalars().all()
