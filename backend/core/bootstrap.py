"""启动引导：准备内置角色与可选的管理员账号。

拆成独立模块的原因：它是"部署相关"的一次性动作，
和路由/中间件那些运行期逻辑没有关系，摘掉也不影响应用启动
（只是第一次启动不会自动建角色和管理员）。
"""

from __future__ import annotations

from backend.core.config import settings
from backend.core.database import AsyncSessionLocal
from backend.core.logger import logger
from backend.models.user import (
    BUILTIN_ROLES,
    Role,
    User,
    get_role_by_name,
    get_user_by_username,
)

#: 管理员密码最短长度
MIN_ADMIN_PASSWORD_LENGTH = 8


async def ensure_roles() -> int:
    """确保内置角色存在，返回新建的数量。"""
    created = 0
    async with AsyncSessionLocal() as db:
        for name, description in BUILTIN_ROLES.items():
            if await get_role_by_name(db, name) is None:
                db.add(Role(name=name, description=description))
                created += 1
        await db.commit()
    if created:
        logger.info(f"已创建 {created} 个内置角色")
    return created


async def ensure_admin() -> bool:
    """按配置创建初始管理员，返回是否真的创建了。"""
    if not settings.ADMIN_USERNAME or not settings.ADMIN_PASSWORD:
        return False

    if len(settings.ADMIN_PASSWORD) < MIN_ADMIN_PASSWORD_LENGTH:
        logger.error(f"ADMIN_PASSWORD 长度不足 {MIN_ADMIN_PASSWORD_LENGTH} 位，跳过管理员初始化")
        return False

    async with AsyncSessionLocal() as db:
        if await get_user_by_username(db, settings.ADMIN_USERNAME) is not None:
            return False

        admin_role = await get_role_by_name(db, "admin")
        admin = User(
            username=settings.ADMIN_USERNAME,
            email=settings.ADMIN_EMAIL or None,
            is_active=True,
        )
        admin.set_password(settings.ADMIN_PASSWORD)
        if admin_role is not None:
            admin.roles.append(admin_role)
        db.add(admin)
        await db.commit()

    logger.warning(f"已创建初始管理员 {settings.ADMIN_USERNAME}，请首次登录后立即修改密码")
    return True


async def bootstrap() -> None:
    """首次启动时准备基础数据。"""
    await ensure_roles()
    await ensure_admin()
