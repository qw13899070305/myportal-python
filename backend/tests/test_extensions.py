"""扩展注册表测试。

重点验证"可拆卸"这个核心性质：
- 某个扩展模块导入失败时，其它扩展照常工作
- 按优先级匹配，兜底扩展只在最后生效
- 摘掉扩展后查找返回 None，而不是抛异常
"""

import textwrap

from backend.extensions.preview import find_handler, registry, supported_extensions
from backend.extensions.registry import ExtensionRegistry, get_registry


class Dummy:
    def __init__(self, name, priority=0, matches_all=False):
        self.name = name
        self.priority = priority
        self._matches_all = matches_all

    def matches(self, ext):
        return self._matches_all or ext == f".{self.name}"


# ---------------- 预览扩展包 ----------------

EXPECTED_HANDLERS = {
    ".txt": "TextPreview",
    ".md": "TextPreview",
    ".csv": "TextPreview",
    ".json": "TextPreview",
    ".log": "TextPreview",
    ".png": "ImagePreview",
    ".jpg": "ImagePreview",
    ".gif": "ImagePreview",
    ".pdf": "PdfPreview",
    ".docx": "WordPreview",
    ".xlsx": "ExcelPreview",
    ".pptx": "PptPreview",
}


def test_preview_extensions_are_loaded():
    """每个格式扩展都应该被自动发现并注册。"""
    loaded = {type(handler).__name__ for handler in registry}
    for expected in set(EXPECTED_HANDLERS.values()):
        assert expected in loaded, f"缺少预览扩展 {expected}"
    assert "FallbackPreview" in loaded


def test_each_extension_claims_the_right_formats():
    for ext, handler_name in EXPECTED_HANDLERS.items():
        handler = find_handler(ext)
        assert handler is not None, f"{ext} 没有匹配到任何扩展"
        assert type(handler).__name__ == handler_name, f"{ext} 匹配到了 {handler!r}"


def test_fallback_only_matches_unknown_formats():
    for ext in (".exe", ".doc", ".xls", ".ppt", ".zip", ""):
        handler = find_handler(ext)
        assert type(handler).__name__ == "FallbackPreview", f"{ext} 不该被具体扩展认领"

    # 已知格式绝不能被兜底扩展抢走
    assert type(find_handler(".pdf")).__name__ == "PdfPreview"
    assert type(find_handler(".xlsx")).__name__ == "ExcelPreview"


def test_supported_extensions_excludes_fallback():
    supported = supported_extensions()
    assert ".docx" in supported
    assert ".pdf" in supported
    # 兜底扩展不声明任何扩展名
    assert "" not in supported


def test_pdf_extension_exposes_optional_capabilities():
    """PDF 分页是"可选能力"，用鸭子类型访问。"""
    handler = find_handler(".pdf")
    assert hasattr(handler, "page_count")
    assert hasattr(handler, "render_page")

    # 其它扩展没有这个能力，接口层会据此给出 400
    assert not hasattr(find_handler(".txt"), "render_page")


# ---------------- 注册表本身的容错 ----------------


def test_registry_register_and_unregister():
    reg = ExtensionRegistry("test")
    item = Dummy("alpha")
    reg.register(item)
    assert "alpha" in reg
    assert reg.get("alpha") is item

    assert reg.unregister("alpha") is True
    assert reg.get("alpha") is None
    assert reg.unregister("alpha") is False


def test_registry_skips_broken_extension(tmp_path, monkeypatch):
    """一个扩展模块导入失败，绝不能影响其它扩展。"""
    package = tmp_path / "brokenpkg"
    package.mkdir()
    (package / "__init__.py").write_text("", encoding="utf-8")
    (package / "good.py").write_text(
        textwrap.dedent(
            """
            from backend.extensions.registry import get_registry

            class Good:
                name = "good"

            get_registry("brokenpkg").register(Good())
            """
        ),
        encoding="utf-8",
    )
    (package / "bad.py").write_text("raise RuntimeError('这个扩展坏掉了')\n", encoding="utf-8")

    monkeypatch.syspath_prepend(str(tmp_path))
    # 扩展内部是通过 get_registry(kind) 注册的，所以要用同一个全局实例
    reg = get_registry("brokenpkg")
    loaded = reg.discover("brokenpkg")

    assert loaded == 1, "坏掉的扩展应被跳过，只加载好的那个"
    assert "good" in reg


def test_registry_find_returns_none_when_empty():
    reg = ExtensionRegistry("empty")
    assert reg.find(lambda item: True) is None
    assert reg.sorted_items() == []


def test_registry_sorted_items_respects_priority():
    reg = ExtensionRegistry("ordered")
    low = Dummy("low", priority=-100, matches_all=True)
    high = Dummy("high", priority=10)
    reg.register(low)
    reg.register(high)

    ordered = reg.sorted_items(key=lambda item: -item.priority)
    assert ordered[0] is high
    assert ordered[-1] is low


def test_render_preview_never_raises_for_unknown_format(tmp_path):
    """未知格式走兜底扩展，返回提示页而不是抛异常。"""
    from backend.extensions.preview import render_preview

    target = tmp_path / "weird.unknown"
    target.write_bytes(b"data")

    preview = render_preview(target, ".unknown")
    assert preview is not None
    assert preview.kind == "html"
    assert "暂不支持在线预览" in preview.html


# ---------------- 优雅降级：零件被摘掉时接口的行为 ----------------


def test_captcha_endpoint_returns_503_without_renderer(client, monkeypatch):
    """验证码渲染器被摘掉时，接口应返回 503 而不是 500。"""
    from backend.api.v1 import auth_captcha

    def _boom():
        raise RuntimeError("验证码服务不可用")

    # 只替换服务层实现即可：限流装饰器是运行时查表调用的。
    # 注意不要动 get_captcha 的 __wrapped__，那会破坏 FastAPI 读到的函数签名。
    monkeypatch.setattr(auth_captcha.captcha_service, "create_captcha", _boom)

    response = client.get("/api/v1/auth/captcha")
    assert response.status_code == 503
    assert "不可用" in response.json()["detail"]


def test_captcha_endpoint_works_normally(client):
    """正常情况下返回 PNG 并带上 X-Captcha-Id。"""
    response = client.get("/api/v1/auth/captcha")
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"
    assert response.headers.get("X-Captcha-Id")
    assert response.content[:8] == b"\x89PNG\r\n\x1a\n"


def test_search_falls_back_to_next_backend(monkeypatch):
    """高优先级后端报错时应自动降级到下一个后端。"""
    import asyncio

    from backend.extensions import search as search_ext

    class Broken:
        name = "broken"
        priority = 999

        def available(self):
            return True

        async def search(self, query, page=1, limit=10):
            raise RuntimeError("后端挂了")

    class Working:
        name = "working"
        priority = 0

        def available(self):
            return True

        async def search(self, query, page=1, limit=10):
            return search_ext.SearchResult(total=0, items=[], engine=self.name)

    monkeypatch.setattr(search_ext, "backends", lambda: [Broken(), Working()])
    result = asyncio.run(search_ext.search("任意关键词"))
    assert result.engine == "working", "应降级到可用的后端"
