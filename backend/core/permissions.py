from fastapi import Depends, HTTPException, status
from backend.models.user import User
from backend.core.auth.dependencies import get_current_user


class RoleChecker:
    def __init__(self, allowed_roles: list[str]):
        self.allowed_roles = allowed_roles

    async def __call__(self, current_user: User = Depends(get_current_user)):
        if not current_user.roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="权限不足"
            )
        user_roles = [role.name for role in current_user.roles]
        if not any(role in self.allowed_roles for role in user_roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="权限不足"
            )
        return current_user


admin_required = RoleChecker(["admin"])