"""用户与角色模型。"""

from sqlalchemy import (
    Boolean,
    Column,
    ForeignKey,
    Integer,
    String,
    Table,
    select,
)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import relationship

from backend.core.database import Base
from backend.core.password import get_password_hash, verify_password

#: 注册时默认分配的角色
DEFAULT_ROLE = "user"
#: 内置角色（首次启动时自动创建）
BUILTIN_ROLES = {
    "user": "普通用户",
    "admin": "管理员",
    "super_admin": "超级管理员",
    "reader": "只读用户",
}

user_roles = Table(
    "user_roles",
    Base.metadata,
    Column(
        "user_id",
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "role_id",
        Integer,
        ForeignKey("roles.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)


class Role(Base):
    __tablename__ = "roles"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, index=True, nullable=False)
    description = Column(String(200), nullable=True)

    users = relationship("User", secondary=user_roles, back_populates="roles")

    def __repr__(self) -> str:  # pragma: no cover - 调试辅助
        return f"<Role {self.name}>"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=True)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    #: 头像文件名（保存在 UPLOAD_DIR/avatars/ 下），为空表示没有上传过头像
    avatar = Column(String(255), nullable=True)

    # lazy="selectin"：异步会话中访问 user.roles 不会触发隐式 IO
    roles = relationship("Role", secondary=user_roles, back_populates="users", lazy="selectin")

    # ---------------- 密码 ----------------
    def set_password(self, password: str) -> None:
        """设置密码（自动哈希）。"""
        self.hashed_password = get_password_hash(password)

    def check_password(self, password: str) -> bool:
        """校验密码。"""
        return verify_password(password, self.hashed_password)

    # ---------------- 便捷属性 ----------------
    @property
    def role_names(self) -> list[str]:
        return [role.name for role in self.roles or []]

    @property
    def is_admin(self) -> bool:
        return bool({"admin", "super_admin"} & set(self.role_names))

    @property
    def avatar_url(self) -> str | None:
        """头像访问地址（没有上传过头像时为 None）。"""
        from backend.services.avatar import avatar_url_for

        return avatar_url_for(self)

    def __repr__(self) -> str:  # pragma: no cover - 调试辅助
        return f"<User {self.username}>"


async def get_user_by_id(db: AsyncSession, user_id: int) -> User | None:
    return await db.scalar(select(User).where(User.id == user_id))


async def get_user_by_username(db: AsyncSession, username: str) -> User | None:
    return await db.scalar(select(User).where(User.username == username))


async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
    return await db.scalar(select(User).where(User.email == email))


async def get_role_by_name(db: AsyncSession, name: str) -> Role | None:
    return await db.scalar(select(Role).where(Role.name == name))


async def get_or_create_role(db: AsyncSession, name: str) -> Role:
    """按名称取角色，不存在则创建（避免因角色表为空而注册失败）。"""
    role = await get_role_by_name(db, name)
    if role is None:
        role = Role(name=name, description=BUILTIN_ROLES.get(name))
        db.add(role)
        await db.flush()
    return role


async def create_user(
    db: AsyncSession,
    username: str,
    password: str,
    email: str | None = None,
    roles: list[str] | None = None,
) -> User:
    """创建用户。

    注意参数顺序是 ``(username, password, email)``，
    ``services/user_service.py`` 里的同名函数已改为委托到这里，
    避免两处签名不一致导致邮箱和密码被写反。
    """
    user = User(username=username, email=email or None, is_active=True)
    user.set_password(password)
    for role_name in roles or [DEFAULT_ROLE]:
        user.roles.append(await get_or_create_role(db, role_name))
    db.add(user)
    await db.commit()
    return user
