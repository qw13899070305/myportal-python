"""可拆卸性测试。

这套测试专门验证项目的核心设计：**每个零件都能单独摘掉**。
不是测业务功能，而是测"少了某一块，其它块还能不能活"。
"""

import sys
import types

import pytest

from backend.api.v1 import CORE_ROUTERS, EXTRA_ROUTERS, LOADED, SKIPPED, _include
from backend.extensions import REGISTRIES, describe_registries

# ---------------- API 路由聚合 ----------------


def test_all_api_modules_are_loaded():
    """所有声明的顶层 API 模块都应该成功挂载，没有静默丢失。"""
    assert SKIPPED == [], f"有模块被跳过: {SKIPPED}"

    top_level = {path for path, _, _ in CORE_ROUTERS} | {path for path, _, _ in EXTRA_ROUTERS}
    missing = top_level - set(LOADED)
    assert not missing, f"顶层模块没有挂载: {missing}"


def test_group_parts_are_loaded():
    """组内拆出来的子零件也必须全部挂载（两级可拆卸的第二级）。"""
    from backend.api.v1 import articles, auth, files

    top_level = {path for path, _, _ in CORE_ROUTERS} | {path for path, _, _ in EXTRA_ROUTERS}

    for group in (auth, articles, files):
        expected = {path for path, _, _ in group.PARTS}
        missing = expected - set(LOADED)
        assert not missing, f"{group.__name__} 的子零件没挂载: {missing}"

        # 子零件必须"名如其组"（auth_* / article_* / file_*），
        # 且不能是顶层模块本身，避免写错模块名却看起来加载成功
        stem = group.__name__.rsplit(".", 1)[-1].rstrip("s")
        for module_path in expected:
            short = module_path.rsplit(".", 1)[-1]
            assert short.startswith(stem + "_"), f"{short} 不属于 {group.__name__}"
            assert module_path not in top_level, f"{module_path} 不该重复挂在顶层"


def test_core_and_extra_are_separated():
    """核心模块（缺了必须报错）与扩展模块（缺了只警告）要分开管理。"""
    assert {path for path, _, _ in CORE_ROUTERS} & {path for path, _, _ in EXTRA_ROUTERS} == set()

    # 认证、文件、文章这几个基本盘必须在核心列表里
    core_names = {path for path, _, _ in CORE_ROUTERS}
    for required in (
        "backend.api.v1.auth",
        "backend.api.v1.files",
        "backend.api.v1.articles",
    ):
        assert required in core_names


def test_missing_extra_module_is_skipped(monkeypatch):
    """摘掉一个扩展模块：只应被跳过，不能抛异常。"""
    from fastapi import APIRouter

    parent = APIRouter()
    skipped_before = len(SKIPPED)

    ok = _include(
        parent,
        "backend.api.v1.definitely_not_exist",
        "/ghost",
        ["幽灵"],
        required=False,
    )
    assert ok is False
    assert len(SKIPPED) == skipped_before + 1
    assert "backend.api.v1.definitely_not_exist" in SKIPPED

    SKIPPED.pop()  # 清理，避免影响其它用例


def test_missing_core_module_raises(monkeypatch):
    """核心模块缺失必须直接报错，而不是静默降级。"""
    from fastapi import APIRouter

    with pytest.raises(ModuleNotFoundError):
        _include(
            APIRouter(),
            "backend.api.v1.definitely_not_exist",
            "/ghost",
            ["幽灵"],
            required=True,
        )


def test_module_without_router_is_skipped():
    """模块存在但没有 router 时，作为扩展应被跳过。"""
    from fastapi import APIRouter

    module_name = "backend.api.v1._no_router_here"
    module = types.ModuleType(module_name)
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setitem(sys.modules, module_name, module)
    try:
        ok = _include(APIRouter(), module_name, "/x", ["x"], required=False)
        assert ok is False
        assert module_name in SKIPPED
    finally:
        SKIPPED.remove(module_name)
        monkeypatch.undo()


# ---------------- 扩展注册表 ----------------


def test_preview_registry_is_registered_globally():
    """预览扩展应该出现在全局注册表索引里。"""
    assert "preview" in REGISTRIES
    listing = describe_registries()
    assert "preview" in listing
    assert "text" in listing["preview"]


# ---------------- 可选的挂载 ----------------


def test_mount_frontend_reports_missing_build(tmp_path):
    """前端没构建时，mount_frontend 应返回 False 而不是抛错。"""
    from fastapi import FastAPI

    from backend.spa import mount_frontend

    app = FastAPI()
    mounted = mount_frontend(app, candidates=(tmp_path / "nope",))
    assert mounted is False
    # 退化成了提示用的根路由
    assert any(getattr(route, "path", None) == "/" for route in app.routes)


def test_mount_frontend_uses_build_when_present(tmp_path):
    from fastapi import FastAPI

    from backend.spa import SPAStaticFiles, mount_frontend

    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "index.html").write_text("<html>ok</html>", encoding="utf-8")

    app = FastAPI()
    assert mount_frontend(app, candidates=(dist,)) is True
    assert any(isinstance(route.app, SPAStaticFiles) for route in app.routes)


def test_backend_paths_are_not_swallowed_by_spa_fallback(tmp_path):
    """``/api``、``/ws`` 找不到时**不能**回退成 index.html。

    以前写错的接口路径会返回 200 + HTML，前端只看到 JSON 解析失败，
    HEAD 请求也会被静态回退吃掉（手机下载管理器就是先发 HEAD 的）。
    """
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from backend.spa import mount_frontend

    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "index.html").write_text("<html>ok</html>", encoding="utf-8")

    app = FastAPI()
    mount_frontend(app, candidates=(dist,))

    with TestClient(app) as client:
        # 前端深层链接照旧回退到 index.html
        spa = client.get("/files")
        assert spa.status_code == 200
        assert spa.text == "<html>ok</html>"

        # 后端路径必须如实返回 404
        api = client.get("/api/v1/definitely/not/a/route")
        assert api.status_code == 404
        assert api.headers["content-type"].startswith("application/json")


def test_mount_socketio_is_optional():
    """socket.io 挂载失败不应该让应用起不来。"""
    from fastapi import FastAPI

    from backend.socketio.mount import mount_socketio

    app = FastAPI()
    assert mount_socketio(app) is True


def test_socketio_event_modules_are_discovered():
    """每个事件文件都应该被自动发现并注册。"""
    from backend.socketio import events
    from backend.socketio.handlers import sio

    assert events.SKIPPED == []
    loaded_names = {name.rsplit(".", 1)[1] for name in events.LOADED}
    assert {"connection", "message", "revoke"} <= loaded_names

    registered = set(sio.handlers["/"]) if hasattr(sio, "handlers") else set()
    for event in ("connect", "disconnect", "join", "send_message", "revoke_message"):
        assert event in registered, f"事件 {event} 没有注册"


# ---------------- 中间件 / 引导 ----------------


def test_max_body_middleware_rejects_oversized():
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from backend.middleware.max_body import MaxBodySizeMiddleware

    app = FastAPI()
    app.add_middleware(MaxBodySizeMiddleware, max_body=100)

    @app.post("/echo")
    async def echo():  # pragma: no cover - 不会真的被调用
        return {"ok": True}

    with TestClient(app) as client:
        big = client.post("/echo", content=b"x" * 200)
        assert big.status_code == 413

        small = client.post("/echo", content=b"x" * 10)
        assert small.status_code == 200


def test_max_body_middleware_tolerates_bad_header():
    """非法 Content-Length 应该交给下游处理，而不是 500。"""
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from backend.middleware.max_body import MaxBodySizeMiddleware

    app = FastAPI()
    app.add_middleware(MaxBodySizeMiddleware, max_body=100)

    @app.get("/ping")
    async def ping():
        return {"ok": True}

    with TestClient(app) as client:
        response = client.get("/ping", headers={"Content-Length": "abc"})
        assert response.status_code == 200


def test_bootstrap_created_builtin_roles(client, admin_headers):
    """启动引导应该把内置角色建出来并分配给管理员。

    这里通过接口断言（而不是直接开新事件循环调用 ensure_roles），
    因为应用引擎绑定在 TestClient 自己的事件循环上。
    """
    from backend.models.user import BUILTIN_ROLES

    assert {"admin", "user"} <= set(BUILTIN_ROLES)

    me = client.get("/api/v1/auth/me", headers=admin_headers)
    assert me.status_code == 200
    assert "admin" in me.json()["roles"]
