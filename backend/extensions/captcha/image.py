"""图片验证码渲染器（Pillow）。

画一张带干扰线和噪点的 PNG。想换成别的样式（算术题、滑块）
只要加一个新文件实现 :class:`CaptchaRenderer` 并把 priority 调高。
"""

from __future__ import annotations

import io
import random

from PIL import Image, ImageDraw, ImageFont

from backend.extensions.captcha.base import CaptchaRenderer
from backend.extensions.registry import get_registry


class ImageCaptchaRenderer(CaptchaRenderer):
    name = "image"
    priority = 10
    length = 4

    #: 画布尺寸
    width = 160
    height = 60
    font_size = 38

    def _load_font(self) -> ImageFont.ImageFont:
        """尽量拿到一个可用字体，取不到就退回内置位图字体。"""
        for candidate in (
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf",
        ):
            try:
                return ImageFont.truetype(candidate, self.font_size)
            except OSError:
                continue
        try:
            return ImageFont.load_default(size=self.font_size)  # Pillow >= 10.1
        except TypeError:  # pragma: no cover - 很旧的 Pillow
            return ImageFont.load_default()

    def _draw_noise_lines(self, draw: ImageDraw.ImageDraw) -> None:
        for _ in range(6):
            draw.line(
                (
                    random.randint(0, self.width),
                    random.randint(0, self.height),
                    random.randint(0, self.width),
                    random.randint(0, self.height),
                ),
                fill=(
                    random.randint(150, 220),
                    random.randint(150, 220),
                    random.randint(150, 220),
                ),
                width=1,
            )

    def _draw_noise_dots(self, draw: ImageDraw.ImageDraw) -> None:
        for _ in range(180):
            draw.point(
                (random.randint(0, self.width), random.randint(0, self.height)),
                fill=(
                    random.randint(120, 200),
                    random.randint(120, 200),
                    random.randint(120, 200),
                ),
            )

    def render(self, code: str) -> tuple[bytes, str]:
        image = Image.new("RGB", (self.width, self.height), (245, 246, 250))
        draw = ImageDraw.Draw(image)

        self._draw_noise_lines(draw)

        font = self._load_font()
        step = self.width // (len(code) + 1)
        for index, char in enumerate(code):
            draw.text(
                (
                    step * (index + 1) - step // 3 + random.randint(-3, 3),
                    random.randint(4, 12),
                ),
                char,
                font=font,
                fill=(
                    random.randint(20, 90),
                    random.randint(20, 90),
                    random.randint(90, 170),
                ),
            )

        self._draw_noise_dots(draw)

        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        return buffer.getvalue(), "image/png"


get_registry("captcha_renderer").register(ImageCaptchaRenderer())
