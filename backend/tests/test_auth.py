"""认证流程测试：注册、登录、验证码、CSRF、刷新、改密、退出、头像。"""

import io

from backend.tests.conftest import (
    ADMIN_PASSWORD,
    USER_PASSWORD,
    auth_header,
    csrf_headers,
    login,
    register,
    register_and_login,
)


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["database"] is True


def test_api_health(client):
    response = client.get("/api/v1/health/")
    assert response.status_code == 200
    assert response.json()["database"] is True


def test_register_login_me(client):
    username, token = register_and_login(client)

    response = client.get("/api/v1/auth/me", headers=auth_header(token))
    assert response.status_code == 200
    body = response.json()
    assert body["username"] == username
    assert body["roles"] == ["user"]
    assert body["is_active"] is True


def test_register_does_not_leak_password_hash(client):
    response = register(client, "hashcheck")
    assert response.status_code == 201
    assert "hashed_password" not in response.json()


def test_register_duplicate_username(client, user):
    username, _ = user
    response = register(client, username)
    assert response.status_code == 400
    assert "已存在" in response.json()["detail"]


def test_register_weak_password_rejected(client):
    response = client.post(
        "/api/v1/auth/register",
        json={"username": "weakpwd", "password": "alllowercase"},
        headers=csrf_headers(client),
    )
    assert response.status_code == 422
    # 校验失败的提示必须是可直接展示的字符串，而不是对象列表
    assert isinstance(response.json()["detail"], str)


def test_register_password_mismatch(client):
    response = client.post(
        "/api/v1/auth/register",
        json={
            "username": "mismatch",
            "password": USER_PASSWORD,
            "confirm_password": "OtherPass1!",
        },
        headers=csrf_headers(client),
    )
    assert response.status_code == 422


def test_register_requires_csrf(client):
    """没有 CSRF 令牌的注册请求必须被拒绝。"""
    response = client.post(
        "/api/v1/auth/register",
        json={"username": "nocsrf", "password": USER_PASSWORD},
    )
    assert response.status_code == 403
    assert "CSRF" in response.json()["detail"]


def test_login_requires_csrf(client, user):
    username, _ = user
    response = client.post(
        "/api/v1/auth/login", json={"username": username, "password": USER_PASSWORD}
    )
    assert response.status_code == 403


def test_login_accepts_form_and_json(client, user):
    """表单（OAuth2）与 JSON 两种提交方式都要支持。"""
    username, _ = user

    as_json = client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": USER_PASSWORD},
        headers=csrf_headers(client),
    )
    assert as_json.status_code == 200

    # /auth/token 是 OAuth2 入口，按规范豁免 CSRF（供 docs 的 Authorize 使用）
    as_form = client.post(
        "/api/v1/auth/token", data={"username": username, "password": USER_PASSWORD}
    )
    assert as_form.status_code == 200
    assert as_form.json()["token_type"] == "bearer"


def test_login_wrong_password(client, user):
    username, _ = user
    response = client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": "WrongPass1!"},
        headers=csrf_headers(client),
    )
    assert response.status_code == 401
    assert response.headers.get("WWW-Authenticate") == "Bearer"


def test_me_requires_token(client):
    assert client.get("/api/v1/auth/me").status_code == 401


def test_me_rejects_garbage_token(client):
    response = client.get("/api/v1/auth/me", headers=auth_header("not-a-real-jwt"))
    assert response.status_code == 401


def test_captcha_endpoint_returns_png(client):
    response = client.get("/api/v1/auth/captcha")
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"
    assert response.headers.get("X-Captcha-Id")
    # PNG 魔数
    assert response.content[:8] == b"\x89PNG\r\n\x1a\n"


def test_captcha_required_after_repeated_failures(client):
    """连续失败达到阈值后，登录必须携带验证码。"""
    username = "captcha_user"
    assert register(client, username).status_code == 201

    for _ in range(3):
        client.post(
            "/api/v1/auth/login",
            json={"username": username, "password": "WrongPass1!"},
            headers=csrf_headers(client),
        )

    # 第 4 次即使密码正确，也必须带验证码
    blocked = client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": USER_PASSWORD},
        headers=csrf_headers(client),
    )
    assert blocked.status_code == 400
    assert "验证码" in blocked.json()["detail"]

    # 带上（错误的）验证码仍然失败
    still_blocked = client.post(
        "/api/v1/auth/login",
        json={
            "username": username,
            "password": USER_PASSWORD,
            "captcha_id": "nope",
            "captcha_code": "XXXX",
        },
        headers=csrf_headers(client),
    )
    assert still_blocked.status_code == 400


def test_refresh_token_rotation(client, user):
    username, _ = user
    login_data = client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": USER_PASSWORD},
        headers=csrf_headers(client),
    ).json()

    response = client.post(
        "/api/v1/auth/refresh", json={"refresh_token": login_data["refresh_token"]}
    )
    assert response.status_code == 200, response.text
    new_tokens = response.json()
    assert new_tokens["access_token"] != login_data["access_token"]

    # 旧刷新令牌必须立即失效（轮换）
    replay = client.post(
        "/api/v1/auth/refresh", json={"refresh_token": login_data["refresh_token"]}
    )
    assert replay.status_code == 401


def test_refresh_rejects_access_token(client, user):
    _, token = user
    response = client.post("/api/v1/auth/refresh", json={"refresh_token": token})
    assert response.status_code == 401


def test_refresh_token_cannot_access_business_api(client):
    username, _ = register_and_login(client)
    login_data = client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": USER_PASSWORD},
        headers=csrf_headers(client),
    ).json()

    response = client.get("/api/v1/auth/me", headers=auth_header(login_data["refresh_token"]))
    assert response.status_code == 401


def test_change_password(client):
    username, token = register_and_login(client)

    wrong = client.post(
        "/api/v1/auth/change-password",
        json={"old_password": "WrongOld1!", "new_password": "BrandNew1!"},
        headers=auth_header(token),
    )
    assert wrong.status_code == 400

    ok = client.post(
        "/api/v1/auth/change-password",
        json={"old_password": USER_PASSWORD, "new_password": "BrandNew1!"},
        headers=auth_header(token),
    )
    assert ok.status_code == 200

    assert (
        client.post(
            "/api/v1/auth/login",
            json={"username": username, "password": USER_PASSWORD},
            headers=csrf_headers(client),
        ).status_code
        == 401
    )
    assert login(client, username, "BrandNew1!")


def test_logout_blacklists_token(client):
    _, token = register_and_login(client)

    assert client.get("/api/v1/auth/me", headers=auth_header(token)).status_code == 200
    assert client.post("/api/v1/auth/logout", headers=auth_header(token)).status_code == 200
    # 退出后同一个令牌必须立即失效
    assert client.get("/api/v1/auth/me", headers=auth_header(token)).status_code == 401


def test_avatar_upload_and_fetch(client, user_headers):
    # 一张 1x1 的合法 PNG
    import base64

    png = base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8DwHwAF"
        "BQH/qZ0d8wAAAABJRU5ErkJggg=="
    )
    response = client.post(
        "/api/v1/auth/avatar",
        files={"file": ("a.png", io.BytesIO(png), "image/png")},
        headers=user_headers,
    )
    assert response.status_code == 200, response.text
    assert response.json()["avatar_url"].startswith("/api/v1/auth/avatar/")

    me = client.get("/api/v1/auth/me", headers=user_headers).json()
    assert me["avatar_url"]

    fetched = client.get(response.json()["avatar_url"], headers=user_headers)
    assert fetched.status_code == 200
    assert fetched.content == png


def test_avatar_rejects_non_image(client, user_headers):
    response = client.post(
        "/api/v1/auth/avatar",
        files={"file": ("a.txt", io.BytesIO(b"hello"), "text/plain")},
        headers=user_headers,
    )
    assert response.status_code == 400


def test_users_apply_cannot_escalate_role(client):
    """通过 /users/apply 申请管理员必须被忽略。"""
    response = client.post(
        "/api/v1/users/apply",
        json={
            "username": "escalate1",
            "password": USER_PASSWORD,
            "requested_role": "admin",
        },
        headers=csrf_headers(client),
    )
    assert response.status_code == 201, response.text
    assert response.json()["roles"] == ["user"]


def test_check_username(client):
    response = client.get("/api/v1/auth/check-username", params={"username": "admin"})
    assert response.status_code == 200
    assert response.json()["available"] is False

    response = client.get(
        "/api/v1/auth/check-username", params={"username": "definitely-not-taken"}
    )
    assert response.json()["available"] is True


def test_admin_can_login(client):
    assert login(client, "admin", ADMIN_PASSWORD)
