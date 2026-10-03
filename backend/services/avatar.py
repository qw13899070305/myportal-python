"""用户头像存储。

头像以 ``{user_id}.{ext}`` 的形式保存在 ``UPLOAD_DIR/avatars/`` 下，
数据库里只记录文件名，避免路径穿越。
"""

from pathlib import Path

from backend.core.config import settings
from backend.core.logger import logger

#: 允许的头像格式
ALLOWED_AVATAR_TYPES = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/gif": ".gif",
    "image/webp": ".webp",
}
MAX_AVATAR_SIZE = 2 * 1024 * 1024  # 2MB


def avatar_dir() -> Path:
    directory = settings.UPLOAD_DIR / "avatars"
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def find_avatar(user_id: int) -> Path | None:
    """找出该用户的头像文件（不关心扩展名）。"""
    directory = settings.UPLOAD_DIR / "avatars"
    if not directory.is_dir():
        return None
    for path in directory.glob(f"{user_id}.*"):
        if path.is_file():
            return path
    return None


def avatar_url_for(user) -> str | None:
    """生成头像访问地址；没有头像时返回 None。"""
    user_id = getattr(user, "id", None)
    if not user_id:
        return None
    return f"/api/v1/auth/avatar/{user_id}" if find_avatar(user_id) else None


def save_avatar(user_id: int, content: bytes, content_type: str | None) -> str:
    """保存头像，返回文件名。旧头像会被覆盖。"""
    ext = ALLOWED_AVATAR_TYPES.get((content_type or "").lower())
    if ext is None:
        raise ValueError("头像只支持 PNG / JPEG / GIF / WebP 格式")
    if len(content) > MAX_AVATAR_SIZE:
        raise ValueError(f"头像不能超过 {MAX_AVATAR_SIZE // 1024 // 1024}MB")

    remove_avatar(user_id)
    filename = f"{user_id}{ext}"
    (avatar_dir() / filename).write_bytes(content)
    logger.info(f"用户 {user_id} 更新头像: {filename}")
    return filename


def remove_avatar(user_id: int) -> None:
    """删除该用户已有的头像文件。"""
    existing = find_avatar(user_id)
    if existing is not None:
        existing.unlink(missing_ok=True)
