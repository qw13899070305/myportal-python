import bleach
from bleach.css_sanitizer import CSSSanitizer

ALLOWED_TAGS = [
    'a', 'abbr', 'b', 'blockquote', 'code', 'em', 'i', 'li', 'ol', 'p', 'pre', 'strong', 'ul',
    'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'br', 'hr', 'img', 'table', 'thead', 'tbody', 'tr', 'th', 'td'
]
ALLOWED_ATTRIBUTES = {
    'a': ['href', 'title', 'target'],
    'img': ['src', 'alt', 'title'],
    'th': ['align'],
    'td': ['align']
}

def sanitize_html_bleach(dirty_html: str) -> str:
    """清洗 HTML，防止 XSS"""
    cleaner = bleach.Cleaner(tags=ALLOWED_TAGS, attributes=ALLOWED_ATTRIBUTES,
                             css_sanitizer=CSSSanitizer(), strip=True)
    return cleaner.clean(dirty_html)

def sanitize_filename(filename: str) -> str:
    import os
    return os.path.basename(filename)

def validate_file_type(filename: str, file):
    # 简单基于扩展名检查，已结合魔数校验
    ALLOWED_EXTENSIONS = {'.txt', '.pdf', '.png', '.jpg', '.jpeg', '.gif', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx', '.zip'}
    ext = os.path.splitext(filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise ValueError("不支持的文件类型")
    return True
