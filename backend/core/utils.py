"""通用工具：HTML 清洗、文件名处理、时间工具。"""

import os
from datetime import UTC, datetime

import bleach
from bleach.css_sanitizer import CSSSanitizer

# 允许在文档预览/Markdown 渲染中出现的标签与属性
ALLOWED_TAGS = [
    "a",
    "abbr",
    "b",
    "blockquote",
    "br",
    "code",
    "em",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "hr",
    "i",
    "img",
    "li",
    "ol",
    "p",
    "pre",
    "strong",
    "table",
    "tbody",
    "td",
    "th",
    "thead",
    "tr",
    "ul",
]
ALLOWED_ATTRIBUTES = {
    "a": ["href", "title", "target"],
    "img": ["src", "alt", "title"],
    "th": ["align", "colspan", "rowspan"],
    "td": ["align", "colspan", "rowspan"],
}

#: 允许上传的扩展名（魔数校验在 api/v1/file_common.py 中另行执行）。
#: 权威列表是 :data:`backend.api.v1.file_common.ALLOWED_EXTENSIONS`，改那里时记得同步这里。
ALLOWED_EXTENSIONS = {
    ".txt",
    ".md",
    ".csv",
    ".json",
    ".log",
    ".pdf",
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".webp",
    ".bmp",
    ".heic",
    ".heif",
    ".doc",
    ".docx",
    ".xls",
    ".xlsx",
    ".ppt",
    ".pptx",
    ".zip",
    ".epub",
    ".azw3",
    ".mobi",
    ".chm",
    ".mp4",
    ".mov",
    ".3gp",
    ".m4v",
    ".mp3",
    ".m4a",
    ".wav",
}


def format_size(num_bytes: int) -> str:
    """把字节数变成人看的字符串（用于错误提示与日志）。"""
    if num_bytes >= 1024**3:
        value = num_bytes / 1024**3
        return f"{value:g}GB"
    if num_bytes >= 1024**2:
        return f"{num_bytes // 1024 // 1024}MB"
    if num_bytes >= 1024:
        return f"{num_bytes // 1024}KB"
    return f"{num_bytes}字节"


def utcnow() -> datetime:
    """返回**不带时区信息**的 UTC 当前时间。

    数据库中的时间列统一存储 naive UTC，这样能避免
    ``datetime.now()``（本地时间）与 ``datetime.utcnow()`` /
    数据库 ``CURRENT_TIMESTAMP``（UTC）混用导致的比较错误——
    此前"2 分钟内可撤回消息"的判断就因此失效。
    """
    return datetime.now(UTC).replace(tzinfo=None)


def sanitize_html_bleach(dirty_html: str) -> str:
    """清洗 HTML，防止 XSS。"""
    cleaner = bleach.Cleaner(
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        css_sanitizer=CSSSanitizer(),
        strip=True,
    )
    return cleaner.clean(dirty_html)


def sanitize_filename(filename: str) -> str:
    """去掉目录部分，只保留文件名，防止路径穿越。"""
    return os.path.basename(filename.replace("\\", "/"))


def validate_file_type(filename: str) -> bool:
    """基于扩展名的初步校验（真实类型还需要魔数校验）。"""
    ext = os.path.splitext(filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise ValueError(f"不支持的文件类型 {ext or '(无扩展名)'}")
    return True
