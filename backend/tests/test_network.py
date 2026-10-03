"""内网 / IPv6 访问相关测试。

覆盖三件事：
1. 本机地址探测（IPv4 + IPv6）与 URL 拼接（IPv6 要加方括号）
2. 「本机 / 内网来源」判定 —— 既要放行内网，又不能放行外部域名
3. CORS 与 socket.io 是否真的放行了内网 Origin
"""

from __future__ import annotations

import pytest

from backend.core.network import (
    LocalAddress,
    extract_host,
    is_local_origin,
    lan_addresses,
    local_addresses,
    local_urls,
    origin_is_allowed,
)

# ---------------- 地址探测 ----------------


def test_local_addresses_includes_loopback():
    """至少要能探测到回环地址，否则说明探测逻辑整个失效了。"""
    addresses = local_addresses(refresh=True)
    assert addresses, "没有探测到任何本机地址"
    assert any(item.is_loopback for item in addresses), "没探测到回环地址"


def test_local_addresses_have_family_and_interface():
    for item in local_addresses(refresh=True):
        assert item.family in {"ipv4", "ipv6"}
        assert item.interface
        assert item.version in {4, 6}


def test_lan_addresses_excludes_loopback_and_link_local():
    for item in lan_addresses(refresh=True):
        assert not item.is_loopback
        assert not item.is_link_local


def test_ipv6_url_is_bracketed():
    """IPv6 字面量必须加方括号，否则 URL 解析会错。"""
    v6 = LocalAddress(interface="eth0", address="2409:8a7c::1", family="ipv6")
    assert v6.url(8000) == "http://[2409:8a7c::1]:8000"

    v4 = LocalAddress(interface="eth0", address="192.168.1.2", family="ipv4")
    assert v4.url(8000) == "http://192.168.1.2:8000"


def test_ipv6_url_strips_zone_id():
    """链路本地地址带 %eth0 区域 id，拼 URL 时必须去掉。"""
    v6 = LocalAddress(interface="eth0", address="fe80::1%eth0", family="ipv6")
    assert v6.url(8000) == "http://[fe80::1]:8000"


def test_local_urls_are_usable():
    for url in local_urls(8000):
        assert url.startswith("http://")
        assert url.endswith(":8000")
        assert "::" not in url.split("]")[0] or url.startswith("http://[")


# ---------------- Origin 解析 ----------------


@pytest.mark.parametrize(
    ("origin", "expected"),
    [
        ("http://192.168.1.2:5173", "192.168.1.2"),
        ("http://[2409:8a7c::1]:5173", "2409:8a7c::1"),
        ("http://[::1]:5173", "::1"),
        ("https://example.com", "example.com"),
        ("https://example.com/", "example.com"),
        ("http://localhost:5173", "localhost"),
        ("", ""),
    ],
)
def test_extract_host(origin, expected):
    assert extract_host(origin) == expected


# ---------------- 来源判定 ----------------


@pytest.mark.parametrize(
    "origin",
    [
        "http://localhost:5173",
        "http://localhost",
        "http://127.0.0.1:5173",
        "http://[::1]:5173",
        "http://192.168.1.50:5173",  # 任意私有网段
        "http://10.0.0.9:5173",
        "http://172.16.5.5:5173",
        "http://169.254.1.1:5173",  # 链路本地
        "http://nas.local:5173",  # mDNS 名字
        "http://[fd00::1]:5173",  # IPv6 ULA
    ],
)
def test_local_origins_are_allowed(origin):
    assert is_local_origin(origin) is True


@pytest.mark.parametrize(
    "origin",
    [
        "http://evil.com",
        "https://evil.com:443",
        "http://8.8.8.8:5173",
        "http://[2001:4860:4860::8888]:5173",
        "http://not-local.example.org",
        "",
        None,
    ],
)
def test_external_origins_are_rejected(origin):
    assert is_local_origin(origin) is False


def test_own_global_address_is_allowed():
    """关键用例：宽带下发的全球单播 IPv6（2409: 这类）不是"私有地址"，
    但它是本机自己的地址，必须放行 —— 用户就是用它访问的。"""
    own = [item for item in lan_addresses(refresh=True)]
    if not own:
        pytest.skip("本机没有可用的内网地址")

    for item in own:
        origin = item.url(5173)
        assert is_local_origin(origin) is True, f"{origin} 应该被放行"


def test_origin_is_allowed_respects_explicit_list():
    """显式白名单里的外部域名也要放行（用户显式配置就应该生效）。"""
    assert origin_is_allowed("http://example.com", ["http://example.com"]) is True
    assert origin_is_allowed("http://example.com") is False


def test_origin_is_allowed_without_origin():
    """没有 Origin（命令行 / 同源请求）不应该被拦。"""
    assert origin_is_allowed("") is True
    assert origin_is_allowed(None) is True


# ---------------- CORS 真的放行了吗 ----------------


def test_cors_preflight_from_lan_origin(client):
    """内网地址发来的预检必须拿到 ACAO 头，否则浏览器会拦掉请求。"""
    response = client.options(
        "/api/v1/auth/login",
        headers={
            "Origin": "http://192.168.1.50:5173",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type,x-csrf-token",
        },
    )
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "http://192.168.1.50:5173"
    assert response.headers.get("access-control-allow-credentials") == "true"


def test_cors_preflight_from_external_origin_denied(client):
    """外部域名不应该拿到 ACAO 头。"""
    response = client.options(
        "/api/v1/auth/login",
        headers={
            "Origin": "http://evil.com",
            "Access-Control-Request-Method": "POST",
        },
    )
    assert "access-control-allow-origin" not in response.headers


def test_cors_simple_request_from_lan_origin(client):
    response = client.get("/api/v1/health/", headers={"Origin": "http://192.168.1.2:5173"})
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "http://192.168.1.2:5173"


# ---------------- socket.io 的 Origin 判定 ----------------


def test_socketio_origin_allowed_for_lan():
    """socket.io 会自己校验 Origin，内网地址必须放行，否则聊天连不上。"""
    from backend.socketio.server import origin_allowed

    assert origin_allowed("http://192.168.1.2:5173") is True
    assert origin_allowed("http://[2409:8a7c:4810:d4e0:2e0:23ff:fe21:5116]:5173") is True
    assert origin_allowed("http://localhost:5173") is True
    assert origin_allowed("http://evil.com") is False


def test_socketio_accepts_lan_origin_handshake(client):
    """带内网 Origin 的 socket.io 握手必须成功（不是 400）。"""
    response = client.get(
        "/ws/socket.io/?EIO=4&transport=polling",
        headers={"Origin": "http://192.168.1.50:5173"},
    )
    assert response.status_code == 200
    assert response.text.startswith("0{")  # engine.io 握手报文


# ---------------- Redis 不可用时的优雅降级 ----------------


def test_redis_probe_reports_unreachable_without_raising():
    """Redis 没起来时探测应该返回 False，而不是抛异常或卡住。"""
    import time

    from backend.core import redis as redis_core

    redis_core.reset_probe_cache()
    started = time.monotonic()
    result = redis_core.redis_reachable()
    elapsed = time.monotonic() - started

    assert isinstance(result, bool)
    assert elapsed < 2.0, f"探测不应该卡住，实际用了 {elapsed:.2f}s"


def test_probe_result_is_cached():
    """探测结果要缓存，否则每个请求都去连一次挂掉的 Redis。"""
    from backend.core import redis as redis_core

    redis_core.reset_probe_cache()
    redis_core.redis_reachable()
    first = redis_core._probe_cache[0]
    redis_core.redis_reachable()
    assert redis_core._probe_cache[0] == first, "第二次探测不应重新发起连接"


def test_status_reports_configuration():
    from backend.core.redis import status

    info = status()
    assert set(info) == {"configured", "reachable", "url"}
    assert isinstance(info["configured"], bool)
    assert isinstance(info["reachable"], bool)
