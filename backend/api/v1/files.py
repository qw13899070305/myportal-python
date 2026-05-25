import os, mimetypes, io, re, uuid
from pathlib import Path
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query, Request
from fastapi.responses import FileResponse, StreamingResponse, HTMLResponse, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from backend.core.database import get_db
from backend.core.auth import get_current_user, RoleChecker
from backend.core.config import settings
from backend.core.utils import validate_file_type, sanitize_filename, generate_thumbnail
from backend.models.file import FileItem
from backend.services.preview import (
    get_file_path, preview_word, preview_excel, preview_ppt, preview_pdf_page, get_pdf_page_count
)
from PIL import Image, ImageDraw, ImageFont

router = APIRouter(prefix="/files", tags=["文件"])
UPLOAD_DIR = settings.UPLOAD_DIR
UPLOAD_DIR.mkdir(exist_ok=True)
settings.PREVIEW_TEMP_DIR.mkdir(exist_ok=True)
(UPLOAD_DIR / "avatars").mkdir(exist_ok=True)

def parse_range_header(range_header: str, file_size: int) -> tuple[int, int]:
    match = re.match(r'bytes=(\d+)-(\d*)', range_header)
    if not match:
        raise HTTPException(416, "无效的 Range 请求")
    start = int(match.group(1))
    end_str = match.group(2)
    end = int(end_str) if end_str else file_size - 1
    if start >= file_size or end >= file_size:
        raise HTTPException(416, "Range 超出文件范围")
    return start, end

def range_stream(file_path: Path, start: int, end: int, chunk_size: int = 8192):
    with open(file_path, "rb") as f:
        f.seek(start)
        remaining = end - start + 1
        while remaining > 0:
            chunk = f.read(min(chunk_size, remaining))
            if not chunk:
                break
            yield chunk
            remaining -= len(chunk)

@router.post("/upload")
async def upload(file: UploadFile = File(..., max_size=100*1024*1024),
                 user=Depends(RoleChecker(["author","admin","super_admin"])),
                 db: AsyncSession = Depends(get_db)):
    validate_file_type(file.filename, file.file)
    safe_name = f"{uuid.uuid4().hex}{os.path.splitext(sanitize_filename(file.filename))[1]}"
    file_path = UPLOAD_DIR / safe_name
    content = await file.read()
    file_path.write_bytes(content)
    item = FileItem(name=file_path.name, size=len(content), uploader_id=user.id)
    db.add(item)
    await db.commit()
    return {"id": item.id, "filename": file_path.name}

@router.get("/download/{filename}")
async def download(filename: str, _=Depends(RoleChecker(["admin","super_admin"]))):
    safe_name = os.path.basename(filename)
    if safe_name != filename:
        raise HTTPException(400, "非法文件名")
    fp = UPLOAD_DIR / safe_name
    if not fp.exists():
        raise HTTPException(404)
    return FileResponse(fp, filename=safe_name)

@router.get("/avatar/{filename}")
async def get_avatar(filename: str):
    # ✅ 修复路径穿越漏洞（代码放在函数内部）
    safe_name = os.path.basename(filename)
    if safe_name != filename:
        raise HTTPException(400, "非法文件名")
    fp = UPLOAD_DIR / "avatars" / safe_name
    if not fp.exists():
        raise HTTPException(404)
    return FileResponse(fp)

@router.get("/preview/{file_id}")
async def preview_file(file_id: int, request: Request,
                       db: AsyncSession = Depends(get_db),
                       user=Depends(get_current_user)):
    result = await db.execute(select(FileItem).where(FileItem.id == file_id, FileItem.deleted == False))
    file_item = result.scalar_one_or_none()
    if not file_item:
        raise HTTPException(404, "文件不存在或已删除")
    file_path = UPLOAD_DIR / file_item.name
    if not file_path.exists():
        raise HTTPException(404, "文件不存在")
    return FileResponse(file_path)
