import os, uuid, mimetypes
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import FileResponse, HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from backend.core.database import get_db
from backend.core.auth import get_current_user, RoleChecker
from backend.core.config import settings
from backend.core.utils import sanitize_filename
from backend.models.file import FileItem

router = APIRouter(prefix="/files", tags=["文件"])
UPLOAD_DIR = settings.UPLOAD_DIR
UPLOAD_DIR.mkdir(exist_ok=True)
settings.PREVIEW_TEMP_DIR.mkdir(exist_ok=True)
(UPLOAD_DIR / "avatars").mkdir(exist_ok=True)

MAGIC_SIGS = {
    b'\x89PNG': 'image/png',
    b'\xff\xd8\xff': 'image/jpeg',
    b'GIF8': 'image/gif',
    b'%PDF': 'application/pdf',
    b'PK\x03\x04': 'zip/office',
    b'\xd0\xcf\x11\xe0': 'ole/office',
}

def check_magic(content: bytes, expected_mime: str = None) -> bool:
    for magic, mime_hint in MAGIC_SIGS.items():
        if content.startswith(magic):
            if expected_mime is None:
                return True
            if mime_hint == 'zip/office':
                return expected_mime in [
                    'application/zip',
                    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                    'application/vnd.openxmlformats-officedocument.presentationml.presentation'
                ]
            if mime_hint == 'ole/office':
                return expected_mime in [
                    'application/msword',
                    'application/vnd.ms-excel',
                    'application/vnd.ms-powerpoint'
                ]
            return expected_mime == mime_hint
    return False

def safe_filename(filename: str) -> str:
    return uuid.uuid4().hex + os.path.splitext(os.path.basename(filename))[1]

@router.post("/upload")
async def upload(file: UploadFile = File(..., max_size=50*1024*1024),  # ✅ 限制文件大小50MB
                 user=Depends(RoleChecker(["author","admin","super_admin"])),
                 db: AsyncSession = Depends(get_db)):
    head = await file.read(32)
    await file.seek(0)
    if not check_magic(head, file.content_type):
        raise HTTPException(400, "文件内容与类型不符")
    safe_name = safe_filename(file.filename)
    file_path = UPLOAD_DIR / safe_name
    content = await file.read()
    file_path.write_bytes(content)
    item = FileItem(name=file_path.name, size=len(content), uploader_id=user.id)
    db.add(item)
    await db.commit()
    return {"id": item.id, "filename": file_path.name}

@router.post("/upload-avatar")
async def upload_avatar(file: UploadFile = File(..., max_size=2*1024*1024),  # ✅ 限制头像大小2MB
                        user=Depends(get_current_user),
                        db: AsyncSession = Depends(get_db)):
    if file.content_type not in ["image/png", "image/jpeg", "image/gif"]:
        raise HTTPException(400, "仅支持 PNG/JPG/GIF")
    head = await file.read(32)
    await file.seek(0)
    if not check_magic(head, file.content_type):
        raise HTTPException(400, "文件内容不匹配")
    safe_name = f"avatar_{user.id}_{uuid.uuid4().hex}{os.path.splitext(file.filename)[1]}"
    file_path = UPLOAD_DIR / "avatars" / safe_name
    content = await file.read()
    file_path.write_bytes(content)
    user.avatar = safe_name
    db.add(user)
    await db.commit()
    return {"avatar": safe_name, "url": f"/api/v1/files/avatar/{safe_name}"}

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
    safe_name = os.path.basename(filename)
    if safe_name != filename:
        raise HTTPException(400, "非法文件名")
    fp = UPLOAD_DIR / "avatars" / safe_name
    if not fp.exists():
        raise HTTPException(404)
    return FileResponse(fp)

@router.get("/preview/{file_id}")
async def preview_file(file_id: int,
                       db: AsyncSession = Depends(get_db),
                       user=Depends(get_current_user)):
    result = await db.execute(select(FileItem).where(FileItem.id == file_id, FileItem.deleted == False))
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(404, "文件不存在")
    path = UPLOAD_DIR / item.name
    if not path.exists():
        raise HTTPException(404, "文件不存在")
    if path.suffix.lower() == ".pdf":
        return HTMLResponse(f"""
        <html><body style="margin:0">
        <iframe src="/static/pdfjs/web/viewer.html?file=/api/v1/files/download/{path.name}" width="100%" height="100%"></iframe>
        </body></html>""")
    return FileResponse(path)
