"""pytest 全局配置与公共 fixture。

所有环境变量都必须在导入 ``backend`` 之前设置好，因为
``backend.core.config.settings`` 是模块级单例。
"""

import logging
import os
import shutil
import tempfile
import uuid

import pytest

# ---------- 测试环境（必须在导入应用之前完成）----------
TEST_ROOT = tempfile.mkdtemp(prefix="myportal-test-")

os.environ["SECRET_KEY"] = "pytest-secret-key-0123456789-abcdefghijklmnop"
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{TEST_ROOT}/test.db"
os.environ["UPLOAD_DIR"] = f"{TEST_ROOT}/uploads"
os.environ["REDIS_URL"] = ""
os.environ["REDIS_ENABLED"] = "false"
os.environ["DEBUG"] = "false"
os.environ["LOG_LEVEL"] = "WARNING"
os.environ["RATE_LIMIT_ENABLED"] = "false"
os.environ["ADMIN_USERNAME"] = "admin"
os.environ["ADMIN_PASSWORD"] = "AdminPass1!"
os.environ["ADMIN_EMAIL"] = "admin@example.com"

USER_PASSWORD = "TestPass1!"
ADMIN_PASSWORD = "AdminPass1!"

# TestClient 关闭事件循环时会打断 aiosqlite 的连接回收，产生无意义的
# "Exception terminating connection" 错误日志，这里静音掉。
logging.getLogger("sqlalchemy.pool").setLevel(logging.CRITICAL)


@pytest.fixture(scope="session")
def client():
    """带 lifespan 的测试客户端（会建表并初始化管理员）。"""
    from fastapi.testclient import TestClient

    from backend.main import app

    with TestClient(app) as test_client:
        yield test_client

    shutil.rmtree(TEST_ROOT, ignore_errors=True)


# ---------------- 通用辅助 ----------------


def auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def csrf_headers(client) -> dict[str, str]:
    """取一份新的 CSRF 令牌请求头（双提交 Cookie）。"""
    response = client.get("/api/v1/auth/csrf-token")
    assert response.status_code == 200, response.text
    return {"X-CSRF-Token": response.json()["csrf_token"]}


def register(client, username: str, password: str = USER_PASSWORD, **extra):
    """注册用户（自动带 CSRF 令牌），返回响应对象。"""
    return client.post(
        "/api/v1/auth/register",
        json={
            "username": username,
            "password": password,
            "confirm_password": password,
            **extra,
        },
        headers=csrf_headers(client),
    )


def login(client, username: str, password: str = USER_PASSWORD) -> str:
    """登录并返回 access_token。"""
    response = client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": password},
        headers=csrf_headers(client),
    )
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


def register_and_login(client, password: str = USER_PASSWORD) -> tuple[str, str]:
    """注册一个随机用户并登录，返回 (username, access_token)。"""
    username = f"user_{uuid.uuid4().hex[:10]}"
    response = register(client, username, password)
    assert response.status_code == 201, response.text
    return username, login(client, username, password)


@pytest.fixture
def user(client) -> tuple[str, str]:
    """普通用户 (username, token)。"""
    return register_and_login(client)


@pytest.fixture
def user_headers(user) -> dict[str, str]:
    return auth_header(user[1])


@pytest.fixture(scope="session")
def admin_token(client) -> str:
    """由 ADMIN_USERNAME/ADMIN_PASSWORD 自动创建的管理员。"""
    return login(client, "admin", ADMIN_PASSWORD)


@pytest.fixture
def admin_headers(admin_token) -> dict[str, str]:
    return auth_header(admin_token)
