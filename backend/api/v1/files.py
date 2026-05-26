from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, status
from fastapi.responses import FileResponse
from pathlib import Path
from backend.core.config import settings
from backend.core.security import get_current_user
from backend.models.user import User
import aiofiles
import uuid

router = APIRouter()

ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "gif", "pdf", "doc", "docx", "xls", "xlsx", "txt", "mp4", "avi"}

async def validate_file_type(file: UploadFile):
    # 读取文件头检测真实类型（简化版，实际应使用 filetype 库）
    content = await file.read(2048)
    await file.seek(0)
    # 简单检查常见文件头
    if content.startswith(b'\x89PNG'):
        return True
    if content.startswith(b'\xff\xd8\xff'):
        return True
    if content.startswith(b'GIF8'):
        return True
    if content.startswith(b'%PDF'):
        return True
    # 对于其他类型，回退到扩展名检查
    ext = Path(file.filename).suffix.lower().lstrip(".")
    if ext in ALLOWED_EXTENSIONS:
        return True
    return False

@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user)
):
    if not file.filename:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="文件名不能为空")

    # 文件大小限制
    if file.size and file.size > settings.MAX_UPLOAD_SIZE:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="文件大小超过限制")

    # 类型检查
    if not await validate_file_type(file):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="不支持的文件类型")

    # 生成安全文件名
    ext = Path(file.filename).suffix.lower()
    safe_filename = f"{uuid.uuid4().hex}{ext}"
    upload_dir = Path(settings.UPLOAD_DIR) / str(current_user.id)
    upload_dir.mkdir(parents=True, exist_ok=True)
    file_path = upload_dir / safe_filename

    # 异步写入文件
    async with aiofiles.open(file_path, 'wb') as out_file:
        while chunk := await file.read(8192):
            await out_file.write(chunk)

    # 返回文件信息
    return {
        "filename": safe_filename,
        "original_name": file.filename,
        "size": file_path.stat().st_size,
        "url": f"/api/v1/files/{current_user.id}/{safe_filename}"
    }

@router.get("/{user_id}/{filename}")
async def get_file(user_id: int, filename: str):
    file_path = Path(settings.UPLOAD_DIR) / str(user_id) / filename
    if not file_path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="文件不存在")
    return FileResponse(file_path)