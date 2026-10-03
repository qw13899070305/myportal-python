"""监听 socket 构建与 uvicorn 启动（独立零件）。

**为什么需要自己建 socket**：uvicorn 默认走
``loop.create_server(host, port)``，而 asyncio 在创建 ``AF_INET6``
socket 时会强制设置 ``IPV6_V6ONLY = True``
（见 ``asyncio/base_events.py``）。结果就是 ``host="::"``
**只监听 IPv6**，IPv4 内网地址访问会直接 Connection refused ——
这正是"内网访问不到"的根因。

解决办法：自己绑好 socket（IPv4 + IPv6 各一个，互不冲突），
再用 ``sockets=[...]`` 传给 uvicorn。
"""

from __future__ import annotations

import errno
import socket
from contextlib import suppress

from backend.core.config import BASE_DIR
from backend.core.logger import logger

#: 表示"同时监听 IPv4 与 IPv6"的写法
DUAL_STACK_HOSTS = frozenset({"::", "*", "[::]"})

#: 监听队列长度
BACKLOG = 2048

#: 热重载只监视这些目录（相对项目根）。
#:
#: 为什么不用"监视整个项目 + 排除"：uvicorn 默认把整个工作目录都监视起来，
#: 而项目里的 ``.venv`` 有 3000+ 个 ``.py``（site-packages），
#: ``frontend/node_modules`` 里也藏着 ``.py``。
#: 更麻烦的是 ``.venv/lib64`` 是**符号链接**，靠 ``reload_excludes``
#: 的目录展开盖不住它 —— 实测改一个 site-packages 文件就会触发全量重载。
#:
#: 所以直接**白名单**：只监视后端代码目录。前端由 Vite 自己的 HMR 负责。
RELOAD_DIRS = ("backend",)

#: 兜底的排除规则（``__pycache__`` 这类即使在 backend 里也不该触发重载）
RELOAD_EXCLUDES = [
    ".venv/*",
    "venv/*",
    "env/*",
    "frontend/node_modules/*",
    "frontend/dist/*",
    ".git/*",
    "logs/*",
    "uploads/*",
    "__pycache__/*",
    ".pytest_cache/*",
    ".ruff_cache/*",
    ".mypy_cache/*",
    "*.pyc",
]


class ListenError(OSError):
    """所有监听地址都失败时抛出，带可读的排查提示。"""

    def __init__(self, port: int, errors: list[tuple[str, OSError]]) -> None:
        self.port = port
        self.errors = errors
        super().__init__(self._build_message())

    def _build_message(self) -> str:
        lines = [f"端口 {self.port} 无法监听（IPv4 与 IPv6 都失败）"]
        for family, exc in self.errors:
            lines.append(f"  {family}: {exc}")

        if any(getattr(exc, "errno", None) == errno.EADDRINUSE for _, exc in self.errors):
            lines += [
                "",
                "端口已被其它进程占用。先看看是谁在用：",
                f"    ss -tlnp | grep {self.port}",
                "停掉它，或者换个端口启动：",
                f"    PORT={self.port + 1} python app.py",
            ]
        return "\n".join(lines)


def _bind(
    family: socket.AddressFamily,
    address: str,
    port: int,
    *,
    v6only: bool = False,
) -> socket.socket:
    """创建一个已 bind + listen 的 socket。"""
    sock = socket.socket(family, socket.SOCK_STREAM)
    try:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        if family == socket.AF_INET6:
            # 显式指定，避免依赖系统默认值（asyncio 会强制设成 True）
            with suppress(OSError, AttributeError):
                sock.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, int(v6only))
        sock.bind((address, port))
        sock.listen(BACKLOG)
        sock.set_inheritable(True)
    except OSError:
        sock.close()
        raise
    return sock


def build_listeners(host: str, port: int) -> list[socket.socket]:
    """按配置生成监听 socket 列表。

    - ``"::"`` / ``"*"``       -> IPv4 + IPv6 各一个（真正的双栈，同一端口）
    - ``"0.0.0.0"``            -> 只监听 IPv4
    - 其它含 ``:`` 的地址       -> 只监听该 IPv6 地址
    - 其它                     -> 只监听该 IPv4 地址

    ``port=0`` 表示"随便给个空闲端口"：先绑 IPv6 拿到实际端口，
    再让 IPv4 用同一个端口，避免两个 socket 跑到不同端口上。
    """
    listeners: list[socket.socket] = []
    errors: list[tuple[str, OSError]] = []

    if host in DUAL_STACK_HOSTS:
        # IPv6 用 v6only=1：这样它和下面的 IPv4 socket 能共存于同一端口
        try:
            ipv6_sock = _bind(socket.AF_INET6, "::", port, v6only=True)
            listeners.append(ipv6_sock)
            logger.debug(f"已监听 IPv6: [::]:{ipv6_sock.getsockname()[1]}")
            if port == 0:
                # 以系统分配的端口为准，让 IPv4 也用它
                port = ipv6_sock.getsockname()[1]
        except OSError as exc:
            errors.append(("IPv6", exc))
            logger.warning(f"IPv6 监听失败（{exc}），将只监听 IPv4")
        try:
            listeners.append(_bind(socket.AF_INET, "0.0.0.0", port))
            logger.debug(f"已监听 IPv4: 0.0.0.0:{port}")
        except OSError as exc:
            errors.append(("IPv4", exc))
            logger.warning(f"IPv4 监听失败（{exc}）")
        if not listeners:
            raise ListenError(port, errors)
        return listeners

    is_v6 = ":" in host
    listeners.append(_bind(socket.AF_INET6 if is_v6 else socket.AF_INET, host, port, v6only=is_v6))
    return listeners


def describe_listeners(listeners: list[socket.socket]) -> str:
    """把监听到的地址拼成一行说明（给日志用）。"""
    parts = []
    for sock in listeners:
        try:
            address = sock.getsockname()
        except OSError:  # pragma: no cover
            continue
        host, port = address[0], address[1]
        parts.append(f"[{host}]:{port}" if ":" in host else f"{host}:{port}")
    return ", ".join(parts)


def reload_options() -> dict:
    """热重载的监视目录与排除规则。

    单独抽出来是为了能直接单测 —— ``serve(reload=True)`` 会真的启动
    reloader 并阻塞，不适合在测试里调用。
    """
    return {
        "reload_dirs": [str(BASE_DIR / name) for name in RELOAD_DIRS],
        "reload_excludes": list(RELOAD_EXCLUDES),
    }


def serve(
    app_import_string: str,
    *,
    host: str,
    port: int,
    reload: bool = False,
    reload_dirs: list[str] | None = None,
    reload_excludes: list[str] | None = None,
    **config_kwargs,
) -> None:
    """建好双栈 socket 后启动 uvicorn。

    ``app_import_string`` 必须是导入字符串（例如 ``"backend.main:app"``），
    因为 reload / workers 都依赖它。

    端口被占用等监听失败会打印可读提示并退出，而不是甩一段 traceback。

    热重载默认只监视项目根目录，并排除 ``.venv`` / ``node_modules`` 等
    重型目录（见 :data:`RELOAD_EXCLUDES`）。
    """
    import uvicorn

    try:
        listeners = build_listeners(host, port)
    except ListenError as exc:
        logger.error(str(exc))
        raise SystemExit(1) from None

    logger.info(f"监听地址: {describe_listeners(listeners)}")

    if reload:
        # 不显式指定的话 uvicorn 会监视整个 cwd，且没有任何排除规则
        for key, value in reload_options().items():
            config_kwargs.setdefault(key, value)

    config = uvicorn.Config(
        app_import_string,
        host=host,
        port=port,
        reload=reload,
        **config_kwargs,
    )
    server = uvicorn.Server(config)

    if reload:
        # reload 模式下由父进程持有 socket，子进程继承
        from uvicorn.supervisors import ChangeReload

        ChangeReload(config, target=server.run, sockets=listeners).run()
    else:
        server.run(sockets=listeners)


__all__ = [
    "BACKLOG",
    "DUAL_STACK_HOSTS",
    "RELOAD_DIRS",
    "RELOAD_EXCLUDES",
    "ListenError",
    "build_listeners",
    "describe_listeners",
    "reload_options",
    "serve",
]
