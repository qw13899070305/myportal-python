"""文件接口（组装配件）。

每个子零件都可以单独摘掉：

===========================  ============================================
模块                          接口
===========================  ============================================
``file_list.py``             GET /, GET /list, GET /recent
``file_upload.py``           POST /upload
``file_download.py``         GET /{id}/download, GET /download/{id}
``file_raw.py``              GET /{id}/raw（inline 字节流，播放器数据源）
``file_book.py``             GET /{id}/book（电子书 JSON，给 APP 用）
``file_edit.py``             GET/PATCH/DELETE /{id}, PUT /rename/{id}
``file_preview.py``          GET /{id}/preview, /pdf-info, /pdf-page/{n}
``trash.py``                 回收站
``share.py``                 分享链接
===========================  ============================================

类型校验与权限解析在 :mod:`backend.api.v1.file_common`。

**挂载顺序很重要**：``file_list``（固定路径 ``/list``、``/recent``）
必须排在 ``file_edit``（``/{file_id}``）之前，否则会被路径参数吃掉。
:mod:`backend.api.v1.file_raw` 与 :mod:`backend.api.v1.file_book` 走的是
``/{file_id}/xxx``（多一层），跟 ``/{file_id}`` 不冲突。
"""

from __future__ import annotations

from fastapi import APIRouter

from backend.api.v1._loader import include_optional

router = APIRouter()

#: 组内的子零件，顺序即路由匹配顺序
PARTS: list[tuple[str, str, list[str]]] = [
    ("backend.api.v1.file_list", "", ["文件"]),
    ("backend.api.v1.file_upload", "", ["文件"]),
    ("backend.api.v1.file_download", "", ["文件"]),
    ("backend.api.v1.file_raw", "", ["文件-字节流"]),
    ("backend.api.v1.file_book", "", ["文件-在线阅读"]),
    ("backend.api.v1.file_edit", "", ["文件"]),
]

for _module, _prefix, _tags in PARTS:
    include_optional(router, _module, _prefix, _tags)

__all__ = ["PARTS", "router"]
