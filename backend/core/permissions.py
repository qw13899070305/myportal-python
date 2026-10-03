"""权限校验（转发模块）。

此前本模块从 ``backend.core.auth.dependencies`` 导入，而
``core/auth.py`` 并不是包，因此导入必然失败。现在统一使用
:mod:`backend.core.security` 的实现。
"""

from fastapi import Depends, HTTPException, status

from backend.core.security import RoleChecker, get_current_user  # noqa: F401
from backend.models.user import User

__all__ = ["RoleChecker", "require_roles", "admin_required", "super_admin_required"]


def require_roles(*roles: str) -> RoleChecker:
    """生成一个角色校验依赖：``Depends(require_roles("admin"))``。"""
    return RoleChecker(list(roles))


class SelfOrAdmin:
    """依赖：只允许本人或管理员访问（用于 ``/{user_id}`` 一类路径）。"""

    async def __call__(
        self,
        user_id: int,
        current_user: User = Depends(get_current_user),
    ) -> User:
        is_admin_user = any(
            role.name in {"admin", "super_admin"} for role in current_user.roles or []
        )
        if current_user.id != user_id and not is_admin_user:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="权限不足")
        return current_user


# 常用实例，路由里可以直接 Depends(admin_required)
admin_required = RoleChecker(["admin", "super_admin"])
super_admin_required = RoleChecker(["super_admin"])
