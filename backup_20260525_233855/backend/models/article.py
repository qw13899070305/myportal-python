from datetime import datetime
from sqlalchemy import String, Text, DateTime, ForeignKey, Integer, Table, Column, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.core.database import Base
from backend.models.user import User

article_tags = Table("article_tags", Base.metadata,
    Column("article_id", Integer, ForeignKey("articles.id", ondelete="CASCADE"), primary_key=True),
    Column("tag_id", Integer, ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True),
)

class Tag(Base):
    __tablename__ = "tags"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50), unique=True)
    articles: Mapped[list["Article"]] = relationship(secondary=article_tags, back_populates="tags")

class Article(Base):
    __tablename__ = "articles"
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    content: Mapped[str] = mapped_column(Text)
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    status: Mapped[str] = mapped_column(String(20), default="pending")
    is_pinned: Mapped[bool] = mapped_column(Boolean, default=False)
    is_internal: Mapped[bool] = mapped_column(Boolean, default=False)  # 内部文章
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    author: Mapped[User] = relationship("User", lazy="selectin")
    comments: Mapped[list["Comment"]] = relationship(back_populates="article", cascade="all, delete-orphan")
    likes: Mapped[list["Like"]] = relationship(back_populates="article", cascade="all, delete-orphan")
    bookmarks: Mapped[list["Bookmark"]] = relationship(back_populates="article", cascade="all, delete-orphan")
    tags: Mapped[list[Tag]] = relationship(secondary=article_tags, back_populates="articles")

class Comment(Base):
    __tablename__ = "comments"
    id: Mapped[int] = mapped_column(primary_key=True)
    article_id: Mapped[int] = mapped_column(ForeignKey("articles.id", ondelete="CASCADE"))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    parent_id: Mapped[int | None] = mapped_column(ForeignKey("comments.id"), nullable=True)
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    article: Mapped[Article] = relationship(back_populates="comments")
    user: Mapped[User] = relationship("User", lazy="selectin")

class Like(Base):
    __tablename__ = "likes"
    id: Mapped[int] = mapped_column(primary_key=True)
    article_id: Mapped[int] = mapped_column(ForeignKey("articles.id", ondelete="CASCADE"))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    article: Mapped[Article] = relationship(back_populates="likes")
    user: Mapped[User] = relationship("User", lazy="selectin")

class Bookmark(Base):
    __tablename__ = "bookmarks"
    id: Mapped[int] = mapped_column(primary_key=True)
    article_id: Mapped[int] = mapped_column(ForeignKey("articles.id", ondelete="CASCADE"))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    article: Mapped[Article] = relationship(back_populates="bookmarks")
    user: Mapped[User] = relationship("User", lazy="selectin")
