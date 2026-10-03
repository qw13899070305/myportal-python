"""文件接口的公共内核。

把「类型校验」和「权限/路径解析」抽出来，这样
:mod:`backend.api.v1.files`（增删改查）与
:mod:`backend.api.v1.file_preview`（在线预览）可以各自独立摘掉，
而不用复制粘贴这些规则。
"""

from __future__ import annotations

from pathlib import Path

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.config import settings
from backend.core.security import is_admin
from backend.core.utils import sanitize_filename
from backend.models.file import FileItem
from backend.models.user import User

# ---------------- 类型白名单 ----------------

TEXT_EXTENSIONS = {".txt", ".md", ".csv", ".json", ".log"}
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp"}
#: 手机相册默认格式：能上传/下载，但浏览器不能在线预览（预览会走兜底提示）
HEIC_EXTENSIONS = {".heic", ".heif"}
PDF_EXTENSIONS = {".pdf"}
WORD_EXTENSIONS = {".docx"}
EXCEL_EXTENSIONS = {".xlsx"}
PPT_EXTENSIONS = {".pptx"}
ARCHIVE_EXTENSIONS = {".zip"}
#: EPUB 是 zip 容器（和 Office 系共用 ``PK`` 魔数）
EPUB_EXTENSIONS = {".epub"}
#: AZW3 / MOBI 是 PalmDB 容器，魔数不在文件开头（见 ``_OFFSET_SIGNATURES``）
MOBI_EXTENSIONS = {".azw3", ".mobi"}
#: 电子书（预览扩展按这个大类走）
EBOOK_EXTENSIONS = EPUB_EXTENSIONS | MOBI_EXTENSIONS
#: Windows 帮助文件（编译后的 HTML 集合），魔数 ``ITSF`` 在文件开头
CHM_EXTENSIONS = {".chm"}
#: 手机录像 / 录音
VIDEO_EXTENSIONS = {".mp4", ".mov", ".3gp", ".m4v"}
AUDIO_EXTENSIONS = {".mp3", ".m4a", ".wav"}
#: 旧版 Office 只能上传/下载，不支持在线预览
LEGACY_OFFICE_EXTENSIONS = {".doc", ".xls", ".ppt"}

#: 魔数 -> 允许的扩展名集合
_MAGIC_SIGNATURES: tuple[tuple[bytes, set[str]], ...] = (
    (b"%PDF", PDF_EXTENSIONS),
    (b"\x89PNG\r\n\x1a\n", {".png"}),
    (b"\xff\xd8\xff", {".jpg", ".jpeg"}),
    (b"GIF87a", {".gif"}),
    (b"GIF89a", {".gif"}),
    (b"BM", {".bmp"}),
    (b"ITSF", CHM_EXTENSIONS),
    (
        b"PK\x03\x04",
        WORD_EXTENSIONS
        | EXCEL_EXTENSIONS
        | PPT_EXTENSIONS
        | ARCHIVE_EXTENSIONS
        | EPUB_EXTENSIONS,
    ),
    (b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1", LEGACY_OFFICE_EXTENSIONS),
)

#: 偏移型魔数：``(偏移, 魔数, 允许的扩展名)``。
#: PalmDB（AZW3/MOBI）的容器标识不在开头，而是在第 60 字节
_OFFSET_SIGNATURES: tuple[tuple[int, bytes, set[str]], ...] = (
    (60, b"BOOKMOBI", MOBI_EXTENSIONS),
    (60, b"TEXtREAd", MOBI_EXTENSIONS),
)

#: 通用 ISO-BMFF 品牌：同一个容器里音视频都可能，扩展名不必再细分
_BMFF_GENERIC_EXTENSIONS = VIDEO_EXTENSIONS | AUDIO_EXTENSIONS

#: ISO-BMFF（MP4 / MOV / 3GP / M4A / HEIC …）的品牌表。
#: 文件头第 4~8 字节固定是 ``ftyp``，第 8~12 字节是主品牌，
#: 之后每 4 字节一个兼容品牌。
_FTYP_BRANDS: dict[bytes, set[str]] = {
    # 手机照片原图：只认 heic/heif 这两个扩展名
    b"heic": HEIC_EXTENSIONS,
    b"heix": HEIC_EXTENSIONS,
    b"hevc": HEIC_EXTENSIONS,
    b"hevx": HEIC_EXTENSIONS,
    b"heim": HEIC_EXTENSIONS,
    b"heis": HEIC_EXTENSIONS,
    b"hevm": HEIC_EXTENSIONS,
    b"hevs": HEIC_EXTENSIONS,
    b"mif1": HEIC_EXTENSIONS,
    b"msf1": HEIC_EXTENSIONS,
    # 视频 / 音频容器
    b"isom": _BMFF_GENERIC_EXTENSIONS,
    b"iso2": _BMFF_GENERIC_EXTENSIONS,
    b"iso4": _BMFF_GENERIC_EXTENSIONS,
    b"iso5": _BMFF_GENERIC_EXTENSIONS,
    b"iso6": _BMFF_GENERIC_EXTENSIONS,
    b"mp41": _BMFF_GENERIC_EXTENSIONS,
    b"mp42": _BMFF_GENERIC_EXTENSIONS,
    b"avc1": _BMFF_GENERIC_EXTENSIONS,
    b"M4V ": _BMFF_GENERIC_EXTENSIONS,
    b"mmp4": _BMFF_GENERIC_EXTENSIONS,
    b"dash": _BMFF_GENERIC_EXTENSIONS,
    b"MSNV": _BMFF_GENERIC_EXTENSIONS,
    b"qt  ": _BMFF_GENERIC_EXTENSIONS,
    b"3gp4": _BMFF_GENERIC_EXTENSIONS,
    b"3gp5": _BMFF_GENERIC_EXTENSIONS,
    b"3gp6": _BMFF_GENERIC_EXTENSIONS,
    b"3g2a": _BMFF_GENERIC_EXTENSIONS,
    b"M4A ": _BMFF_GENERIC_EXTENSIONS,
    b"M4B ": _BMFF_GENERIC_EXTENSIONS,
    b"f4a ": _BMFF_GENERIC_EXTENSIONS,
}

#: 兼容旧接口 ``GET /files/list`` 使用的简化魔数表
LEGACY_ALLOWED_MAGIC = {
    b"\x89PNG\r\n\x1a\n": "png",
    b"\xff\xd8\xff": "jpg",
    b"GIF87a": "gif",
    b"GIF89a": "gif",
    b"%PDF": "pdf",
    b"PK\x03\x04": "zip",
}


def get_ext(data: bytes) -> str | None:
    """按魔数猜测扩展名（保留旧接口使用的函数）。"""
    for magic, ext in LEGACY_ALLOWED_MAGIC.items():
        if data.startswith(magic):
            return ext
    return None


def _iso_bmff_allowed(header: bytes) -> set[str] | None:
    """是 ISO-BMFF 容器就返回它允许的扩展名集合，否则返回 ``None``。

    兼容品牌也要看：手机录的视频主品牌常写成 ``isom``，真正的
    ``mp42`` 之类藏在后面的兼容品牌列表里。
    """
    if len(header) < 12 or header[4:8] != b"ftyp":
        return None

    brands = {header[8:12]}
    brands |= {header[i : i + 4] for i in range(16, len(header) - 3, 4)}

    allowed: set[str] = set()
    for brand in brands:
        allowed |= _FTYP_BRANDS.get(brand, set())
    return allowed


def _is_mp3(header: bytes) -> bool:
    """ID3 标签开头，或 MPEG 音频帧同步（11 个 1）。"""
    if header.startswith(b"ID3"):
        return True
    return len(header) >= 2 and header[0] == 0xFF and (header[1] & 0xE0) == 0xE0


def _is_wav(header: bytes) -> bool:
    """RIFF 容器且类型是 WAVE。"""
    return len(header) >= 12 and header[:4] == b"RIFF" and header[8:12] == b"WAVE"


# ---------------- 校验 ----------------


def safe_original_name(filename: str | None) -> str:
    """取基名并限制长度，避免路径穿越与超长文件名。"""
    name = sanitize_filename(filename or "")[:255]
    if not name or name in {".", ".."}:
        raise HTTPException(status_code=400, detail="文件名不合法")
    return name


def validate_extension(name: str) -> str:
    """扩展名必须在白名单里，返回规范化后的小写扩展名。"""
    ext = Path(name).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"不支持的文件类型 {ext or '(无扩展名)'}",
        )
    return ext


def validate_magic(ext: str, header: bytes) -> None:
    """校验文件头与扩展名是否一致，防止伪造扩展名。

    按顺序尝试四类判定：

    1. 固定前缀魔数（PDF / PNG / JPEG / Office+zip 系 / CHM …）
    2. 偏移型魔数（AZW3 / MOBI 的 PalmDB 标识在第 60 字节）
    3. ISO-BMFF 容器（MP4 / MOV / 3GP / HEIC / M4A …）
    4. 音频（MP3 / WAV）

    都没命中时只放行纯文本类扩展名。
    """
    for magic, allowed in _MAGIC_SIGNATURES:
        if header.startswith(magic):
            if ext not in allowed:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="文件内容与扩展名不匹配",
                )
            return

    for offset, magic, allowed in _OFFSET_SIGNATURES:
        if header[offset : offset + len(magic)] == magic:
            if ext not in allowed:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="文件内容与扩展名不匹配",
                )
            return

    bmff_allowed = _iso_bmff_allowed(header)
    if bmff_allowed is not None:
        if ext not in bmff_allowed:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="文件内容与扩展名不匹配",
            )
        return

    if ext in AUDIO_EXTENSIONS and (_is_mp3(header) or _is_wav(header)):
        return

    # 未命中已知魔数：只允许纯文本类扩展名
    if ext not in TEXT_EXTENSIONS:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="文件内容无法识别")


# ---------------- 路径与权限 ----------------

#: 允许上传的全部扩展名
ALLOWED_EXTENSIONS = (
    TEXT_EXTENSIONS
    | IMAGE_EXTENSIONS
    | HEIC_EXTENSIONS
    | PDF_EXTENSIONS
    | WORD_EXTENSIONS
    | EXCEL_EXTENSIONS
    | PPT_EXTENSIONS
    | ARCHIVE_EXTENSIONS
    | EBOOK_EXTENSIONS
    | CHM_EXTENSIONS
    | VIDEO_EXTENSIONS
    | AUDIO_EXTENSIONS
    | LEGACY_OFFICE_EXTENSIONS
)


def storage_path(item: FileItem, *, must_exist: bool = True) -> Path:
    """把数据库记录解析为磁盘绝对路径，并校验未跳出上传目录。"""
    base = settings.UPLOAD_DIR.resolve()
    path = (base / item.stored_name).resolve()
    if not path.is_relative_to(base):
        raise HTTPException(status_code=400, detail="非法文件路径")
    if must_exist and not path.is_file():
        raise HTTPException(status_code=404, detail="文件已丢失")
    return path


async def get_accessible_file(db: AsyncSession, file_id: int, user: User) -> FileItem:
    """取出文件记录并校验访问权限（上传者本人或管理员）。"""
    item = await db.get(FileItem, file_id)
    if item is None:
        raise HTTPException(status_code=404, detail="文件不存在")
    if item.uploader_id != user.id and not is_admin(user):
        raise HTTPException(status_code=403, detail="无权访问该文件")
    return item


__all__ = [
    "ALLOWED_EXTENSIONS",
    "ARCHIVE_EXTENSIONS",
    "AUDIO_EXTENSIONS",
    "CHM_EXTENSIONS",
    "EBOOK_EXTENSIONS",
    "EPUB_EXTENSIONS",
    "EXCEL_EXTENSIONS",
    "HEIC_EXTENSIONS",
    "IMAGE_EXTENSIONS",
    "LEGACY_ALLOWED_MAGIC",
    "LEGACY_OFFICE_EXTENSIONS",
    "MOBI_EXTENSIONS",
    "PDF_EXTENSIONS",
    "PPT_EXTENSIONS",
    "TEXT_EXTENSIONS",
    "VIDEO_EXTENSIONS",
    "WORD_EXTENSIONS",
    "get_accessible_file",
    "get_ext",
    "safe_original_name",
    "storage_path",
    "validate_extension",
    "validate_magic",
]
