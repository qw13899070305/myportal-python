"""监听 socket 构建测试。

这个文件专门守住一个曾经踩过的坑：
**uvicorn 默认经 asyncio 建 socket，会被强制设成 ``IPV6_V6ONLY=1``**，
导致 ``host="::"`` 只监听 IPv6，IPv4 内网访问直接 Connection refused。

所以这里直接建真 socket、真连接，验证 IPv4 与 IPv6 都能连上。
"""

from __future__ import annotations

import socket

import pytest

from backend.core.server import build_listeners, describe_listeners


def _close_all(listeners):
    for sock in listeners:
        sock.close()


def _connect(family, address, port, timeout=2.0) -> bool:
    """真的去连一下，返回是否成功。"""
    try:
        with socket.socket(family, socket.SOCK_STREAM) as client:
            client.settimeout(timeout)
            client.connect((address, port))
        return True
    except OSError:
        return False


# ---------------- 地址族选择 ----------------


def test_dual_stack_host_creates_both_families():
    """``::`` 必须同时给出 IPv4 与 IPv6 两个监听 socket。"""
    listeners = build_listeners("::", 0)
    try:
        families = {sock.family for sock in listeners}
        assert socket.AF_INET6 in families, "缺少 IPv6 监听"
        assert socket.AF_INET in families, "缺少 IPv4 监听（这正是内网访问不到的根因）"
    finally:
        _close_all(listeners)


def test_wildcard_host_creates_both_families():
    listeners = build_listeners("*", 0)
    try:
        assert {sock.family for sock in listeners} == {socket.AF_INET, socket.AF_INET6}
    finally:
        _close_all(listeners)


def test_ipv4_only_host():
    listeners = build_listeners("0.0.0.0", 0)
    try:
        assert [sock.family for sock in listeners] == [socket.AF_INET]
    finally:
        _close_all(listeners)


def test_explicit_ipv6_host():
    listeners = build_listeners("::1", 0)
    try:
        assert [sock.family for sock in listeners] == [socket.AF_INET6]
    finally:
        _close_all(listeners)


def test_explicit_ipv4_host_is_bound_to_that_address():
    listeners = build_listeners("127.0.0.1", 0)
    try:
        assert listeners[0].getsockname()[0] == "127.0.0.1"
    finally:
        _close_all(listeners)


# ---------------- 真的能连上吗 ----------------


def test_dual_stack_accepts_ipv4_and_ipv6_connections():
    """核心用例：双栈监听必须 IPv4 / IPv6 都能连。

    这里用真 socket 真连接，而不是只看地址族 —— 因为坑就出在
    socket 选项上，光看地址族是发现不了的。
    """
    listeners = build_listeners("::", 0)
    port = listeners[0].getsockname()[1]
    try:
        assert _connect(socket.AF_INET, "127.0.0.1", port), "IPv4 连不上"
        assert _connect(socket.AF_INET6, "::1", port), "IPv6 连不上"
    finally:
        _close_all(listeners)


def test_ipv6_listener_has_v6only_enabled_so_it_can_coexist():
    """IPv6 socket 必须显式 v6only=1，否则无法与 IPv4 socket 共用端口。"""
    listeners = build_listeners("::", 0)
    try:
        v6 = [sock for sock in listeners if sock.family == socket.AF_INET6]
        assert v6, "没有 IPv6 监听"
        assert v6[0].getsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY) == 1
    finally:
        _close_all(listeners)


def test_listeners_are_set_inheritable_for_reload():
    """reload / workers 模式靠子进程继承 socket。"""
    listeners = build_listeners("::", 0)
    try:
        assert all(sock.get_inheritable() for sock in listeners)
    finally:
        _close_all(listeners)


def test_listeners_share_the_same_port():
    listeners = build_listeners("::", 0)
    try:
        ports = {sock.getsockname()[1] for sock in listeners}
        assert len(ports) == 1, f"IPv4 与 IPv6 应该监听同一端口，实际 {ports}"
    finally:
        _close_all(listeners)


def test_port_conflict_raises():
    """端口被占用时应该报错，而不是悄悄只监听一半。"""
    first = build_listeners("0.0.0.0", 0)
    port = first[0].getsockname()[1]
    try:
        with pytest.raises(OSError):
            build_listeners("0.0.0.0", port)
    finally:
        _close_all(first)


def test_describe_listeners_formats_ipv6_with_brackets():
    listeners = build_listeners("::", 0)
    try:
        text = describe_listeners(listeners)
        assert "[::]:" in text, f"IPv6 应该带方括号: {text}"
        assert "0.0.0.0:" in text
    finally:
        _close_all(listeners)


# ---------------- 热重载的监视范围 ----------------


def test_reload_excludes_cover_heavy_directories():
    """热重载必须排除 .venv / node_modules，否则会疯狂误触发重载。

    项目里的 .venv 有 3000+ 个 .py，uvicorn 默认把它们全监视起来。
    """
    from backend.core.server import RELOAD_EXCLUDES

    for pattern in (".venv/*", "frontend/node_modules/*", ".git/*"):
        assert pattern in RELOAD_EXCLUDES, f"缺少排除规则 {pattern}"


def test_reload_options_are_explicit():
    """reload 模式下必须显式给出监视目录与排除规则。

    这里测 reload_options() 而不是 serve(reload=True) ——
    后者会真的启动 reloader 并阻塞。
    """
    from backend.core.server import reload_options

    options = reload_options()
    dirs = options["reload_dirs"]
    assert dirs, "必须显式指定监视目录，否则 uvicorn 会监视整个 cwd"

    # 必须是白名单：只监视后端代码，绝不能是项目根（否则会连 .venv 一起监视）
    from backend.core.config import BASE_DIR

    assert str(BASE_DIR) not in dirs, "监视项目根会把 .venv 里 3000+ 个 .py 也带上"
    assert all(d.startswith(str(BASE_DIR)) for d in dirs)
    assert any(d.endswith("backend") for d in dirs), "至少要监视 backend/"
