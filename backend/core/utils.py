import os, magic, bleach, io
from pathlib import Path
from fastapi import HTTPException
from PIL import Image
from backend.core.config import settings

def validate_file_type(filename: str, file_stream):
    header = file_stream.read(2048)
    file_stream.seek(0)
    mime = magic.from_buffer(header, mime=True)
    allowed = [
        "image/jpeg","image/png","image/gif","application/pdf",
        "video/mp4","audio/mpeg","text/plain",
        "application/zip","application/x-rar-compressed",
        "application/msword",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/vnd.ms-excel",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "application/vnd.ms-powerpoint",
        "application/vnd.openxmlformats-officedocument.presentationml.presentation"
    ]
    if mime not in allowed:
        raise HTTPException(400, f"文件类型不允许: {mime}")

def sanitize_filename(filename: str) -> str:
    name = os.path.basename(filename)
    name = "".join(c for c in name if c.isalnum() or c in "._- ")
    return name if name else "unnamed"

def sanitize_html_bleach(text: str) -> str:
    return bleach.clean(text)

def generate_thumbnail(file_path: Path, size: tuple[int,int] = (200,200)) -> bytes:
    """生成缩略图并返回 JPEG bytes"""
    img = Image.open(file_path)
    img.thumbnail(size, Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=80)
    buf.seek(0)
    return buf.read()
