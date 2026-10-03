"""本机网络地址探测与「内网来源」判定（独立零件）。

解决的问题：**内网（含 IPv6）访问**。

- :func:`local_addresses` —— 列出本机所有地址（IPv4 + IPv6，排除回环）
- :func:`local_urls` —— 生成可以直接点开的访问地址
- :func:`is_local_origin` —— 判断某个 ``Origin`` 是不是"内网/本机来源"

关于判定规则，有个容易踩的坑：很多宽带下发的 IPv6 是
**全球单播**（例如 ``2409:`` 开头），``ipaddress.is_private`` 判不出它是
"内网"。所以除了私有网段，还必须放行**本机自己拥有的地址**——
用户就是通过那个地址访问我们的。
"""

from __future__ import annotations

import ipaddress
import re
import socket
import subprocess
import time
from dataclasses import dataclass

from backend.core.logger import logger

#: 本机地址缓存的有效期（秒）。IPv6 隐私扩展会定期换地址，所以不能永久缓存
_CACHE_TTL = 30.0

_ip_cache: tuple[float, list[LocalAddress]] = (0.0, [])

#: 解析 ``ip -o addr show`` 的一行
_IP_LINE = re.compile(
    r"^\d+:\s+(?P<iface>\S+)\s+(?P<family>inet6?)\s+"
    r"(?P<address>[0-9a-fA-F:.]+)/(?P<prefix>\d+)\s+(?P<rest>.*)$"
)


@dataclass(frozen=True)
class LocalAddress:
    """本机的一个网络地址。"""

    interface: str
    address: str
    family: str  # "ipv4" / "ipv6"
    prefix: int = 0
    scope: str = "global"

    @property
    def is_loopback(self) -> bool:
        try:
            return ipaddress.ip_address(self.address.split("%")[0]).is_loopback
        except ValueError:
            return False

    @property
    def is_link_local(self) -> bool:
        try:
            return ipaddress.ip_address(self.address.split("%")[0]).is_link_local
        except ValueError:
            return False

    @property
    def version(self) -> int:
        return 6 if self.family == "ipv6" else 4

    def url(self, port: int, scheme: str = "http") -> str:
        """拼成可以直接访问的 URL（IPv6 需要方括号）。"""
        host = self.address.split("%")[0]
        if self.version == 6:
            return f"{scheme}://[{host}]:{port}"
        return f"{scheme}://{host}:{port}"


def _parse_ip_output(output: str) -> list[LocalAddress]:
    """解析 ``ip -o addr show`` 的输出。"""
    found: list[LocalAddress] = []
    for line in output.splitlines():
        match = _IP_LINE.match(line.strip())
        if not match:
            continue
        rest = match.group("rest")
        scope = "global"
        if " scope " in f" {rest}":
            scope_match = re.search(r"scope (\S+)", rest)
            if scope_match:
                scope = scope_match.group(1)
        found.append(
            LocalAddress(
                interface=match.group("iface"),
                address=match.group("address"),
                family="ipv6" if match.group("family") == "inet6" else "ipv4",
                prefix=int(match.group("prefix")),
                scope=scope,
            )
        )
    return found


def _fallback_addresses() -> list[LocalAddress]:
    """没有 ``ip`` 命令时的兜底：至少把主机名解析出的地址拿到。"""
    found: list[LocalAddress] = []
    try:
        for info in socket.getaddrinfo(socket.gethostname(), None):
            family, _, _, _, sockaddr = info
            address = sockaddr[0]
            if any(item.address == address for item in found):
                continue
            found.append(
                LocalAddress(
                    interface="(hostname)",
                    address=address,
                    family="ipv6" if family == socket.AF_INET6 else "ipv4",
                )
            )
    except OSError:
        pass
    return found


def local_addresses(refresh: bool = False) -> list[LocalAddress]:
    """本机所有网络地址（带 30 秒缓存）。"""
    global _ip_cache
    now = time.time()
    if not refresh and now - _ip_cache[0] < _CACHE_TTL:
        return _ip_cache[1]

    addresses: list[LocalAddress] = []
    try:
        result = subprocess.run(
            ["ip", "-o", "addr", "show"],
            capture_output=True,
            text=True,
            timeout=3,
            check=False,
        )
        if result.returncode == 0:
            addresses = _parse_ip_output(result.stdout)
    except (OSError, subprocess.SubprocessError):
        pass

    if not addresses:
        addresses = _fallback_addresses()

    _ip_cache = (now, addresses)
    return addresses


def lan_addresses(refresh: bool = False) -> list[LocalAddress]:
    """可以用来对外提供服务的地址（去掉回环与链路本地）。"""
    return [
        item
        for item in local_addresses(refresh=refresh)
        if not item.is_loopback and not item.is_link_local
    ]


def local_ip_set(refresh: bool = False) -> set[str]:
    """本机拥有的 IP 集合（去掉区域 id 与 IPv4-mapped 前缀）。"""
    result: set[str] = set()
    for item in local_addresses(refresh=refresh):
        host = item.address.split("%")[0]
        result.add(host)
        # 同时登记展开形式，避免压缩写法对不上
        try:
            result.add(str(ipaddress.ip_address(host)))
        except ValueError:
            continue
    return result


def local_urls(port: int, scheme: str = "http") -> list[str]:
    """内网可直接访问的地址列表。"""
    return [item.url(port, scheme) for item in lan_addresses()]


def extract_host(origin: str) -> str:
    """从 ``http://[::1]:5173`` 这类 Origin 里取出主机部分。"""
    if not origin:
        return ""
    value = origin.strip()
    if "//" in value:
        value = value.split("//", 1)[1]
    value = value.split("/", 1)[0]

    if value.startswith("["):  # IPv6 字面量
        end = value.find("]")
        return value[1:end] if end != -1 else value.lstrip("[")

    return value.rsplit(":", 1)[0] if ":" in value else value


def is_local_origin(origin: str | None) -> bool:
    """这个 Origin 是不是"本机 / 内网"来源。

    放行三类：

    1. ``localhost`` / ``*.local``
    2. 回环、私有网段、链路本地、IPv6 ULA
    3. **本机自己拥有的地址** —— 关键的一条：宽带下发的 IPv6
       （``2409:`` 这类全球单播）不属于前三类，但用户就是用它访问的
    """
    host = extract_host(origin or "")
    if not host:
        return False

    lowered = host.lower()
    if lowered in {"localhost", "localhost.localdomain"} or lowered.endswith(".local"):
        return True

    # 去掉 IPv6 区域 id
    plain = host.split("%")[0]
    try:
        ip = ipaddress.ip_address(plain)
    except ValueError:
        # 不是 IP，只可能是主机名 —— 拿它和本机主机名比一比
        return lowered == socket.gethostname().lower()

    if ip.is_loopback or ip.is_private or ip.is_link_local:
        return True
    if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped is not None:
        return ip.ipv4_mapped.is_loopback or ip.ipv4_mapped.is_private

    return plain in local_ip_set()


def origin_is_allowed(origin: str | None, extra: list[str] | None = None) -> bool:
    """综合判定：显式配置的 Origin 或内网来源都放行。"""
    if not origin:
        return True  # 没有 Origin（命令行 / 同源）不拦
    if extra and origin in extra:
        return True
    return is_local_origin(origin)


def describe(port: int, scheme: str = "http") -> str:
    """给启动日志用的多行说明。"""
    items = lan_addresses()
    if not items:
        return "  （没有探测到可用的内网地址）"
    lines = []
    for item in items:
        lines.append(f"  {item.url(port, scheme)}   [{item.interface} {item.family}]")
    return "\n".join(lines)


def log_listening(port: int, scheme: str = "http", refresh: bool = True) -> list[str]:
    """把可访问地址打进日志，并返回这些地址。"""
    urls = local_urls(port, scheme)
    logger.info(
        f"可从以下地址访问本服务（监听 {port}）：\n"
        + (describe(port, scheme) if urls else "  （没有探测到可用的内网地址）")
    )
    return urls


__all__ = [
    "LocalAddress",
    "describe",
    "extract_host",
    "is_local_origin",
    "lan_addresses",
    "local_addresses",
    "local_ip_set",
    "local_urls",
    "log_listening",
    "origin_is_allowed",
]
