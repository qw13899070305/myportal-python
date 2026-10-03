"""文件分享链接。

- 分享码随机生成，密码以 Argon2 哈希存储（不再保存明文）
- 过期后自动置为失效
- 下载走 ``/api/v1/share/download/{code}``，无需登录即可访问
"""

import secrets
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.config import settings
from backend.core.database import get_db
from backend.core.logger import logger
from backend.core.password import get_password_hash, verify_password
from backend.core.security import get_current_user, is_admin
from backend.core.utils import utcnow
from backend.models.file import FileItem
from backend.models.share import ShareLink
from backend.models.user import User
from backend.schemas.common import Message
from backend.schemas.site import ShareAccessOut, ShareCreate, ShareOut
from backend.services.audit import safe_log_action

router = APIRouter()


async def _resolve_file(db: AsyncSession, payload: ShareCreate, user: User) -> FileItem:
    """定位要分享的文件（校验权限）。"""
    item: FileItem | None = None
    if payload.file_id is not None:
        item = await db.get(FileItem, payload.file_id)
    elif payload.filename:
        # 兼容旧接口：按磁盘文件名查找
        item = await db.scalar(select(FileItem).where(FileItem.stored_name == payload.filename))
    if item is None or item.deleted:
        raise HTTPException(status_code=404, detail="文件不存在")
    if item.uploader_id != user.id and not is_admin(user):
        raise HTTPException(status_code=403, detail="无权分享该文件")
    return item


@router.post("/create", response_model=ShareOut)
async def create(
    request: Request,
    data: ShareCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """创建分享链接。"""
    item = await _resolve_file(db, data, user)

    hours = data.expire_hours or settings.SHARE_LINK_EXPIRE_HOURS
    code = secrets.token_urlsafe(12)[:24]
    link = ShareLink(
        file_path=item.stored_name,
        code=code,
        password=get_password_hash(data.password) if data.password else None,
        expire_at=utcnow() + timedelta(hours=hours),
        created_by=user.id,
    )
    db.add(link)
    await db.commit()

    await safe_log_action(
        db,
        action="share_create",
        user_id=user.id,
        detail=f"{item.name} -> {code}",
        request=request,
    )
    # password 字段仅用于兼容旧前端的响应结构，这里回显请求里的明文
    return ShareOut(
        code=code,
        expire_at=link.expire_at,
        has_password=bool(link.password),
        password=data.password,
    )


@router.get("/mine", response_model=list[ShareOut])
async def my_shares(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """我创建的分享链接。"""
    result = await db.execute(
        select(ShareLink)
        .where(ShareLink.created_by == user.id)
        .order_by(ShareLink.created_at.desc())
    )
    return [
        ShareOut(code=link.code, expire_at=link.expire_at, has_password=bool(link.password))
        for link in result.scalars().all()
    ]


async def _load_link(db: AsyncSession, code: str) -> ShareLink:
    link = await db.scalar(select(ShareLink).where(ShareLink.code == code))
    if link is None or not link.is_active:
        raise HTTPException(status_code=404, detail="分享不存在或已失效")
    if link.is_expired():
        link.is_active = False
        db.add(link)
        await db.commit()
        raise HTTPException(status_code=410, detail="分享已过期")
    return link


@router.get("/access/{code}", response_model=ShareAccessOut)
async def access(
    code: str,
    password: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
):
    """校验分享码（必要时校验密码），返回下载地址。"""
    link = await _load_link(db, code)

    if link.password and not verify_password(password or "", link.password):
        raise HTTPException(status_code=403, detail="密码错误")

    item = await db.scalar(select(FileItem).where(FileItem.stored_name == link.file_path))
    filename = item.name if item else link.file_path
    return ShareAccessOut(filename=filename, download_url=f"/api/v1/share/download/{code}")


@router.api_route("/download/{code}", methods=["GET", "HEAD"])
async def download(
    code: str,
    password: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
):
    """通过分享码下载文件（无需登录，但需要正确的密码）。"""
    link = await _load_link(db, code)

    if link.password and not verify_password(password or "", link.password):
        raise HTTPException(status_code=403, detail="密码错误")

    item = await db.scalar(select(FileItem).where(FileItem.stored_name == link.file_path))
    if item is None or item.deleted:
        raise HTTPException(status_code=404, detail="文件已被删除")

    base = settings.UPLOAD_DIR.resolve()
    path = (base / item.stored_name).resolve()
    if not path.is_relative_to(base) or not path.is_file():
        raise HTTPException(status_code=404, detail="文件已丢失")

    return FileResponse(
        path,
        filename=item.name,
        media_type=item.content_type or "application/octet-stream",
    )


@router.delete("/{code}", response_model=Message)
async def revoke(
    code: str,
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """取消分享。"""
    link = await db.scalar(select(ShareLink).where(ShareLink.code == code))
    if link is None:
        raise HTTPException(status_code=404, detail="分享不存在")
    if link.created_by != user.id and not is_admin(user):
        raise HTTPException(status_code=403, detail="无权操作该分享")

    await db.delete(link)
    await db.commit()
    await safe_log_action(db, action="share_revoke", user_id=user.id, detail=code, request=request)
    logger.info(f"用户 {user.username} 取消分享 {code}")
    return Message(message="分享已取消")
