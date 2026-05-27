import os
import uuid
import aiofiles
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, status
from backend.core.config import settings
from backend.core.security import get_current_user
from backend.models.user import User

router = APIRouter()

ALLOWED_MAGIC = {
    b'\x89PNG\r\n\x1a\n': 'png',
    b'\xff\xd8\xff': 'jpg',
    b'GIF87a': 'gif',
    b'GIF89a': 'gif',
    b'%PDF': 'pdf',
    b'PK\x03\x04': 'zip',  # 包括 docx, xlsx
}

def get_ext(data: bytes) -> str | None:
    for magic, ext in ALLOWED_MAGIC.items():
        if data.startswith(magic):
            return ext
    return None

@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user)
):
    # 文件大小提前拒绝
    if file.size and file.size > settings.MAX_UPLOAD_SIZE:
        raise HTTPException(status_code=413, detail="文件大小超出限制")

    header = await file.read(8)
    ext = get_ext(header)
    if not ext:
        raise HTTPException(status_code=400, detail="不支持的文件类型")
    await file.seek(0)

    safe_name = f"{uuid.uuid4()}.{ext}"
    upload_dir = Path(settings.UPLOAD_DIR).resolve()
    upload_dir.mkdir(parents=True, exist_ok=True)
    file_path = (upload_dir / safe_name).resolve()
    if not str(file_path).startswith(str(upload_dir)):
        raise HTTPException(status_code=400, detail="非法文件路径")

    total = 0
    async with aiofiles.open(file_path, 'wb') as f:
        while chunk := await file.read(1024 * 1024):
            total += len(chunk)
            if total > settings.MAX_UPLOAD_SIZE:
                await f.close()
                os.remove(file_path)
                raise HTTPException(status_code=413, detail="文件大小超出限制")
            await f.write(chunk)

    return {
        "code": 200,
        "message": "上传成功",
        "data": {"filename": safe_name, "original_name": file.filename, "size": total}
    }

@router.get("/list")
async def list_files(current_user: User = Depends(get_current_user)):
    upload_dir = Path(settings.UPLOAD_DIR).resolve()
    if not upload_dir.exists():
        return {"code": 200, "data": []}
    return {"code": 200, "data": os.listdir(upload_dir)}