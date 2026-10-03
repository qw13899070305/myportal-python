"""文件上传接口（可拆卸扩展）。

``POST /files/upload`` —— 扩展名 + 魔数双重校验，流式落盘并限制总大小。

把本文件删掉，文件列表/下载/预览都照常工作，只是不能再上传。
"""

from __future__ import annotations

import mimetypes
import uuid

import aiofiles
from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Request,
    UploadFile,
    status,
)
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.v1.file_common import (
    safe_original_name,
    validate_extension,
    validate_magic,
)
from backend.core.config import settings
from backend.core.database import get_db
from backend.core.logger import logger
from backend.core.security import get_current_user
from backend.core.utils import format_size, utcnow
from backend.models.file import FileItem
from backend.models.user import User
from backend.schemas.file import FileOut
from backend.services.audit import safe_log_action

router = APIRouter()


@router.post("/upload", response_model=FileOut, status_code=status.HTTP_201_CREATED)
async def upload_file(
    request: Request,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """上传文件。"""
    if not file.filename:
        raise HTTPException(status_code=400, detail="文件名不能为空")

    original_name = safe_original_name(file.filename)
    ext = validate_extension(original_name)

    # 128 字节足够覆盖：zip / Office 前缀、MP3 的 ID3 头、ISO-BMFF 的
    # ``ftyp`` + 主品牌 + 兼容品牌列表，以及 AZW3/MOBI 放在第 60 字节的
    # PalmDB 标识（``BOOKMOBI``）
    header = await file.read(128)
    validate_magic(ext, header)
    await file.seek(0)

    upload_dir = settings.UPLOAD_DIR
    upload_dir.mkdir(parents=True, exist_ok=True)

    stored_name = f"{uuid.uuid4().hex}{ext}"
    target = upload_dir / stored_name

    total = 0
    try:
        async with aiofiles.open(target, "wb") as out:
            while chunk := await file.read(1024 * 1024):
                total += len(chunk)
                if total > settings.MAX_UPLOAD_SIZE:
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail=(
                            f"文件大小超出限制（最大 {format_size(settings.MAX_UPLOAD_SIZE)}）"
                        ),
                    )
                await out.write(chunk)
    except Exception:
        # 任何失败都不能留下半个文件
        target.unlink(missing_ok=True)
        raise

    if total == 0:
        target.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail="不能上传空文件")

    item = FileItem(
        name=original_name,
        stored_name=stored_name,
        size=total,
        content_type=(
            file.content_type
            or mimetypes.guess_type(original_name)[0]
            or "application/octet-stream"
        ),
        uploader_id=current_user.id,
        upload_time=utcnow(),
    )
    db.add(item)
    await db.commit()

    await safe_log_action(
        db,
        action="file_upload",
        user_id=current_user.id,
        detail=f"{original_name} ({total} 字节)",
        request=request,
    )
    logger.info(f"用户 {current_user.username} 上传文件 {original_name} ({total} 字节)")
    return item
