"""请求体大小限制中间件（可拆卸扩展）。

只做一件小事：``Content-Length`` 明显超限时直接返回 413，
避免把超大请求体读进内存。真正的单文件限制在文件上传接口里。
"""

from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from backend.core.config import settings

#: 请求体上限：跟着单文件上限走，再留一点余量给 multipart 的表单开销
MAX_REQUEST_BODY = settings.MAX_UPLOAD_SIZE + 8 * 1024 * 1024


class MaxBodySizeMiddleware(BaseHTTPMiddleware):
    """请求体大小限制：Content-Length 明显超限时直接拒绝。"""

    def __init__(self, app, max_body: int = MAX_REQUEST_BODY) -> None:
        super().__init__(app)
        self.max_body = max_body

    async def dispatch(self, request: Request, call_next):
        content_length = request.headers.get("content-length")
        if content_length:
            try:
                too_large = int(content_length) > self.max_body
            except ValueError:
                too_large = False  # 非法 Content-Length 交给下游处理
            if too_large:
                return JSONResponse(status_code=413, content={"detail": "请求体过大"})
        return await call_next(request)
