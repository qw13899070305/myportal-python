"""验证码扩展的基类与协议。

拆成两类可替换零件：

- :class:`CaptchaRenderer` —— 怎么把答案画出来（图片 / 算术题 / 滑块……）
- :class:`CaptchaStore`    —— 答案存在哪（进程内存 / Redis ……）

两者通过 :class:`CaptchaChallenge` 传递数据，互不知道对方的实现。
"""

from __future__ import annotations

import secrets
import string
from abc import ABC, abstractmethod
from dataclasses import dataclass

#: 去掉容易混淆的字符
DEFAULT_ALPHABET = "".join(c for c in string.ascii_uppercase + string.digits if c not in "O0I1L")


@dataclass(frozen=True)
class CaptchaChallenge:
    """一次验证码挑战：答案 + 呈现给用户的图片。"""

    code: str
    image: bytes
    media_type: str = "image/png"


class CaptchaRenderer(ABC):
    """把验证码答案渲染成可展示的内容。"""

    name: str = ""
    priority: int = 0
    #: 答案长度
    length: int = 4

    def generate_code(self) -> str:
        """默认答案：随机大写字母数字。"""
        return "".join(secrets.choice(DEFAULT_ALPHABET) for _ in range(self.length))

    @abstractmethod
    def render(self, code: str) -> tuple[bytes, str]:
        """返回 ``(内容字节, media_type)``。"""

    def create(self) -> CaptchaChallenge:
        """生成一个完整挑战。"""
        code = self.generate_code()
        body, media_type = self.render(code)
        return CaptchaChallenge(code=code, image=body, media_type=media_type)


class CaptchaStore(ABC):
    """验证码答案的存储。"""

    name: str = ""
    priority: int = 0

    @abstractmethod
    def save(self, captcha_id: str, code: str, ttl: int) -> None:
        """保存答案，``ttl`` 秒后过期。"""

    @abstractmethod
    def take(self, captcha_id: str) -> str | None:
        """取出并**立即作废**答案（一次性），不存在或已过期返回 None。"""

    def clear(self) -> None:  # noqa: B027 - 可选钩子，测试用
        """清空全部（测试用）。"""


__all__ = [
    "DEFAULT_ALPHABET",
    "CaptchaChallenge",
    "CaptchaRenderer",
    "CaptchaStore",
]
