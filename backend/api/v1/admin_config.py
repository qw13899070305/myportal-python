"""后台 · 站点配置（可拆卸扩展）。

挂载在 ``/api/v1/admin`` 下：

- ``GET  /admin/config``        读取（缺失键用默认值补齐）
- ``PUT  /admin/config``        更新
- ``POST /admin/config``        更新（兼容前端的 POST 调用）
- ``GET  /admin/site-info``     公开的站点信息（无需登录）

把本文件删掉，后台其它功能不受影响，只是站点配置恢复成默认值。
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.database import get_db
from backend.core.security import RoleChecker
from backend.core.utils import utcnow
from backend.models.config import DEFAULT_SITE_CONFIG, SiteConfig
from backend.models.user import User
from backend.schemas.site import SiteConfigUpdate
from backend.services.audit import safe_log_action

router = APIRouter()

admin_only = RoleChecker(["admin", "super_admin"])


async def _load_site_config(db: AsyncSession) -> dict[str, str]:
    """读取站点配置，缺失的键用默认值补齐。"""
    result = await db.execute(select(SiteConfig))
    stored = {row.key: row.value for row in result.scalars().all()}
    return {**DEFAULT_SITE_CONFIG, **stored}


async def _update_site_config(
    payload: SiteConfigUpdate,
    db: AsyncSession,
    current_admin: User,
    request: Request | None,
) -> dict[str, str]:
    for key, value in payload.to_pairs():
        row = await db.scalar(select(SiteConfig).where(SiteConfig.key == key))
        if row is None:
            db.add(SiteConfig(key=key, value=value))
        else:
            row.value = value
            db.add(row)
    await db.commit()
    await safe_log_action(
        db,
        action="site_config_update",
        user_id=current_admin.id,
        detail=", ".join(f"{k}={v}" for k, v in payload.to_pairs()),
        request=request,
    )
    return await _load_site_config(db)


@router.get("/config")
async def get_site_config(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(admin_only),
):
    """读取站点配置。"""
    return await _load_site_config(db)


@router.put("/config")
async def update_site_config(
    request: Request,
    payload: SiteConfigUpdate,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(admin_only),
):
    """更新站点配置（按 key upsert）。"""
    return await _update_site_config(payload, db, current_admin, request)


@router.post("/config")
async def update_site_config_post(
    request: Request,
    payload: SiteConfigUpdate,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(admin_only),
):
    """更新站点配置（兼容前端的 POST 调用）。"""
    return await _update_site_config(payload, db, current_admin, request)


@router.get("/site-info")
async def site_info(db: AsyncSession = Depends(get_db)):
    """站点公开信息（无需登录），前端可用来显示站名与公告。"""
    config = await _load_site_config(db)
    return {
        "site_name": config.get("site_name", DEFAULT_SITE_CONFIG["site_name"]),
        "announcement": config.get("announcement", ""),
        "allow_register": config.get("allow_register", "true") == "true",
        "allow_upload": config.get("allow_upload", "true") == "true",
        "server_time": utcnow().isoformat(),
    }
