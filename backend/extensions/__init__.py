"""可拆卸扩展件。

每个子包都是一类"可以整包摘掉"的功能：

- :mod:`backend.extensions.preview` —— 文件在线预览（每种格式一个文件）

新增一类扩展只需要：
1. 建一个子包
2. 在包里放若干模块，模块导入时调用 ``get_registry("类型名").register(...)``
3. 在 ``__init__.py`` 里 ``registry.discover(__name__)``
"""

from backend.extensions.registry import (
    REGISTRIES,
    ExtensionRegistry,
    describe_registries,
    discover_extensions,
    get_registry,
)

__all__ = [
    "REGISTRIES",
    "ExtensionRegistry",
    "describe_registries",
    "discover_extensions",
    "get_registry",
]
