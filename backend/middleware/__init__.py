"""HTTP 中间件集合。

每个中间件一个文件，可以单独摘掉：

- :class:`backend.middleware.request_id.RequestIDMiddleware` —— 请求追踪 ID
- :class:`backend.middleware.max_body.MaxBodySizeMiddleware` —— 请求体大小限制
"""

from backend.middleware.max_body import MAX_REQUEST_BODY, MaxBodySizeMiddleware
from backend.middleware.request_id import RequestIDMiddleware

__all__ = [
    "MAX_REQUEST_BODY",
    "MaxBodySizeMiddleware",
    "RequestIDMiddleware",
]
