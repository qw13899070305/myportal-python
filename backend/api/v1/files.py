import os, mimetypes, io, re
import uuid
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
    get_file_path, preview_word, preview_excel, preview_ppt,
    preview_pdf_page, get_pdf_page_count
)
from PIL import Image, ImageDraw, ImageFont

router = APIRouter(prefix="/files", tags=["文件"])
UPLOAD_DIR = settings.UPLOAD_DIR
UPLOAD_DIR.mkdir(exist_ok=True)
settings.PREVIEW_TEMP_DIR.mkdir(exist_ok=True)
(UPLOAD_DIR / "avatars").mkdir(exist_ok=True)

def parse_range_header(range_header: str, file_size: int) -> tuple[int, int]:
    match = re.match(r'bytes=(\d+)-(\d*)', range_header)
    if not match: raise HTTPException(416, "无效的 Range 请求")
    start = int(match.group(1))
    end_str = match.group(2)
    end = int(end_str) if end_str else file_size - 1
    if start >= file_size or end >= file_size: raise HTTPException(416, "Range 超出文件范围")
    return start, end

def range_stream(file_path: Path, start: int, end: int, chunk_size: int = 8192):
    with open(file_path, "rb") as f:
        f.seek(start)
        remaining = end - start + 1
        while remaining > 0:
            chunk = f.read(min(chunk_size, remaining))
            if not chunk: break
            yield chunk
            remaining -= len(chunk)

@router.post("/upload")
async def upload(file: UploadFile = File(..., max_size=100*1024*1024), user=Depends(RoleChecker(["author","admin","super_admin"])), db: AsyncSession = Depends(get_db)):
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
    fp = UPLOAD_DIR / filename
    if not fp.exists(): raise HTTPException(404)
    return FileResponse(fp, filename=filename)

@router.get("/avatar/{filename}")
    safe_name = os.path.basename(filename)
    if safe_name != filename:
        raise HTTPException(400, "非法文件名")
async def get_avatar(filename: str):
    fp = UPLOAD_DIR / "avatars" / filename
    if not fp.exists(): raise HTTPException(404)
    return FileResponse(fp)

@router.get("/preview/{file_id}")
async def preview_file(file_id: int, request: Request, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    result = await db.execute(select(FileItem).where(FileItem.id == file_id, FileItem.deleted == False))
    file_item = result.scalar_one_or_none()
    if not file_item: raise HTTPException(404, "文件不存在或已删除")
    file_path = UPLOAD_DIR / file_item.name
    if not file_path.exists(): raise HTTPException(404, "物理文件丢失")
    ext = file_path.suffix.lower()

    if ext in (".docx", ".doc"): return HTMLResponse(content=preview_word(file_path))
    elif ext in (".xlsx", ".xls"): return HTMLResponse(content=preview_excel(file_path))
    elif ext in (".pptx", ".ppt"): return HTMLResponse(content=preview_ppt(file_path))
    elif ext == ".pdf":
        page_count = get_pdf_page_count(file_path)
        base = f"/api/v1/files/preview/{file_id}/page?num="
        imgs = "".join(f'<img src="{base}{p}" style="width:100%;margin-bottom:20px;" />' for p in range(1, page_count+1))
        return HTMLResponse(content=f"<html><head><meta charset='utf-8'></head><body style='background:#f0f0f0;text-align:center;'>{imgs}</body></html>")
    elif ext in (".jpg", ".jpeg", ".png", ".gif"):
        img = Image.open(file_path)
        draw = ImageDraw.Draw(img)
        try: font = ImageFont.truetype("arial.ttf", 20)
        except: font = ImageFont.load_default()
        draw.text((10,10), f"{user.username} {datetime.now():%Y-%m-%d %H:%M}", fill=(255,255,255,128), font=font)
        buf = io.BytesIO(); img.save(buf, format=img.format or 'JPEG'); buf.seek(0)
        return Response(content=buf.read(), media_type=f"image/{img.format.lower()}")
    elif ext in (".mp4", ".avi", ".mov", ".mkv", ".mp3", ".wav", ".flac", ".ogg"):
        file_size = file_path.stat().st_size
        range_header = request.headers.get("range")
        media_type = mimetypes.guess_type(file_item.name)[0] or "application/octet-stream"
        if range_header:
            start, end = parse_range_header(range_header, file_size)
            return StreamingResponse(range_stream(file_path, start, end), status_code=206, media_type=media_type,
                headers={"Content-Range": f"bytes {start}-{end}/{file_size}", "Accept-Ranges": "bytes", "Content-Length": str(end-start+1), "Content-Disposition": "inline"})
        else:
            return FileResponse(file_path, media_type=media_type, headers={"Accept-Ranges": "bytes", "Content-Disposition": "inline"})
    else:
        media_type = mimetypes.guess_type(file_item.name)[0] or "application/octet-stream"
        return FileResponse(file_path, media_type=media_type, headers={"Content-Disposition": "inline"})

@router.get("/preview/{file_id}/page")
async def pdf_page(file_id: int, num: int = Query(...), db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    result = await db.execute(select(FileItem).where(FileItem.id == file_id, FileItem.deleted == False))
    file_item = result.scalar_one_or_none()
    if not file_item: raise HTTPException(404)
    return Response(content=preview_pdf_page(UPLOAD_DIR / file_item.name, num), media_type="image/jpeg")

@router.get("/thumbnail/{file_id}")
async def thumbnail(file_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(FileItem).where(FileItem.id == file_id, FileItem.deleted == False))
    file_item = result.scalar_one_or_none()
    if not file_item: raise HTTPException(404)
    file_path = UPLOAD_DIR / file_item.name
    if not file_path.exists(): raise HTTPException(404)
    if file_path.suffix.lower() not in (".jpg", ".jpeg", ".png", ".gif"):
        raise HTTPException(400, "仅支持图片缩略图")
    thumb = generate_thumbnail(file_path)
    return Response(content=thumb, media_type="image/jpeg")

@router.get("/")
async def list_files(page: int=1, limit: int=20, sort: str="time", search: str="", db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    q = select(FileItem).where(FileItem.deleted == False)
    if search:
        q = q.where(FileItem.name.ilike(f"%{search}%"))
    q = q.order_by(FileItem.name) if sort == "name" else q.order_by(FileItem.upload_time.desc())
    total = await db.scalar(select(func.count()).select_from(q.subquery()))
    items = await db.execute(q.offset((page-1)*limit).limit(limit))
    files = items.scalars().all()
    return {"total": total, "items": [{"id":f.id,"name":f.name,"size":f.size,"time":f.upload_time,"preview_url":f"/api/v1/files/preview/{f.id}","thumbnail_url":f"/api/v1/files/thumbnail/{f.id}" if f.name.split('.')[-1].lower() in ('jpg','jpeg','png','gif') else None} for f in files]}

@router.delete("/{file_id}")
async def delete_file(file_id: int, _=Depends(RoleChecker(["admin","super_admin"])), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(FileItem).where(FileItem.id == file_id, FileItem.deleted == False))
    item = result.scalar_one_or_none()
    if not item: raise HTTPException(404, "文件不存在")
    item.deleted = True
    db.add(TrashItem(file_id=item.id, name=item.name, size=item.size))
    await db.commit()
    return {"msg": "已移入回收站"}
@router.put("/rename/{file_id}")
async def rename_file(file_id: int, new_name: str = Query(...), _=Depends(RoleChecker(["admin","super_admin"])), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(FileItem).where(FileItem.id == file_id, FileItem.deleted == False))
    item = result.scalar_one_or_none()
    if not item: raise HTTPException(404, "文件不存在")
    old_path = UPLOAD_DIR / item.name
    new_path = UPLOAD_DIR / new_name
    if new_path.exists(): raise HTTPException(400, "文件名已存在")
    old_path.rename(new_path)
    item.name = new_name
    await db.commit()
    return {"msg": "已重命名"}
@router.get("/download-folder")
async def download_folder(filenames: list[str] = Query(...), _=Depends(RoleChecker(["admin","super_admin"]))):
    import zipfile
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for name in filenames:
            fp = UPLOAD_DIR / name
            if fp.exists(): zf.write(fp, arcname=name)
    buf.seek(0)
    return StreamingResponse(buf, media_type="application/zip", headers={"Content-Disposition": "attachment; filename=folder.zip"})
