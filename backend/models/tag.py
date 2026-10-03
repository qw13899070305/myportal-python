"""标签模型（转发模块）。

``Tag`` 与多对多关联表 ``article_tags`` 一起定义在
:mod:`backend.models.article` 中。本模块曾经重复定义了
``__tablename__ = "tags"``，只要两个模块同时被导入，
SQLAlchemy 就会抛 ``Table 'tags' is already defined``。
这里改为转发，保证 ``from backend.models.tag import Tag`` 仍然可用。
"""

from backend.models.article import Tag, article_tags  # noqa: F401

__all__ = ["Tag", "article_tags"]
