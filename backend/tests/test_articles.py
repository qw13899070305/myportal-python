"""文章接口测试：可见性、审核、点赞、收藏、评论、下架、删除。"""

from backend.tests.conftest import auth_header


def _create(client, headers, title="测试文章", content="正文内容", **extra):
    payload = {"title": title, "content": content, **extra}
    response = client.post("/api/v1/articles/", json=payload, headers=headers)
    assert response.status_code == 201, response.text
    return response.json()


def test_create_article_is_pending_for_normal_user(client, user_headers):
    article = _create(client, user_headers)
    assert article["status"] == "pending"
    assert article["content"] == "正文内容"
    assert article["likes_count"] == 0
    assert article["comments_count"] == 0


def test_submit_alias_works(client, user_headers):
    response = client.post(
        "/api/v1/articles/submit",
        json={"title": "别名接口", "content": "内容"},
        headers=user_headers,
    )
    assert response.status_code == 201, response.text
    assert response.json()["status"] == "pending"


def test_pending_article_hidden_from_anonymous(client, user_headers):
    article = _create(client, user_headers, title="待审核文章")

    listing = client.get("/api/v1/articles/").json()
    assert all(item["id"] != article["id"] for item in listing["items"])

    assert client.get(f"/api/v1/articles/{article['id']}").status_code == 403

    detail = client.get(f"/api/v1/articles/{article['id']}", headers=user_headers)
    assert detail.status_code == 200


def test_admin_approval_publishes_article(client, user_headers, admin_headers):
    article = _create(client, user_headers, title="等待审核")

    review = client.post(
        f"/api/v1/articles/review/{article['id']}",
        params={"action": "approve"},
        headers=admin_headers,
    )
    assert review.status_code == 200, review.text
    assert review.json()["status"] == "approved"

    listing = client.get("/api/v1/articles/").json()
    assert any(item["id"] == article["id"] for item in listing["items"])

    detail = client.get(f"/api/v1/articles/{article['id']}").json()
    assert detail["title"] == "等待审核"
    assert detail["content"] == "正文内容"


def test_review_with_json_body(client, user_headers, admin_headers):
    article = _create(client, user_headers, title="body 审核")
    response = client.post(
        f"/api/v1/articles/{article['id']}/review",
        json={"action": "approve"},
        headers=admin_headers,
    )
    assert response.status_code == 200
    assert response.json()["status"] == "approved"


def test_review_requires_admin(client, user_headers):
    article = _create(client, user_headers)
    response = client.post(
        f"/api/v1/articles/review/{article['id']}",
        params={"action": "approve"},
        headers=user_headers,
    )
    assert response.status_code == 403


def test_admin_article_is_auto_approved(client, admin_headers):
    article = _create(client, admin_headers, title="管理员发布")
    assert article["status"] == "approved"


def test_internal_article_hidden_from_others(client, admin_headers, user_headers):
    article = _create(client, admin_headers, title="内部通知", is_internal=True)
    assert article["is_internal"] is True

    listing = client.get("/api/v1/articles/").json()
    assert all(item["id"] != article["id"] for item in listing["items"])

    denied = client.get(f"/api/v1/articles/{article['id']}", headers=user_headers)
    assert denied.status_code == 403

    internal = client.get(
        "/api/v1/articles/", params={"internal": "true"}, headers=admin_headers
    ).json()
    assert any(item["id"] == article["id"] for item in internal["items"])

    public = client.get(
        "/api/v1/articles/", params={"public": "true"}, headers=admin_headers
    ).json()
    assert all(not item["is_internal"] for item in public["items"])


def test_like_toggle(client, admin_headers, user_headers):
    article = _create(client, admin_headers, title="点赞测试")
    url = f"/api/v1/articles/{article['id']}/like"

    first = client.post(url, headers=user_headers).json()
    assert first == {"liked": True, "likes_count": 1}

    second = client.post(url, headers=user_headers).json()
    assert second == {"liked": False, "likes_count": 0}


def test_bookmark_toggle_and_list(client, admin_headers, user_headers):
    article = _create(client, admin_headers, title="收藏测试")
    url = f"/api/v1/articles/{article['id']}/bookmark"

    assert client.post(url, headers=user_headers).json()["bookmarked"] is True

    mine = client.get("/api/v1/articles/bookmarks/mine", headers=user_headers)
    assert mine.status_code == 200, mine.text
    assert any(item["id"] == article["id"] for item in mine.json()["items"])

    legacy = client.get("/api/v1/articles/bookmarks/list", headers=user_headers)
    assert legacy.status_code == 200
    assert any(item["id"] == article["id"] for item in legacy.json()["items"])

    assert client.post(url, headers=user_headers).json()["bookmarked"] is False
    assert client.get("/api/v1/articles/bookmarks/mine", headers=user_headers).json()["items"] == []


def test_is_liked_and_bookmarked_reflected_in_detail(client, admin_headers, user_headers):
    article = _create(client, admin_headers, title="状态回显")
    client.post(f"/api/v1/articles/{article['id']}/like", headers=user_headers)
    client.post(f"/api/v1/articles/{article['id']}/bookmark", headers=user_headers)

    detail = client.get(f"/api/v1/articles/{article['id']}", headers=user_headers).json()
    assert detail["is_liked"] is True
    assert detail["is_bookmarked"] is True
    assert detail["likes_count"] == 1


def test_comment_flow_includes_username(client, admin_headers, user, user_headers):
    username, _ = user
    article = _create(client, admin_headers, title="评论测试")
    url = f"/api/v1/articles/{article['id']}/comments"

    created = client.post(url, json={"content": "写得好"}, headers=user_headers)
    assert created.status_code == 201, created.text
    assert created.json()["username"] == username
    assert created.json()["user"]["username"] == username

    listing = client.get(url, headers=user_headers).json()
    assert listing["total"] == 1
    assert listing["items"][0]["content"] == "写得好"
    assert listing["items"][0]["username"] == username

    detail = client.get(f"/api/v1/articles/{article['id']}", headers=user_headers).json()
    assert detail["comments_count"] == 1

    notifications = client.get("/api/v1/notifications/", headers=admin_headers).json()
    assert any(n["type"] == "comment" for n in notifications["items"])


def test_comment_reply_and_delete(client, admin_headers, user_headers):
    article = _create(client, admin_headers, title="楼中楼")
    url = f"/api/v1/articles/{article['id']}/comments"

    parent = client.post(url, json={"content": "主楼"}, headers=user_headers).json()
    reply = client.post(
        url, json={"content": "回复", "parent_id": parent["id"]}, headers=admin_headers
    )
    assert reply.status_code == 201, reply.text
    assert reply.json()["parent_id"] == parent["id"]

    assert client.delete(f"{url}/{parent['id']}", headers=user_headers).status_code == 200
    assert client.get(url, headers=user_headers).json()["total"] == 1


def test_update_article_resets_status(client, user_headers, admin_headers):
    article = _create(client, user_headers, title="待修改")
    client.post(
        f"/api/v1/articles/review/{article['id']}",
        params={"action": "approve"},
        headers=admin_headers,
    )

    updated = client.patch(
        f"/api/v1/articles/{article['id']}",
        json={"title": "修改后的标题"},
        headers=user_headers,
    )
    assert updated.status_code == 200
    assert updated.json()["title"] == "修改后的标题"
    assert updated.json()["status"] == "pending"


def test_withdraw_article(client, admin_headers):
    article = _create(client, admin_headers, title="准备下架")
    response = client.post(f"/api/v1/articles/{article['id']}/withdraw", headers=admin_headers)
    assert response.status_code == 200
    assert (
        client.get(f"/api/v1/articles/{article['id']}", headers=admin_headers).json()["status"]
        == "pending"
    )


def test_withdraw_requires_approved_status(client, user_headers):
    article = _create(client, user_headers, title="还没通过")
    response = client.post(f"/api/v1/articles/{article['id']}/withdraw", headers=user_headers)
    assert response.status_code == 400


def test_other_user_cannot_edit_or_delete(client, admin_headers, user_headers):
    article = _create(client, admin_headers, title="别人的文章")

    assert (
        client.patch(
            f"/api/v1/articles/{article['id']}",
            json={"title": "篡改"},
            headers=user_headers,
        ).status_code
        == 403
    )
    assert (
        client.delete(f"/api/v1/articles/{article['id']}", headers=user_headers).status_code == 403
    )


def test_delete_own_article(client, user_headers):
    article = _create(client, user_headers, title="自删")
    assert (
        client.delete(f"/api/v1/articles/{article['id']}", headers=user_headers).status_code == 200
    )
    assert client.get(f"/api/v1/articles/{article['id']}", headers=user_headers).status_code == 404


def test_admin_delete_path(client, admin_headers, user_headers):
    article = _create(client, user_headers, title="管理员删除")

    assert (
        client.delete(f"/api/v1/articles/admin/{article['id']}", headers=user_headers).status_code
        == 403
    )
    assert (
        client.delete(f"/api/v1/articles/admin/{article['id']}", headers=admin_headers).status_code
        == 200
    )


def test_tag_filter_and_search(client, admin_headers):
    _create(client, admin_headers, title="唯一标题甲", tags=["alpha", "beta"])
    _create(client, admin_headers, title="唯一标题乙", tags=["gamma"])

    by_tag = client.get("/api/v1/articles/", params={"tag": "alpha"}).json()
    assert by_tag["total"] == 1
    assert by_tag["items"][0]["title"] == "唯一标题甲"
    assert by_tag["items"][0]["tags"] == ["alpha", "beta"]

    by_search = client.get("/api/v1/articles/", params={"search": "唯一标题乙"}).json()
    assert by_search["total"] == 1
    assert by_search["items"][0]["title"] == "唯一标题乙"

    tags = client.get("/api/v1/articles/tags").json()
    assert "alpha" in tags and "gamma" in tags


def test_tags_are_deduplicated(client, admin_headers):
    article = _create(client, admin_headers, title="标签去重", tags=["x", "x", " y ", ""])
    assert sorted(article["tags"]) == ["x", "y"]


def test_pagination_and_limit_alias(client, admin_headers):
    for index in range(3):
        _create(client, admin_headers, title=f"分页文章 {index}")

    first = client.get("/api/v1/articles/", params={"page": 1, "size": 2}).json()
    assert len(first["items"]) == 2
    assert first["total"] >= 3

    limited = client.get("/api/v1/articles/", params={"limit": 1}).json()
    assert len(limited["items"]) == 1


def test_invalid_status_filter_rejected(client, admin_headers):
    response = client.get("/api/v1/articles/", params={"status": "bogus"}, headers=admin_headers)
    assert response.status_code == 400


def test_non_admin_cannot_filter_by_status(client, user_headers):
    response = client.get("/api/v1/articles/", params={"status": "pending"}, headers=user_headers)
    assert response.status_code == 403


def test_mine_requires_login(client):
    assert client.get("/api/v1/articles/", params={"mine": "true"}).status_code == 401


def test_article_auth_required_for_create(client):
    response = client.post("/api/v1/articles/", json={"title": "x", "content": "y"})
    assert response.status_code == 401


def test_review_notification_created(client, user_headers, admin_headers):
    article = _create(client, user_headers, title="通知测试")
    client.post(
        f"/api/v1/articles/review/{article['id']}",
        params={"action": "reject"},
        headers=admin_headers,
    )
    notifications = client.get("/api/v1/notifications/", headers=user_headers).json()
    assert any(n["type"] == "article_review" for n in notifications["items"])


def test_search_endpoint(client, admin_headers):
    _create(client, admin_headers, title="可被搜到的文章", content="独特关键词zzz")
    response = client.get(
        "/api/v1/search/", params={"query": "独特关键词zzz"}, headers=admin_headers
    )
    assert response.status_code == 200
    body = response.json()
    assert body["total"] >= 1
    assert body["engine"] in {"database", "meilisearch"}


def test_article_detail_author_is_username(client, user, user_headers):
    username, _ = user
    article = _create(client, user_headers, title="作者展示")
    assert article["author"] == username
    assert auth_header(user[1])  # 保持 token 可用
