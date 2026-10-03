"""聊天、通知与后台管理接口测试。"""

import pytest
from starlette.websockets import WebSocketDisconnect

from backend.tests.conftest import auth_header, register_and_login


def recv_until(websocket, msg_type: str, limit: int = 10) -> dict:
    """读取 WebSocket 帧直到出现指定 type（跳过 online / user_joined 等通知帧）。"""
    for _ in range(limit):
        payload = websocket.receive_json()
        if payload.get("type") == msg_type:
            return payload
    raise AssertionError(f"未在 {limit} 帧内收到 type={msg_type} 的消息")


# ---------------- 聊天（HTTP） ----------------


def test_chat_history_requires_auth(client):
    assert client.get("/api/v1/chat/history").status_code == 401
    assert client.get("/api/v1/chat/messages").status_code == 401


def test_chat_online_endpoint(client, user_headers):
    response = client.get("/api/v1/chat/online", headers=user_headers)
    assert response.status_code == 200
    assert "count" in response.json()


def test_history_supports_multiple_page_param_names(client, user_headers):
    for params in ({"limit": 5}, {"size": 5}, {"page_size": 5}):
        response = client.get("/api/v1/chat/history", params=params, headers=user_headers)
        assert response.status_code == 200, (params, response.text)


# ---------------- 聊天（WebSocket） ----------------


def test_websocket_broadcast(client, user):
    username, token = user

    with client.websocket_connect(f"/api/v1/chat/ws?token={token}") as websocket:
        websocket.send_json({"content": "hello from pytest"})
        payload = recv_until(websocket, "message")

    assert payload["content"] == "hello from pytest"
    assert payload["username"] == username
    assert payload["id"] > 0


def test_websocket_message_appears_in_history(client, user):
    _, token = user
    headers = auth_header(token)

    with client.websocket_connect(f"/api/v1/chat/ws?token={token}") as websocket:
        websocket.send_json({"content": "history check"})
        message_id = recv_until(websocket, "message")["id"]

    history = client.get("/api/v1/chat/messages", headers=headers).json()
    item = next(item for item in history["items"] if item["id"] == message_id)
    assert item["content"] == "history check"
    assert item["username"]


def test_websocket_rejects_bad_token(client):
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect("/api/v1/chat/ws?token=garbage") as websocket:
            websocket.receive_json()


def test_websocket_rejects_missing_token(client):
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect("/api/v1/chat/ws") as websocket:
            websocket.receive_json()


def test_websocket_rejects_too_long_message(client, user):
    _, token = user
    with client.websocket_connect(f"/api/v1/chat/ws?token={token}") as websocket:
        websocket.send_json({"content": "x" * 5000})
        payload = recv_until(websocket, "error")

    assert "过长" in payload["detail"]


def test_websocket_ping(client, user):
    _, token = user
    with client.websocket_connect(f"/api/v1/chat/ws?token={token}") as websocket:
        websocket.send_json({"type": "ping"})
        assert recv_until(websocket, "pong")["type"] == "pong"


def test_websocket_accepts_plain_text(client, user):
    """兼容老前端直接发纯文本。"""
    _, token = user
    with client.websocket_connect(f"/api/v1/chat/ws?token={token}") as websocket:
        websocket.send_text("plain text message")
        payload = recv_until(websocket, "message")

    assert payload["content"] == "plain text message"


def test_message_can_be_recalled(client, user):
    _, token = user
    headers = auth_header(token)

    with client.websocket_connect(f"/api/v1/chat/ws?token={token}") as websocket:
        websocket.send_json({"content": "recall me"})
        message_id = recv_until(websocket, "message")["id"]

    recalled = client.delete(f"/api/v1/chat/messages/{message_id}", headers=headers)
    assert recalled.status_code == 200

    history = client.get("/api/v1/chat/messages", headers=headers).json()
    assert all(item["id"] != message_id for item in history["items"])


def test_cannot_recall_others_message(client, user):
    _, token = user
    with client.websocket_connect(f"/api/v1/chat/ws?token={token}") as websocket:
        websocket.send_json({"content": "mine only"})
        message_id = recv_until(websocket, "message")["id"]

    _, other_token = register_and_login(client)
    response = client.delete(
        f"/api/v1/chat/messages/{message_id}", headers=auth_header(other_token)
    )
    assert response.status_code == 403


def test_mention_creates_notification(client, user, admin_headers):
    _, token = user
    with client.websocket_connect(f"/api/v1/chat/ws?token={token}") as websocket:
        websocket.send_json({"content": "@admin 请看一下"})
        recv_until(websocket, "message")

    notifications = client.get(
        "/api/v1/notifications/", params={"unread_only": True}, headers=admin_headers
    ).json()
    assert any(n["type"] == "mention" for n in notifications["items"])


def test_clear_own_messages(client, user_headers):
    response = client.delete("/api/v1/chat/messages", headers=user_headers)
    assert response.status_code == 200


def test_clear_all_requires_admin(client, user_headers):
    assert client.delete("/api/v1/chat/all", headers=user_headers).status_code == 403


# ---------------- 通知 ----------------


def test_notification_read_flow(client, user_headers):
    listing = client.get("/api/v1/notifications/", headers=user_headers)
    assert listing.status_code == 200
    assert "unread" in listing.json()

    count = client.get("/api/v1/notifications/unread-count", headers=user_headers)
    assert count.status_code == 200
    assert isinstance(count.json()["unread"], int)

    assert client.post("/api/v1/notifications/read-all", headers=user_headers).status_code == 200
    assert (
        client.get("/api/v1/notifications/unread-count", headers=user_headers).json()["unread"] == 0
    )


def test_notification_can_be_marked_and_deleted(client, user, user_headers, admin_headers):
    """给自己造一条通知：管理员评论我的文章。"""
    username, _ = user
    article = client.post(
        "/api/v1/articles/",
        json={"title": f"通知测试-{username}", "content": "内容"},
        headers=user_headers,
    ).json()
    client.post(
        f"/api/v1/articles/{article['id']}/comments",
        json={"content": "评论"},
        headers=admin_headers,
    )

    items = client.get("/api/v1/notifications/", headers=user_headers).json()["items"]
    target = next(n for n in items if n["type"] in {"comment", "article_review"})

    assert (
        client.post(f"/api/v1/notifications/{target['id']}/read", headers=user_headers).status_code
        == 200
    )
    assert (
        client.delete(f"/api/v1/notifications/{target['id']}", headers=user_headers).status_code
        == 200
    )


def test_notifications_are_private(client, user_headers, admin_headers):
    client.post("/api/v1/notifications/read-all", headers=admin_headers)
    listing = client.get("/api/v1/notifications/", headers=user_headers).json()
    assert listing["unread"] == 0


# ---------------- 后台管理 ----------------


def test_admin_endpoints_reject_normal_user(client, user_headers):
    for method, url in (
        ("get", "/api/v1/admin/stats"),
        ("get", "/api/v1/admin/dashboard"),
        ("get", "/api/v1/admin/users"),
        ("get", "/api/v1/admin/chat/messages"),
        ("get", "/api/v1/admin/config"),
        ("get", "/api/v1/audit/"),
    ):
        response = getattr(client, method)(url, headers=user_headers)
        assert response.status_code == 403, url


def test_admin_stats_and_dashboard(client, admin_headers):
    response = client.get("/api/v1/admin/stats", headers=admin_headers)
    assert response.status_code == 200
    body = response.json()
    for key in ("users", "articles", "files", "pending_articles", "chat_messages"):
        assert key in body
    assert body["users"] >= 1

    legacy = client.get("/api/v1/admin/dashboard", headers=admin_headers)
    assert legacy.status_code == 200
    assert legacy.json()["code"] == 200
    assert legacy.json()["data"]["users"] >= 1


def test_admin_user_list_and_toggle(client, admin_headers):
    username, token = register_and_login(client)

    listing = client.get(
        "/api/v1/admin/users", params={"search": username}, headers=admin_headers
    ).json()
    assert listing["total"] == 1
    user_id = listing["items"][0]["id"]

    # 禁用后该用户的令牌立即失效
    disabled = client.post(f"/api/v1/admin/users/{user_id}/toggle-active", headers=admin_headers)
    assert disabled.status_code == 200
    assert disabled.json()["is_active"] is False
    assert client.get("/api/v1/auth/me", headers=auth_header(token)).status_code == 403

    enabled = client.post(f"/api/v1/admin/users/{user_id}/toggle-active", headers=admin_headers)
    assert enabled.json()["is_active"] is True
    assert client.get("/api/v1/auth/me", headers=auth_header(token)).status_code == 200


def test_admin_cannot_disable_self(client, admin_headers):
    me = client.get("/api/v1/auth/me", headers=admin_headers).json()
    response = client.post(f"/api/v1/admin/users/{me['id']}/toggle-active", headers=admin_headers)
    assert response.status_code == 400


def test_users_approve_endpoint(client, admin_headers):
    username, _ = register_and_login(client)
    listing = client.get(
        "/api/v1/admin/users", params={"search": username}, headers=admin_headers
    ).json()
    user_id = listing["items"][0]["id"]

    response = client.post(f"/api/v1/users/approve/{user_id}", headers=admin_headers)
    assert response.status_code == 200
    assert response.json()["is_active"] is True


def test_site_config_roundtrip(client, admin_headers):
    initial = client.get("/api/v1/admin/config", headers=admin_headers).json()
    assert "site_name" in initial

    updated = client.put(
        "/api/v1/admin/config",
        json={"site_name": "测试门户", "announcement": "公告内容"},
        headers=admin_headers,
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["site_name"] == "测试门户"
    assert updated.json()["announcement"] == "公告内容"

    # POST 别名（前端使用的方式）
    posted = client.post(
        "/api/v1/admin/config",
        json={"site_name": "改名了"},
        headers=admin_headers,
    )
    assert posted.status_code == 200
    assert client.get("/api/v1/admin/config", headers=admin_headers).json()["site_name"] == "改名了"

    # 站点公开信息不需要登录
    public = client.get("/api/v1/admin/site-info")
    assert public.status_code == 200
    assert public.json()["site_name"] == "改名了"


def test_admin_chat_management(client, admin_headers, user):
    _, token = user
    with client.websocket_connect(f"/api/v1/chat/ws?token={token}") as websocket:
        websocket.send_json({"content": "admin manage me"})
        message_id = recv_until(websocket, "message")["id"]

    listing = client.get("/api/v1/admin/chat/messages", headers=admin_headers)
    assert listing.status_code == 200
    assert any(item["id"] == message_id for item in listing.json()["items"])

    assert (
        client.delete(
            f"/api/v1/admin/chat/messages/{message_id}", headers=admin_headers
        ).status_code
        == 200
    )
    # /chat/clear 是前端使用的路径
    assert client.delete("/api/v1/admin/chat/clear", headers=admin_headers).status_code == 200
    assert client.get("/api/v1/admin/chat/messages", headers=admin_headers).json()["total"] == 0


# ---------------- 审计日志 ----------------


def test_audit_log_records_actions(client, admin_headers):
    response = client.get("/api/v1/audit/", headers=admin_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["total"] >= 1
    actions = {item["action"] for item in body["items"]}
    # 之前必然发生过登录
    assert "login" in actions

    filtered = client.get(
        "/api/v1/audit/", params={"action": "login"}, headers=admin_headers
    ).json()
    assert all("login" in item["action"] for item in filtered["items"])


# ---------------- 分类 ----------------


def test_category_crud(client, admin_headers, user_headers):
    created = client.post("/api/v1/categories/", json={"name": "技术分享"}, headers=admin_headers)
    assert created.status_code == 201, created.text
    category_id = created.json()["id"]

    # 重复创建被拒绝
    assert (
        client.post(
            "/api/v1/categories/", json={"name": "技术分享"}, headers=admin_headers
        ).status_code
        == 400
    )

    # 列表是公开的
    listing = client.get("/api/v1/categories/")
    assert listing.status_code == 200
    assert any(item["id"] == category_id for item in listing.json())

    # 普通用户不能创建/删除
    assert (
        client.post(
            "/api/v1/categories/", json={"name": "普通用户"}, headers=user_headers
        ).status_code
        == 403
    )
    assert (
        client.delete(f"/api/v1/categories/{category_id}", headers=user_headers).status_code == 403
    )

    assert (
        client.delete(f"/api/v1/categories/{category_id}", headers=admin_headers).status_code == 200
    )
