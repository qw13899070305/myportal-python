"""文件接口测试：上传校验、下载、预览、重命名、回收站、分享。"""

import fitz

from backend.tests.conftest import register_and_login


def _upload(client, headers, name="notes.txt", data=b"hello world", mime="text/plain"):
    return client.post(
        "/api/v1/files/upload",
        files={"file": (name, data, mime)},
        headers=headers,
    )


def _make_pdf() -> bytes:
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), "MyPortal PDF preview")
    payload = doc.tobytes()
    doc.close()
    return payload


def _upload_ok(client, headers, name="notes.txt", data=b"hello world", mime="text/plain"):
    response = _upload(client, headers, name=name, data=data, mime=mime)
    assert response.status_code == 201, response.text
    return response.json()


def test_upload_text_file(client, user_headers):
    body = _upload_ok(client, user_headers)
    assert body["name"] == "notes.txt"
    assert body["size"] == len(b"hello world")
    assert body["deleted"] is False
    assert body["uploader"]  # 上传者用户名


def test_upload_rejects_disallowed_extension(client, user_headers):
    response = _upload(client, user_headers, name="evil.exe", data=b"MZ\x90\x00")
    assert response.status_code == 400


def test_upload_rejects_empty_file(client, user_headers):
    response = _upload(client, user_headers, name="empty.txt", data=b"")
    assert response.status_code == 400


def test_upload_rejects_magic_mismatch(client, user_headers):
    """扩展名是 .png，内容是纯文本 -> 必须拒绝。"""
    response = _upload(client, user_headers, name="fake.png", data=b"just text", mime="image/png")
    assert response.status_code == 400


def test_upload_strips_path_from_filename(client, user_headers):
    body = _upload_ok(client, user_headers, name="../../etc/passwd.txt", data=b"root:x:0:0")
    assert body["name"] == "passwd.txt"


def test_upload_accepts_phone_and_ebook_formats(client, user_headers):
    """手机相册 / 录像 / 录音 / 电子书要能传（白名单与魔数都得认）。"""
    cases = [
        ("photo.heic", b"\x00\x00\x00\x18ftypheic\x00\x00\x00\x00mif1heic", "image/heic"),
        ("photo.heif", b"\x00\x00\x00\x18ftypmif1\x00\x00\x00\x00mif1heic", "image/heif"),
        ("movie.mp4", b"\x00\x00\x00\x18ftypisom\x00\x00\x00\x00isommp42", "video/mp4"),
        ("clip.mov", b"\x00\x00\x00\x14ftypqt  \x00\x00\x02\x00qt  ", "video/quicktime"),
        ("record.3gp", b"\x00\x00\x00\x18ftyp3gp4\x00\x00\x00\x003gp4isom", "video/3gpp"),
        ("song.m4a", b"\x00\x00\x00\x18ftypM4A \x00\x00\x00\x00M4A mp42", "audio/mp4"),
        ("song.mp3", b"ID3\x04\x00\x00\x00\x00\x00\x00", "audio/mpeg"),
        ("sound.wav", b"RIFF\x24\x00\x00\x00WAVEfmt ", "audio/wav"),
        ("book.epub", b"PK\x03\x04" + b"\x00" * 20, "application/epub+zip"),
    ]
    for name, data, mime in cases:
        body = _upload_ok(client, user_headers, name=name, data=data, mime=mime)
        assert body["name"] == name, name


def test_upload_rejects_fake_phone_formats(client, user_headers):
    """只改扩展名不行：内容是纯文本的 .heic / .mp4 / .mp3 必须被魔数拦下。"""
    for name in ("fake.heic", "fake.mp4", "fake.m4a", "fake.mp3", "fake.wav"):
        response = _upload(client, user_headers, name=name, data=b"just a text file")
        assert response.status_code == 400, name


def _pdb(magic: bytes) -> bytes:
    """拼一个 PalmDB 头：容器标识固定在第 60 字节（AZW3 / MOBI）。"""
    return b"\x00" * 60 + magic + b"\x00" * 64


def test_upload_accepts_ebook_and_chm_formats(client, user_headers):
    """EPUB / AZW3 / MOBI / CHM 要能传：AZW3 的魔数在第 60 字节，CHM 是 ITSF。"""
    cases = [
        ("book.epub", b"PK\x03\x04" + b"\x00" * 20, "application/epub+zip"),
        ("book.azw3", _pdb(b"BOOKMOBI"), "application/x-mobipocket-ebook"),
        ("book.mobi", _pdb(b"BOOKMOBI"), "application/x-mobipocket-ebook"),
        ("old.mobi", _pdb(b"TEXtREAd"), "application/x-mobipocket-ebook"),
        ("manual.chm", b"ITSF" + b"\x00" * 124, "application/vnd.ms-htmlhelp"),
    ]
    for name, data, mime in cases:
        body = _upload_ok(client, user_headers, name=name, data=data, mime=mime)
        assert body["name"] == name, name


def test_upload_rejects_mismatched_ebook_formats(client, user_headers):
    """扩展名和容器对不上必须拒绝：.azw3 里塞 CHM、.chm 里塞 zip、.epub 里塞纯文本。"""
    mismatches = [
        ("fake.azw3", b"ITSF" + b"\x00" * 124),
        ("fake.mobi", b"PK\x03\x04" + b"\x00" * 124),
        ("fake.chm", b"PK\x03\x04" + b"\x00" * 124),
        ("fake.epub", b"just a text file"),
        ("fake.chm", b"just a text file"),
    ]
    for name, data in mismatches:
        response = _upload(client, user_headers, name=name, data=data)
        assert response.status_code == 400, name


def test_list_and_recent(client, user_headers):
    _upload_ok(client, user_headers, name="listed.txt")

    listing = client.get("/api/v1/files/", headers=user_headers)
    assert listing.status_code == 200
    assert listing.json()["total"] >= 1

    # /recent 不能被 /{file_id} 抢占（否则会 422）
    recent = client.get("/api/v1/files/recent", headers=user_headers)
    assert recent.status_code == 200, recent.text
    assert isinstance(recent.json(), list)

    # 旧接口返回磁盘文件名列表
    legacy = client.get("/api/v1/files/list", headers=user_headers)
    assert legacy.status_code == 200
    assert isinstance(legacy.json()["data"], list)


def test_list_supports_limit_alias(client, user_headers):
    response = client.get("/api/v1/files/", params={"limit": 1}, headers=user_headers)
    assert response.status_code == 200
    assert len(response.json()["items"]) <= 1


def test_files_carry_category(client, user_headers):
    """每个文件对象都要带分类键（机器键，客户端自己翻译）。"""
    body = _upload_ok(client, user_headers, name="shot.png", data=b"\x89PNG\r\n\x1a\n" + b"\x00" * 32)

    assert body["category"] == "image"
    listed = client.get("/api/v1/files/", headers=user_headers).json()["items"]
    assert {item["category"] for item in listed} == {"image"}

    # 重命名后分类跟着变（分类是按文件名实时派生的，不存库）
    renamed = client.patch(
        f"/api/v1/files/{body['id']}", json={"name": "notes.txt"}, headers=user_headers
    )
    assert renamed.status_code == 200, renamed.text
    assert renamed.json()["category"] == "document"


def test_list_filters_by_category_and_counts(client, user_headers):
    _upload_ok(client, user_headers, name="a.png", data=b"\x89PNG\r\n\x1a\n" + b"\x00" * 32)
    _upload_ok(client, user_headers, name="b.jpg", data=b"\xff\xd8\xff" + b"\x00" * 32)
    _upload_ok(client, user_headers, name="c.txt", data=b"hello")
    _upload_ok(client, user_headers, name="d.epub", data=b"PK\x03\x04" + b"\x00" * 32)

    images = client.get("/api/v1/files/", params={"category": "image"}, headers=user_headers).json()
    assert images["total"] == 2
    assert {item["name"] for item in images["items"]} == {"a.png", "b.jpg"}

    ebooks = client.get("/api/v1/files/", params={"category": "ebook"}, headers=user_headers).json()
    assert [item["name"] for item in ebooks["items"]] == ["d.epub"]

    docs = client.get("/api/v1/files/", params={"category": "document"}, headers=user_headers).json()
    assert [item["name"] for item in docs["items"]] == ["c.txt"]

    # 计数与筛选口径一致
    counts = client.get("/api/v1/files/categories", headers=user_headers).json()
    assert counts["total"] == 4
    by_key = {item["key"]: item["count"] for item in counts["items"]}
    assert by_key["image"] == 2 and by_key["document"] == 1 and by_key["ebook"] == 1
    assert by_key["video"] == 0 and by_key["other"] == 0

    # 搜索条件也要作用在计数上
    counted = client.get(
        "/api/v1/files/categories", params={"search": "a.png"}, headers=user_headers
    ).json()
    assert counted["total"] == 1
    assert {item["key"]: item["count"] for item in counted["items"]}["image"] == 1

    # 未知分类要如实报错，而不是当成"全部"
    bad = client.get("/api/v1/files/", params={"category": "nope"}, headers=user_headers)
    assert bad.status_code == 400
    assert "image" in bad.json()["detail"]


def test_category_other_holds_unclassified_files(client, user_headers, user):
    """不在分类表里的文件落到 other。

    上传白名单不允许产生这种文件，所以直接往库里塞一条"历史遗留"记录
    （老版本传上来的 .exe / 无扩展名文件），验证 other 走的是取反集。
    """
    import sqlite3

    from backend.core.filetypes import category_of
    from backend.tests.conftest import TEST_ROOT

    username = user[0]
    connection = sqlite3.connect(f"{TEST_ROOT}/test.db")
    try:
        uploader_id = connection.execute(
            "SELECT id FROM users WHERE username = ?", (username,)
        ).fetchone()[0]
        connection.execute(
            "INSERT INTO files (name, stored_name, size, content_type, upload_time,"
            " uploader_id, deleted) VALUES (?,?,?,?,?,?,0)",
            ("legacy.exe", "legacy-stored.exe", 3, "application/octet-stream",
             "2026-01-01 00:00:00.000000", uploader_id),
        )
        connection.commit()
    finally:
        connection.close()

    other = client.get("/api/v1/files/", params={"category": "other"}, headers=user_headers).json()
    assert [item["name"] for item in other["items"]] == ["legacy.exe"]
    assert other["items"][0]["category"] == "other"

    # 有扩展名但不在分类表里的走同一条规则
    assert category_of("virus.exe") == "other"


def test_download_roundtrip(client, user_headers):
    content = b"download me please"
    file_id = _upload_ok(client, user_headers, name="dl.txt", data=content)["id"]

    response = client.get(f"/api/v1/files/{file_id}/download", headers=user_headers)
    assert response.status_code == 200
    assert response.content == content

    # 旧路径同样可用
    legacy = client.get(f"/api/v1/files/download/{file_id}", headers=user_headers)
    assert legacy.status_code == 200
    assert legacy.content == content


def test_download_accepts_token_query_param(client, user):
    """<a download> 无法设置请求头，必须支持 ?token=。"""
    _, token = user
    file_id = _upload_ok(client, {"Authorization": f"Bearer {token}"})["id"]

    response = client.get(f"/api/v1/files/{file_id}/download?token={token}")
    assert response.status_code == 200

    assert client.get(f"/api/v1/files/{file_id}/download").status_code == 401


def test_download_head_returns_file_headers(client, user_headers):
    """HEAD 必须命中下载接口。

    FastAPI 不会给 GET 路由自动加 HEAD，手机上的下载管理器先发 HEAD 探
    大小/文件名时会掉进前端静态回退，拿到 index.html（曾经就是这样）。
    """
    content = b"head me please"
    file_id = _upload_ok(client, user_headers, name="head.txt", data=content)["id"]

    response = client.head(
        f"/api/v1/files/{file_id}/download",
        headers={"Authorization": user_headers["Authorization"]},
    )
    assert response.status_code == 200
    assert response.headers["content-length"] == str(len(content))
    assert "attachment" in response.headers["content-disposition"]
    assert response.content == b""  # HEAD 不带响应体


def test_preview_text_file(client, user_headers):
    file_id = _upload_ok(
        client, user_headers, name="preview.txt", data=b"<script>alert(1)</script>"
    )["id"]

    response = client.get(f"/api/v1/files/{file_id}/preview", headers=user_headers)
    assert response.status_code == 200
    # 文本预览必须转义，不能原样输出脚本
    assert "<script>" not in response.text
    assert "&lt;script&gt;" in response.text
    assert "default-src 'none'" in response.headers["content-security-policy"]

    legacy = client.get(f"/api/v1/files/preview/{file_id}", headers=user_headers)
    assert legacy.status_code == 200


def test_preview_pdf_and_page_image(client, user_headers):
    file_id = _upload_ok(
        client, user_headers, name="doc.pdf", data=_make_pdf(), mime="application/pdf"
    )["id"]

    info = client.get(f"/api/v1/files/{file_id}/pdf-info", headers=user_headers)
    assert info.status_code == 200
    assert info.json()["page_count"] == 1

    page = client.get(f"/api/v1/files/{file_id}/pdf-page/1", headers=user_headers)
    assert page.status_code == 200
    assert page.headers["content-type"] == "image/jpeg"

    out_of_range = client.get(f"/api/v1/files/{file_id}/pdf-page/9", headers=user_headers)
    assert out_of_range.status_code == 404


def test_rename_file_both_styles(client, user_headers):
    file_id = _upload_ok(client, user_headers, name="old.txt")["id"]

    renamed = client.patch(
        f"/api/v1/files/{file_id}", json={"name": "new.txt"}, headers=user_headers
    )
    assert renamed.status_code == 200
    assert renamed.json()["name"] == "new.txt"

    legacy = client.put(
        f"/api/v1/files/rename/{file_id}",
        params={"new_name": "newest.txt"},
        headers=user_headers,
    )
    assert legacy.status_code == 200
    assert legacy.json()["name"] == "newest.txt"


def test_rename_rejects_unsafe_name(client, user_headers):
    file_id = _upload_ok(client, user_headers, name="safe.txt")["id"]

    assert (
        client.patch(
            f"/api/v1/files/{file_id}", json={"name": "x.exe"}, headers=user_headers
        ).status_code
        == 400
    )
    # 路径穿越会被裁成基名
    response = client.patch(
        f"/api/v1/files/{file_id}",
        json={"name": "../../escape.txt"},
        headers=user_headers,
    )
    assert response.status_code == 200
    assert response.json()["name"] == "escape.txt"


def test_soft_delete_trash_and_restore(client, user_headers):
    file_id = _upload_ok(client, user_headers, name="trashme.txt")["id"]

    assert client.delete(f"/api/v1/files/{file_id}", headers=user_headers).status_code == 200

    listing = client.get("/api/v1/files/", headers=user_headers).json()
    assert all(item["id"] != file_id for item in listing["items"])

    trash = client.get("/api/v1/trash/", headers=user_headers).json()
    entry = next(item for item in trash["items"] if item["file_id"] == file_id)
    assert entry["name"] == "trashme.txt"

    # 重复删除被拒绝
    assert client.delete(f"/api/v1/files/{file_id}", headers=user_headers).status_code == 400

    restored = client.post(f"/api/v1/trash/restore/{entry['id']}", headers=user_headers)
    assert restored.status_code == 200, restored.text

    listing = client.get("/api/v1/files/", headers=user_headers).json()
    assert any(item["id"] == file_id for item in listing["items"])


def test_permanent_delete_from_trash(client, user_headers):
    file_id = _upload_ok(client, user_headers, name="purge.txt")["id"]
    client.delete(f"/api/v1/files/{file_id}", headers=user_headers)
    entry_id = client.get("/api/v1/trash/", headers=user_headers).json()["items"][0]["id"]

    assert (
        client.delete(f"/api/v1/trash/permanent/{entry_id}", headers=user_headers).status_code
        == 200
    )
    assert client.get(f"/api/v1/files/{file_id}", headers=user_headers).status_code == 404
    assert client.get("/api/v1/trash/", headers=user_headers).json()["items"] == []


def test_empty_trash(client, user_headers):
    for index in range(2):
        file_id = _upload_ok(client, user_headers, name=f"bulk{index}.txt")["id"]
        client.delete(f"/api/v1/files/{file_id}", headers=user_headers)

    response = client.delete("/api/v1/trash/", headers=user_headers)
    assert response.status_code == 200
    assert client.get("/api/v1/trash/", headers=user_headers).json()["items"] == []


def test_users_cannot_access_others_files(client, user_headers):
    file_id = _upload_ok(client, user_headers, name="private.txt")["id"]

    _, other_token = register_and_login(client)
    other = {"Authorization": f"Bearer {other_token}"}

    assert client.get(f"/api/v1/files/{file_id}", headers=other).status_code == 403
    assert client.get(f"/api/v1/files/{file_id}/download", headers=other).status_code == 403
    assert client.get(f"/api/v1/files/{file_id}/preview", headers=other).status_code == 403
    assert client.delete(f"/api/v1/files/{file_id}", headers=other).status_code == 403


def test_admin_can_access_users_files(client, user_headers, admin_headers):
    file_id = _upload_ok(client, user_headers, name="adminview.txt")["id"]

    assert client.get(f"/api/v1/files/{file_id}", headers=admin_headers).status_code == 200
    listing = client.get("/api/v1/files/", headers=admin_headers).json()
    assert any(item["id"] == file_id for item in listing["items"])


def test_upload_requires_auth(client):
    response = client.post("/api/v1/files/upload", files={"file": ("a.txt", b"x", "text/plain")})
    assert response.status_code == 401


def test_admin_cleanup_purges_deleted_files(client, user_headers, admin_headers):
    file_id = _upload_ok(client, user_headers, name="cleanup.txt")["id"]
    client.delete(f"/api/v1/files/{file_id}", headers=user_headers)

    response = client.post("/api/v1/admin/files/cleanup", headers=admin_headers)
    assert response.status_code == 200
    assert response.json()["deleted_count"] >= 1
    assert client.get(f"/api/v1/files/{file_id}", headers=admin_headers).status_code == 404


# ---------------- 分享 ----------------


def test_share_create_access_and_download(client, user_headers):
    content = b"shared content"
    file_id = _upload_ok(client, user_headers, name="share.txt", data=content)["id"]

    created = client.post("/api/v1/share/create", json={"file_id": file_id}, headers=user_headers)
    assert created.status_code == 200, created.text
    code = created.json()["code"]
    assert created.json()["has_password"] is False

    access = client.get(f"/api/v1/share/access/{code}")
    assert access.status_code == 200
    assert access.json()["filename"] == "share.txt"

    download = client.get(f"/api/v1/share/download/{code}")
    assert download.status_code == 200
    assert download.content == content

    mine = client.get("/api/v1/share/mine", headers=user_headers)
    assert any(item["code"] == code for item in mine.json())

    assert client.delete(f"/api/v1/share/{code}", headers=user_headers).status_code == 200
    assert client.get(f"/api/v1/share/access/{code}").status_code == 404


def test_share_password_is_hashed_and_required(client, user_headers):
    file_id = _upload_ok(client, user_headers, name="secret.txt")["id"]

    created = client.post(
        "/api/v1/share/create",
        json={"file_id": file_id, "password": "SharePass1!"},
        headers=user_headers,
    ).json()
    code = created["code"]
    assert created["has_password"] is True

    assert client.get(f"/api/v1/share/access/{code}").status_code == 403
    assert (
        client.get(f"/api/v1/share/access/{code}", params={"password": "wrong"}).status_code == 403
    )
    assert (
        client.get(f"/api/v1/share/access/{code}", params={"password": "SharePass1!"}).status_code
        == 200
    )
    assert (
        client.get(f"/api/v1/share/download/{code}", params={"password": "SharePass1!"}).status_code
        == 200
    )


def test_share_cannot_target_others_file(client, user_headers, admin_headers):
    """普通用户不能分享管理员的文件。"""
    admin_file = _upload_ok(client, admin_headers, name="adminonly.txt")["id"]
    response = client.post(
        "/api/v1/share/create", json={"file_id": admin_file}, headers=user_headers
    )
    assert response.status_code == 403


def test_share_missing_file_returns_404(client, user_headers):
    response = client.post("/api/v1/share/create", json={"file_id": 999999}, headers=user_headers)
    assert response.status_code == 404
