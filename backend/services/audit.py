"""审计日志服务。

关键操作（登录、注册、删除、审核、用户启停……）都会写入 ``audit_logs``，
后台可以通过 ``/api/v1/audit`` 查询。

``log_action`` 只把对象加入会话，不提交事务，由调用方统一 ``commit``。
"""

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.logger import logger
from backend.models.audit import AuditLog


def client_ip(request: Request | None) -> str:
    """取客户端 IP：优先 X-Forwarded-For，其次直连地址。"""
    if request is None:
        return ""
    forwarded = request.headers.get("x-forwarded-for", "")
    if forwarded:
        return forwarded.split(",")[0].strip()[:45]
    if request.client and request.client.host:
        return request.client.host[:45]
    return ""


async def log_action(
    db: AsyncSession,
    *,
    action: str,
    user_id: int | None = None,
    detail: str | None = None,
    request: Request | None = None,
) -> AuditLog:
    """写一条审计日志（不提交事务）。"""
    entry = AuditLog(
        user_id=user_id,
        action=action[:200],
        detail=(detail or "")[:2000] or None,
        ip_address=client_ip(request),
    )
    db.add(entry)
    return entry


async def safe_log_action(
    db: AsyncSession,
    *,
    action: str,
    user_id: int | None = None,
    detail: str | None = None,
    request: Request | None = None,
) -> None:
    """写审计日志并立即提交；失败只记日志，绝不影响业务主流程。"""
    try:
        await log_action(db, action=action, user_id=user_id, detail=detail, request=request)
        await db.commit()
    except Exception as exc:  # pragma: no cover - 审计失败不应中断业务
        logger.warning(f"写入审计日志失败: {exc}")
        await db.rollback()
