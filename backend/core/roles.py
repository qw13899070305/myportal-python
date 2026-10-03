"""角色与权限判定（独立零件）。

- :func:`is_admin` —— 纯函数判断，不依赖 FastAPI
- :class:`RoleChecker` —— FastAPI 依赖，要求当前用户具备指定角色之一

把权限相关的东西单独放，是为了让"谁算管理员"这条规则只有一个出处：
以后要加 ``moderator`` 之类的角色，只改这一个文件。
"""

from __future__ import annotations

from fastapi import Depends, HTTPException, status

from backend.core.current_user import get_current_user
from backend.models.user import User

#: 视为管理员的角色
ADMIN_ROLES = frozenset({"admin", "super_admin"})


def roles_of(user: User | None) -> set[str]:
    """取出用户的角色名集合。"""
    if user is None:
        return set()
    return {role.name for role in user.roles or []}


def has_any_role(user: User | None, allowed: set[str] | frozenset[str]) -> bool:
    """用户是否具备给定角色之一。"""
    return bool(roles_of(user) & set(allowed))


def is_admin(user: User | None) -> bool:
    """用户是否具备管理权限。"""
    return has_any_role(user, ADMIN_ROLES)


class RoleChecker:
    """依赖：要求当前用户具备指定角色之一。"""

    def __init__(self, allowed_roles: list[str]):
        self.allowed_roles = set(allowed_roles)

    async def __call__(self, current_user: User = Depends(get_current_user)) -> User:
        if not has_any_role(current_user, self.allowed_roles):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="权限不足")
        return current_user


__all__ = ["ADMIN_ROLES", "RoleChecker", "has_any_role", "is_admin", "roles_of"]
