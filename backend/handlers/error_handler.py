from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from backend.core.logger import logger

async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"未捕获异常 {request.method} {request.url.path}: {exc}", exc_info=True)
    return JSONResponse(status_code=500, content={"detail": "服务器内部错误"})

async def http_exception_handler(request: Request, exc: HTTPException):
    logger.warning(f"HTTP异常 {exc.status_code}: {exc.detail}")
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})