"""全局异常处理：统一响应格式，避免泄露内部细节。"""

from fastapi import HTTPException, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from backend.core.config import settings
from backend.core.logger import logger


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """业务异常：保留原始状态码与响应头（如 ``WWW-Authenticate``）。"""
    logger.warning(f"HTTP {exc.status_code} {request.method} {request.url.path}: {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
        # 丢掉 headers 会让 401 响应缺少 WWW-Authenticate，前端与规范都依赖它
        headers=getattr(exc, "headers", None),
    )


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """参数校验失败。

    默认 422 响应体里的 ``detail`` 是对象列表，前端无法直接展示，
    这里额外给出一条可读提示，同时保留原始错误明细。
    """
    errors = exc.errors()
    detail = "请求参数不合法"
    if errors:
        first = errors[0]
        location = ".".join(
            str(part) for part in first.get("loc", ()) if part not in ("body", "query")
        )
        message = first.get("msg", detail)
        detail = f"{location}: {message}" if location else message
    logger.warning(f"422 {request.method} {request.url.path}: {detail}")
    return JSONResponse(
        status_code=422,
        content={"detail": detail, "errors": jsonable_encoder(errors)},
    )


async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """未捕获异常：记录完整堆栈，只对外返回笼统信息。"""
    logger.error(f"未捕获异常 {request.method} {request.url.path}: {exc}", exc_info=True)
    detail = "服务器内部错误"
    if settings.DEBUG:
        detail = f"{type(exc).__name__}: {exc}"
    return JSONResponse(status_code=500, content={"detail": detail})
