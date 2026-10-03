"""数据库引擎、会话工厂与 ORM 基类。

注意：``Base`` 必须在这里定义——所有模型都通过
``from backend.core.database import Base`` 获取它，
缺少它会导致整个应用在 import 阶段直接崩溃。
"""

from collections.abc import AsyncIterator
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from backend.core.config import settings


class Base(DeclarativeBase):
    """所有 ORM 模型的公共基类。"""


def _is_sqlite(url: str) -> bool:
    return url.startswith("sqlite")


# SQLite 不需要连接池参数，其他数据库（PostgreSQL/MySQL）才需要。
_engine_kwargs: dict = {"echo": False, "future": True}
if not _is_sqlite(settings.DATABASE_URL):
    _engine_kwargs.update(
        pool_size=settings.DB_POOL_SIZE,
        max_overflow=settings.DB_MAX_OVERFLOW,
        pool_recycle=settings.DB_POOL_RECYCLE,
        pool_pre_ping=settings.DB_POOL_PRE_PING,
    )

engine = create_async_engine(settings.DATABASE_URL, **_engine_kwargs)

AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db() -> AsyncIterator[AsyncSession]:
    """FastAPI 依赖：提供一个请求级会话，异常自动回滚。"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise


def ensure_sqlite_directory() -> None:
    """SQLite 的库文件目录不存在时先建出来。

    否则会抛出很难看懂的 ``unable to open database file``——
    例如把 DATABASE_URL 指到 ``/var/lib/myportal/data.db`` 但目录还没建。
    """
    url = settings.DATABASE_URL
    if not _is_sqlite(url) or ":memory:" in url:
        return

    # sqlite+aiosqlite:////abs/path.db  或  sqlite+aiosqlite:///rel/path.db
    raw = url.split(":///", 1)[-1]
    if not raw:
        return
    path = Path(raw)
    if path.is_absolute():
        path.parent.mkdir(parents=True, exist_ok=True)
    else:
        path.parent.mkdir(parents=True, exist_ok=True)


async def init_models() -> None:
    """创建所有尚未存在的表。

    必须先 import ``backend.models``，否则 ``Base.metadata``
    里只有被显式导入过的模型，造成"表不存在"的运行时错误。
    """
    import backend.models  # noqa: F401  注册全部模型元数据

    ensure_sqlite_directory()

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
