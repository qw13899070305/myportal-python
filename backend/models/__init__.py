"""集中导入所有 ORM 模型。

``Base.metadata`` 只包含**被导入过**的模型，因此这里必须导入每一个
模型模块，``create_all`` 才能建出完整的库表结构。
"""

from backend.models.article import (
    STATUS_APPROVED,
    STATUS_PENDING,
    STATUS_REJECTED,
    Article,
    Bookmark,
    Comment,
    Like,
    Tag,
    article_tags,
)
from backend.models.audit import AuditLog
from backend.models.category import Category
from backend.models.chat import ChatMessage, Notification
from backend.models.config import DEFAULT_SITE_CONFIG, SiteConfig
from backend.models.file import FileItem, TrashItem
from backend.models.share import ShareLink

# 说明：``backend/models/tag.py`` 是对 article.Tag 的转发模块，
# 这里不再重复导入（同一个名字导入两次会触发 lint 的重复定义告警），
# 需要它的代码直接 ``from backend.models.tag import Tag`` 即可。
from backend.models.user import (
    BUILTIN_ROLES,
    DEFAULT_ROLE,
    Role,
    User,
    user_roles,
)

__all__ = [
    "BUILTIN_ROLES",
    "DEFAULT_ROLE",
    "DEFAULT_SITE_CONFIG",
    "STATUS_APPROVED",
    "STATUS_PENDING",
    "STATUS_REJECTED",
    "Article",
    "AuditLog",
    "Bookmark",
    "Category",
    "ChatMessage",
    "Comment",
    "FileItem",
    "Like",
    "Notification",
    "Role",
    "ShareLink",
    "SiteConfig",
    "Tag",
    "TrashItem",
    "User",
    "article_tags",
    "user_roles",
]
