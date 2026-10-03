"""用户头像接口（可拆卸扩展）。

挂载在 ``/api/v1/auth`` 下：

- ``POST   /auth/avatar``            上传/更新当前用户头像
- ``GET    /auth/avatar/{user_id}``  读取指定用户头像
- ``DELETE /auth/avatar``            删除当前用户头像

把本文件删掉不会影响注册登录，只是 ``UserOut.avatar_url`` 永远为 null
（``backend.services.avatar`` 的磁盘检查会自然返回 None）。
"""

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.database import get_db
from backend.core.security import get_current_user
from backend.models.user import User
from backend.schemas.common import Message
from backend.schemas.user import AvatarOut
from backend.services import avatar as avatar_service

router = APIRouter()


@router.post("/avatar", response_model=AvatarOut)
async def upload_avatar(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """上传/更新当前用户头像（PNG / JPEG / GIF / WebP，最大 2MB）。"""
    content = await file.read()
    try:
        filename = avatar_service.save_avatar(current_user.id, content, file.content_type)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None

    current_user.avatar = filename
    db.add(current_user)
    await db.commit()
    return AvatarOut(avatar_url=f"/api/v1/auth/avatar/{current_user.id}")


@router.get("/avatar/{user_id}")
async def get_avatar(user_id: int, _: User = Depends(get_current_user)):
    """读取指定用户的头像（需要登录）。"""
    path = avatar_service.find_avatar(user_id)
    if path is None:
        raise HTTPException(status_code=404, detail="该用户还没有上传头像")
    return FileResponse(
        path,
        headers={
            "Cache-Control": "public, max-age=300",
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.delete("/avatar", response_model=Message)
async def delete_avatar(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """删除当前用户头像。"""
    avatar_service.remove_avatar(current_user.id)
    current_user.avatar = None
    db.add(current_user)
    await db.commit()
    return Message(message="头像已删除")
