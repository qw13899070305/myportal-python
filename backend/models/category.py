"""文章分类模型。

与标签（``tags``）的区别：分类是唯一的、必选的层级结构，
标签是多对多的自由标记。
"""

from sqlalchemy import Column, Integer, String

from backend.core.database import Base


class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, nullable=False)
    description = Column(String(200), nullable=True)

    def __repr__(self) -> str:  # pragma: no cover - 调试辅助
        return f"<Category {self.name}>"
