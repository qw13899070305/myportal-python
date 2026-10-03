"""可拆卸扩展的通用注册表。

设计目标：**任何扩展件被摘掉，其余功能都必须照常工作**。

- 注册：扩展模块在被导入时调用 :meth:`ExtensionRegistry.register`
- 发现：:meth:`ExtensionRegistry.discover` 导入包内全部模块，
  某一个模块导入失败（缺依赖、语法错误……）只会被跳过并记一条日志，
  不会影响其它扩展
- 查找：失败一律返回 ``None``，由调用方决定降级行为

用法::

    registry = ExtensionRegistry("preview")
    registry.discover("backend.extensions.preview")
"""

from __future__ import annotations

import importlib
import pkgutil
from collections.abc import Callable, Iterable, Iterator
from typing import Generic, TypeVar

from backend.core.logger import logger

T = TypeVar("T")


class ExtensionRegistry(Generic[T]):
    """一类扩展件的注册表。"""

    def __init__(self, kind: str, description: str = "") -> None:
        self.kind = kind
        self.description = description
        self._items: list[T] = []
        self._by_name: dict[str, T] = {}

    # ---------------- 注册 ----------------

    def register(self, item: T, name: str | None = None) -> T:
        """注册一个扩展件（重复名字会覆盖，方便热重载）。"""
        key = name or getattr(item, "name", None) or type(item).__name__
        if key in self._by_name:
            self._items[self._items.index(self._by_name[key])] = item
        else:
            self._items.append(item)
        self._by_name[key] = item
        return item

    def unregister(self, name: str) -> bool:
        """摘掉一个扩展件，返回是否存在。"""
        item = self._by_name.pop(name, None)
        if item is None:
            return False
        self._items.remove(item)
        return True

    # ---------------- 自动发现 ----------------

    def discover(self, package: str, skip: Iterable[str] = ()) -> int:
        """导入 ``package`` 下的全部子模块，返回成功导入的数量。

        ``skip`` 里的模块名会被跳过（通常是 ``base`` 之类只放基类的模块）。
        导入失败的模块只会被记录，不影响其它扩展。

        注意：扩展模块内部是通过 ``get_registry(kind)`` 取注册表再注册的，
        所以本方法只对**该类型的全局注册表**有意义；一般直接用
        :func:`discover_extensions` 就好。
        """
        skipped = set(skip) | {"__init__"}
        try:
            root = importlib.import_module(package)
        except Exception as exc:  # pragma: no cover - 包本身导入失败
            logger.warning(f"[{self.kind}] 扩展包 {package} 导入失败: {exc}")
            return 0

        loaded = 0
        for module_info in pkgutil.iter_modules(root.__path__):
            if module_info.name in skipped:
                continue
            full_name = f"{package}.{module_info.name}"
            try:
                importlib.import_module(full_name)
                loaded += 1
            except Exception as exc:
                # 单个扩展坏掉/缺依赖时静默降级，这是"可拆卸"的关键
                logger.warning(f"[{self.kind}] 跳过扩展 {full_name}: {exc}")
        logger.debug(f"[{self.kind}] 已加载 {loaded} 个扩展（来自 {package}）")
        return loaded

    # ---------------- 查询 ----------------

    @property
    def items(self) -> list[T]:
        return list(self._items)

    @property
    def names(self) -> list[str]:
        return list(self._by_name)

    def get(self, name: str) -> T | None:
        return self._by_name.get(name)

    def find(self, predicate: Callable[[T], bool]) -> T | None:
        """返回第一个满足条件的扩展件。"""
        for item in self._items:
            try:
                if predicate(item):
                    return item
            except Exception as exc:  # pragma: no cover - 扩展自身实现有误
                logger.warning(f"[{self.kind}] 扩展 {item!r} 判定失败: {exc}")
        return None

    def sorted_items(self, key: Callable[[T], object] | None = None) -> list[T]:
        """按 key 排序后的扩展列表（不改变内部顺序）。"""
        return sorted(self._items, key=key) if key else list(self._items)

    def __len__(self) -> int:
        return len(self._items)

    def __iter__(self) -> Iterator[T]:
        return iter(self._items)

    def __contains__(self, name: object) -> bool:
        return name in self._by_name


#: 全局注册表索引：扩展类型 -> 注册表，便于统一查看/热插拔
REGISTRIES: dict[str, ExtensionRegistry] = {}


def get_registry(kind: str, description: str = "") -> ExtensionRegistry:
    """按类型取（或创建）全局注册表。"""
    if kind not in REGISTRIES:
        REGISTRIES[kind] = ExtensionRegistry(kind, description)
    return REGISTRIES[kind]


def discover_extensions(
    package: str,
    kind: str,
    description: str = "",
    skip: Iterable[str] = (),
) -> ExtensionRegistry:
    """按类型取**全局**注册表并发现扩展（推荐用法）。

    扩展模块内部是通过 ``get_registry(kind)`` 拿到注册表再注册的，
    因此必须使用同一个全局实例，不能在本地 new 一个再 discover。
    """
    registry = get_registry(kind, description)
    registry.discover(package, skip=skip)
    return registry


def describe_registries() -> dict[str, list[str]]:
    """列出所有注册表及其扩展，供 /health 之类的自检接口使用。"""
    return {kind: registry.names for kind, registry in REGISTRIES.items()}
