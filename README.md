# myportal-python

基于 FastAPI + Vue 3 的全栈信息门户，包含用户系统、文件管理、文章发布、实时聊天、后台管理。

## 特性
- JWT 认证与角色控制（访问/刷新令牌轮换、退出即失效）
- 文件上传 / 下载 / 预览（扩展名 + 魔数双重校验）、回收站、分享链接
- 电子书在线阅读：EPUB / AZW3 / MOBI / CHM 直接在浏览器里翻阅（解析层出纯数据，JSON 接口可给 APP 用）
- 视频 / 音频 / 图片用浏览器原生控件播放，后端只提供支持 `Range` 的字节流
- Markdown 文章：标签、分类、点赞、收藏、评论、发布审核
- 实时聊天：socket.io 与原生 WebSocket 双通道，支持 @提及和撤回
- 通知中心（站内提醒）、审计日志、图形验证码、限流、CSRF 防护
- 暗黑模式切换、中英文切换、PWA
- Docker 一键部署

## 快速开始

### 1. 配置

```bash
cp .env.example .env
```

编辑 `.env`，**必须**填写 `SECRET_KEY`（少于 32 字符会直接启动失败）：

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

建议同时填写 `ADMIN_USERNAME` / `ADMIN_PASSWORD`：首次启动会自动创建管理员账号，
不填的话没有任何管理员，后台功能无法使用。

> Redis 是可选的。`REDIS_URL` 留空即可，此时令牌黑名单退化为进程内存储，
> 单进程部署下"退出登录立即失效"依然有效。
>
> **配了 `REDIS_ENABLED=true` 但没装 Redis 也不会出问题**：启动时会做一次
> 可用性探测，连不上就整体降级（socket.io 退回单机模式、黑名单走进程内），
> 只在启动日志里提示一次，不会每请求重试、也不会刷屏。
> 代价是多副本部署时进程之间不互通消息 —— 单机使用完全无感。

### 2. 后端

```bash
pip install -r requirements.txt
python app.py                      # http://localhost:8000
```

### 3. 前端（开发模式）

```bash
cd frontend
npm install
npm run dev                        # http://localhost:5173
```

Vite 已配置 `/api` 与 `/ws` 代理（含 WebSocket），前端直接访问同源接口即可。

### 4. 生产部署

```bash
cd frontend && npm run build       # 产物输出到 frontend/dist
python app.py                      # 后端会自动挂载 frontend/dist
```

或使用 Docker：

```bash
docker compose up -d               # http://localhost:8000
```

## 常用环境变量

完整列表见 [`.env.example`](.env.example)。

| 变量 | 默认值 | 说明 |
| --- | --- | --- |
| `SECRET_KEY` | 无（必填） | JWT 签名密钥，≥32 字符 |
| `HOST` | `::` | 双栈监听（IPv4 + IPv6 都能连）；`0.0.0.0` 只听 IPv4，`127.0.0.1` 只听本机 |
| `PORT` | `8000` | 后端端口 |
| `DEBUG` | `true` | 生产环境请设为 `false`（同时控制热重载） |
| `DATABASE_URL` | 项目根目录 `data.db` | SQLite 路径（父目录会自动创建） |
| `REDIS_URL` | 空 | 留空即禁用 Redis |
| `REDIS_ENABLED` | 自动 | 只表示"想用"；**连不上会自动降级**，不影响功能 |
| `UPLOAD_DIR` | `uploads` | 相对路径会解析到项目根目录 |
| `MAX_UPLOAD_SIZE` | `32212254720`（30GB） | 单文件上限（字节）；multipart 先落临时文件，峰值占用约 2 倍 |
| `CORS_ORIGINS` | `["http://localhost:5173"]` | JSON 数组，禁止 `"*"` |
| `ALLOW_PRIVATE_NETWORK_ORIGINS` | `true` | 自动放行本机/内网来源（内网访问必需） |
| `ADMIN_USERNAME` / `ADMIN_PASSWORD` | 空 | 首次启动创建的管理员 |
| `COOKIE_SECURE` | `false` | 全站 HTTPS 时设为 `true` |
| `CSRF_ENABLED` | `true` | 未携带令牌的写操作需要 CSRF |
| `RATE_LIMIT_ENABLED` | `true` | 压测/自动化测试时可关闭 |

## 支持上传的文件类型

扩展名白名单 + 魔数校验，两者必须一致（改白名单请改
`backend/api/v1/file_common.py` 的 `ALLOWED_EXTENSIONS`）：

| 类别 | 扩展名 |
| --- | --- |
| 文本 | `.txt` `.md` `.csv` `.json` `.log` |
| 图片 | `.png` `.jpg` `.jpeg` `.gif` `.webp` `.bmp` |
| 手机照片 | `.heic` `.heif`（能传能下，浏览器不支持在线预览） |
| 文档 | `.pdf` `.doc` `.docx` `.xls` `.xlsx` `.ppt` `.pptx` |
| 压缩包 / 电子书 | `.zip` `.epub` `.azw3` `.mobi` `.chm` |
| 视频 | `.mp4` `.mov` `.3gp` `.m4v` |
| 音频 | `.mp3` `.m4a` `.wav` |

单文件上限由 `MAX_UPLOAD_SIZE` 控制（默认 30GB）。上传失败时页面上会直接显示
后端返回的原因（例如「文件大小超出限制（最大 30GB）」）。

## 文件分类

每个文件都自动带分类，**不需要人工整理**：规则只有一份，在
`backend/core/filetypes.py`，按文件名实时派生（重命名后自动跟着变，不存数据库）。

| 分类键 | 中文（客户端自己翻译） | 包含 |
| --- | --- | --- |
| `image` | 图片 | png jpg jpeg gif webp bmp heic heif |
| `document` | 文档 | txt md csv json log pdf docx xlsx pptx doc xls ppt |
| `ebook` | 电子书 | epub azw3 mobi chm |
| `video` | 视频 | mp4 mov 3gp m4v |
| `audio` | 音频 | mp3 m4a wav |
| `archive` | 压缩包 | zip |
| `other` | 其他 | 不在上表中的（历史遗留数据） |

对外只给**机器键**，中文/英文/图标由客户端翻译（网站用
`frontend/src/utils/format.js`，APP 用自家资源）。接口：

| 接口 | 说明 |
| --- | --- |
| 任意返回文件对象的接口 | 都带 `category` 字段（列表 / 最近上传 / 上传响应 / 重命名 / 回收站） |
| `GET /api/v1/files/?category=image` | 按分类筛选，参数就是上表的键；未知键返回 400 |
| `GET /api/v1/files/categories?search=` | 每个分类的文件数（含 `all` 总数），给客户端的分类标签用；统计口径与列表完全一致，标签上的数字不会和点进去看到的不一样 |

分类表与上传白名单必须一一对齐，这件事由 `backend/tests/test_file_types.py`
钉住：多一个、少一个都会测试失败。

## 在线预览 / 在线阅读的架构（前后端分离）

**后端只出数据和字节流，怎么展示是客户端的事。** 网站和手机 APP 都只是同一个
API 的不同客户端，谁也不依赖谁：

| 层 | 位置 | 产出 | 谁在用 |
| --- | --- | --- | --- |
| 解析层 | `backend/services/books/` | `Book` / `Chapter` 纯数据 | 所有客户端 |
| 网页展示层 | `backend/extensions/preview/` | HTML 页面 | 网站 |
| 接口层 | `backend/api/v1/file_*.py` | JSON / 字节流 | 网站、手机 APP、第三方界面 |

| 接口 | 返回 | 说明 |
| --- | --- | --- |
| `GET /api/v1/files/` | JSON | 文件列表，支持 `?search=` `?category=` `?page=` `?size=`，每项带 `category` |
| `GET /api/v1/files/categories` | JSON | 每个分类的文件数（分类标签用） |
| `GET /api/v1/files/{id}/book` | JSON | 电子书数据：书名/作者/章节/正文。`?chapter=N` 只取一节（懒加载），`html=0` / `text=0` 裁剪字段 |
| `GET /api/v1/files/{id}/preview` | HTML | 网页预览（PDF / Office / 电子书 / 文本…） |
| `GET /api/v1/files/{id}/raw` | 字节流 | 图片 / 音频 / 视频 / PDF **内联**，支持 `Range`、`?token=`，供 `<video>` / `<audio>` / `<img>` 与 APP 播放器直接用 |
| `GET /api/v1/files/{id}/download` | 字节流 | 附件下载，同样支持 `Range` 与 `?token=` |

解析层目录（每个格式一个子包，各自可以单独摘掉）：

```
backend/services/books/
├── model.py        Book / Chapter / BookError（不可变数据，接口就在这）
├── sanitize.py     共用 HTML 清洗（白名单、危险标签整段删、data: 内联）
├── epub/           EPUB   → Book
├── mobi/           AZW3 / MOBI → Book
└── chm/            CHM    → Book（含纯 Python 的 LZX 解码）
backend/extensions/preview/
├── book_base.py    Book → 网页（排版只写这一遍，网站专用）
└── epub.py / mobi.py / chm.py   薄适配器：只声明扩展名
```

规矩只有一条：**解析层里不许出现 HTML 外壳、CSS、界面文案**。
它一旦"顺手"渲染页面，APP 这条路就被焊死了。

## 内网 / IPv6 访问

默认配置就是**双栈监听**，内网 IPv4 和 IPv6 都能直接访问，不用改配置。

### 怎么看自己该用哪个地址

启动时会直接打印（`python app.py`）：

```
监听地址: [::]:8000, 0.0.0.0:8000
可从以下地址访问本服务（监听 8000）：
  http://192.168.1.2:8000                          [enp6s0 ipv4]
  http://[2409:8a7c:4810:d4e0:2e0:23ff:fe21:5116]:8000   [enp6s0 ipv6]
```

也可以随时查接口：`curl http://localhost:8000/health` → `access_urls` 字段。

前端 Vite 也会打印：

```
➜  Local:   http://localhost:5173/
➜  Network: http://192.168.1.2:5173/     ← 手机/别的电脑用这个
```

> Vite 默认只监听 localhost 且**不打印 Network 行**，所以这里配了 `host: '::'`。

### 四个已经踩过的坑（都已在代码里处理）

1. **`python app.py` 起不来**：`uvicorn.run(app, reload=True)` 必须传
   **导入字符串**，传 app 对象会直接报错退出（exit code 3）。
2. **绑 `::` 只听了 IPv6**：uvicorn 走 asyncio 建 socket 时，
   asyncio 会强制 `IPV6_V6ONLY=1`，导致 IPv4 内网地址
   Connection refused。所以 `backend/core/server.py` 自己建
   **IPv4 + IPv6 两个监听 socket** 再交给 uvicorn。
3. **内网 Origin 被拒**：浏览器发来的 `Origin` 是
   `http://192.168.1.2:5173`，不可能提前写进 `CORS_ORIGINS`，
   socket.io 会把聊天握手直接拒掉。现在
   `ALLOW_PRIVATE_NETWORK_ORIGINS=true` 会自动放行
   「本机/内网」来源（判据见 `backend/core/network.py`，
   核心是"该地址属于本机"），`evil.com` 之类外部域名依然被拒。
4. **热重载疯狂误触发**：uvicorn 默认监视整个工作目录且没有排除规则，
   而 `.venv` 里有 3000+ 个 `.py`。更坑的是 `.venv/lib64` 是**符号链接**，
   光靠 `reload_excludes` 盖不住（实测改一个 site-packages 文件就会全量重载）。
   现在改成白名单：**只监视 `backend/`**，前端交给 Vite 自己的 HMR。

### 手机 / 别的电脑连不上时自查

```bash
ss -tlnp | grep 8000                 # 应该同时有 0.0.0.0:8000 和 [::]:8000
curl -s http://<你的IP>:8000/health  # 换成本机内网 IP 试
```

- 只有 `[::]:8000` 没有 `0.0.0.0:8000` → 双栈没生效（检查是否用了旧的启动方式）
- 去看系统防火墙是否放行了 8000 / 5173 端口

## 扩展机制（可拆卸设计）

每个文件都是一个可以**单独摘掉**的零件：摘掉之后，其余部分照常工作，
只会少掉那一个功能。已用测试固化这个性质（`backend/tests/test_detachability.py`）。

### 预览扩展 —— 新增一种文档格式

只要往 `backend/extensions/preview/` 里丢一个文件，**自动生效**：

```python
# backend/extensions/preview/foo.py
from backend.extensions.preview.base import Preview, PreviewHandler
from backend.extensions.registry import get_registry


class FooPreview(PreviewHandler):
    name = "foo"
    extensions = frozenset({".foo"})
    priority = 10                      # 越大越先匹配；兜底扩展是 -100

    def render(self, path):
        return Preview.html_page(self.wrap_html(f"<p>{self.escape(path.name)}</p>"))


get_registry("preview").register(FooPreview())
```

- 删掉这个文件 → 该格式自动降级到兜底提示页，其它格式不受影响
- 某个扩展导入失败（缺依赖、写错了）→ 只记一条日志并跳过它
- 额外能力用鸭子类型暴露（参考 `pdf.py` 的 `page_count` / `render_page`），
  删掉 pdf.py 时接口层会给出 400 而不是崩掉

### 搜索后端 / 验证码 —— 可替换的实现

同样是"丢文件即生效"的注册表：

| 目录 | 换什么 | 现有零件 |
| --- | --- | --- |
| `backend/extensions/search/` | 搜索引擎，按 `priority` 挑第一个可用的 | `database.py`（兜底）、`meilisearch.py` |
| `backend/extensions/captcha/` | 验证码渲染器与存储 | `image.py`（Pillow）、`store_memory.py` |

想接 Elasticsearch 就加 `backend/extensions/search/elasticsearch.py`；
想换成滑块验证就加 `backend/extensions/captcha/slider.py` 并给更高的 `priority`。
某个后端调用失败会自动降级到下一个，**搜索不会因为外部服务挂掉而不可用**。

### API 模块 —— 两级可拆卸

**第一级：整组**（`backend/api/v1/__init__.py`）

| 表 | 行为 | 放什么 |
| --- | --- | --- |
| `CORE_ROUTERS` | 导入失败直接抛错 | 基本盘：auth / users / files / articles / chat / admin |
| `EXTRA_ROUTERS` | 导入失败只记日志并跳过 | 预览、回收站、分享、评论、点赞、审核、通知、审计…… |

**第二级：组内**（`auth.py` / `articles.py` / `files.py` 各自的 `PARTS` 表）

以认证组为例，7 个零件各自独立：

```
auth.py           只负责组合（56 行）
auth_common.py    公共内核：签发令牌、解析登录请求、登录主流程
auth_register.py  POST /register
auth_login.py     POST /login, POST /token
auth_token.py     POST /refresh, POST /logout
auth_profile.py   GET  /me, POST /change-password, GET /check-username
auth_captcha.py   GET  /captcha
auth_avatar.py    POST/GET/DELETE /avatar
auth_csrf.py      GET  /csrf-token
```

两级用的是同一套加载器 `backend/api/v1/_loader.py`，
所以"已挂载 / 被跳过"只有一份记录。删掉任何一个零件都只影响它自己，
启动日志会写明跳过了哪些，`GET /health` 也能看到实际加载结果。

### 前端 —— 页面只负责组合

```
components/layout/   AppSidebar / AppTopbar / MobileNav
components/files/    FileCard / FileUploader / FileSearchBar / RenameDialog /
                     ShareDialog / FileContextMenu
components/articles/ ArticleHeader / ArticleActions / ArticleBody / ArticleCard /
                     CommentSection / ArticleFilterBar / ArticleTagFilter
components/admin/    ArticleReviewCard / SiteBasicForm / CategoryManager / AuditFilterBar
components/profile/  AvatarCard / PasswordForm / SideLists
components/common/   DataTable / LoadMore / PageHeader / Toolbar
router/routes/       auth.js / main.js / admin.js / index.js   + guards.js
utils/               request.js（只管 axios） / csrf.js / errors.js /
                     realtime.js / format.js
```

页面本身只剩"取数据 + 组合零件 + 调接口"，例如 `Profile.vue` 只有 21 行。
`DataTable` 这类通用零件被后台 5 个页面复用，改一处全都受益。

### socket.io 事件 —— 一个事件一个文件

`backend/socketio/events/` 下的模块**导入即注册**（`@sio.event` 装饰器）：

- `connection.py` → connect / disconnect / join
- `message.py` → send_message
- `revoke.py` → revoke_message

删掉 `revoke.py`，撤回事件就没了，收发消息照常。

### 前端工具 —— 各管一件事

| 文件 | 职责 |
| --- | --- |
| `utils/request.js` | axios 实例 + 拦截器（其它都不管） |
| `utils/csrf.js` | CSRF 令牌获取与判定 |
| `utils/errors.js` | 错误归一化成中文提示 |
| `utils/realtime.js` | socket.io 连接封装 |
| `utils/format.js` | 纯格式化函数（有单测） |

### 自检

`GET /health` 会返回当前实际加载的扩展清单：

```json
{
  "status": "ok",
  "database": true,
  "redis": "disabled",
  "extensions": { "preview": ["excel", "fallback", "image", "pdf", "ppt", "text", "word"] }
}
```

## 测试

```bash
pytest                             # 后端 197 个用例（含可拆卸性、内网、双栈监听测试）
ruff check backend/                # 后端静态检查

cd frontend
npm test                           # 前端 19 个单元测试
npm run lint                       # ESLint
npm run build                      # 生产构建
```

## 许可证
MIT
