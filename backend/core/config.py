"""应用配置。

所有可调参数集中在此，可通过环境变量或项目根目录下的 ``.env`` 覆盖。
导入本模块即得到全局唯一实例 ``settings``。
"""

from pathlib import Path

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# 项目根目录（backend/core/config.py -> backend -> 项目根）
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# 明确禁止的弱密钥
_WEAK_SECRET_KEYS = {
    "",
    "your-secret-key-here",
    "changeme",
    "change-me",
    "secret",
    "super-secret-key",
}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ---------------- 基础 ----------------
    APP_NAME: str = "MyPortal"
    DEBUG: bool = False
    LOG_LEVEL: str = "DEBUG"

    # ---------------- 安全 ----------------
    # 必填，且长度 >= 32，不允许弱默认值（保证部署时不会忘记配置）
    SECRET_KEY: str = Field(..., min_length=32)

    @field_validator("SECRET_KEY", mode="after")
    @classmethod
    def validate_secret_key(cls, v: str) -> str:
        if v.strip().lower() in _WEAK_SECRET_KEYS:
            raise ValueError("SECRET_KEY 不能为已知弱密钥，请更换为随机长字符串")
        if len(v) < 32:
            raise ValueError("SECRET_KEY 长度至少为 32 字符")
        return v

    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    ARGON2_TIME_COST: int = 3
    ARGON2_MEMORY_COST: int = 65536
    ARGON2_PARALLELISM: int = 4

    # ---------------- 数据库 ----------------
    BASE_DIR: Path = BASE_DIR
    DATABASE_URL: str = f"sqlite+aiosqlite:///{BASE_DIR / 'data.db'}"
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20
    DB_POOL_RECYCLE: int = 3600
    DB_POOL_PRE_PING: bool = False

    # ---------------- Redis（可选）----------------
    REDIS_URL: str = ""
    REDIS_ENABLED: bool = False
    REDIS_POOL_SIZE: int = 20

    @model_validator(mode="after")
    def resolve_redis_enabled(self) -> "Settings":
        """未显式配置 ``REDIS_ENABLED`` 时，依据是否提供 ``REDIS_URL`` 自动推导。

        显式配置优先，这样既能保留 REDIS_URL 又临时关掉 Redis，
        也不会因为 .env 里写了 REDIS_URL 但没装 Redis 就让所有请求失败。
        """
        if "REDIS_ENABLED" not in self.model_fields_set:
            self.REDIS_ENABLED = bool(self.REDIS_URL.strip())
        return self

    # ---------------- 全文搜索（可选）----------------
    MEILISEARCH_URL: str = ""
    MEILISEARCH_API_KEY: str = ""

    # ---------------- 上传 ----------------
    UPLOAD_DIR: Path = BASE_DIR / "uploads"
    #: 单个文件上限。注意：multipart 会先落到临时文件再复制进 UPLOAD_DIR，
    #: 上传过程中峰值占用约为文件大小的 2 倍。
    MAX_UPLOAD_SIZE: int = 30 * 1024 * 1024 * 1024  # 30GB（手机录像也能传）

    @field_validator("UPLOAD_DIR", mode="after")
    @classmethod
    def resolve_upload_dir(cls, v: Path) -> Path:
        """相对路径统一解析到项目根目录，避免受启动时工作目录影响。"""
        return v if v.is_absolute() else (BASE_DIR / v).resolve()

    # ---------------- 监听地址 ----------------
    # 默认 "::" —— 双栈监听，IPv4 与 IPv6 都能连上
    # （Linux 的 net.ipv6.bindv6only=0 时，绑 :: 会同时接受 IPv4 连接）。
    # 只想听本机就改成 "127.0.0.1"；只想听 IPv4 内网就改成 "0.0.0.0"。
    HOST: str = "::"
    PORT: int = 8000

    # ---------------- CORS ----------------
    # 环境变量中写成 JSON 数组，例如 ["http://localhost:5173"]
    CORS_ORIGINS: list[str] = ["http://localhost:5173"]

    @field_validator("CORS_ORIGINS", mode="after")
    @classmethod
    def reject_wildcard_cors(cls, v: list[str]) -> list[str]:
        if "*" in v:
            raise ValueError(
                "CORS_ORIGINS 不允许使用通配符 '*'（与 allow_credentials=True 冲突），"
                "请显式列出允许的来源"
            )
        return v

    # 自动放行"本机 / 内网"来源（回环、私有网段、以及本机自己拥有的地址）。
    #
    # 为什么需要它：内网访问时浏览器发来的 Origin 是 http://192.168.1.2:5173
    # 或 http://[2409:...]:5173，而这些**不在** CORS_ORIGINS 里，
    # 会导致 WebSocket / socket.io 握手被拒。
    #
    # 为什么不能只放行私有网段：很多宽带下发的 IPv6 是**全球单播**
    # （2409: 开头这类），is_private 判不出来，但用户就是用它访问的。
    #
    # 安全性：放行的前提是"该地址属于本机"，外部域名（evil.com）依然被拒。
    # 需要严格白名单时设为 false。
    ALLOW_PRIVATE_NETWORK_ORIGINS: bool = True

    # ---------------- 限流 ----------------
    RATE_LIMIT_ENABLED: bool = True

    # ---------------- CSRF ----------------
    # 对"未携带 Bearer 令牌的写请求"（登录/注册/申请）启用 CSRF 校验。
    # 纯 API 调用方可通过设为 false 关闭。
    CSRF_ENABLED: bool = True

    # 是否给 CSRF Cookie 加 Secure 标记。
    # 默认 False —— 本地开发与内网 HTTP 部署必须为 False，
    # 否则浏览器不会回传 Cookie，登录会直接 403。
    # 已经全站 HTTPS 时请设为 true。
    COOKIE_SECURE: bool = False

    # ---------------- 分页 ----------------
    PAGE_SIZE_DEFAULT: int = 20
    PAGE_SIZE_MAX: int = 100

    # ---------------- 聊天 ----------------
    CHAT_MESSAGE_MAX_LENGTH: int = 500
    CHAT_RECALL_WINDOW_MINUTES: int = 2
    CHAT_MAX_MESSAGES: int = 200

    # ---------------- 分享链接 ----------------
    SHARE_LINK_EXPIRE_HOURS: int = 24

    # ---------------- 登录验证码 ----------------
    # 同一账号/IP 连续失败达到该次数后，登录必须携带验证码
    CAPTCHA_TRIGGER_FAILURES: int = 3
    CAPTCHA_EXPIRE_SECONDS: int = 300

    # ---------------- 初始管理员（可选）----------------
    # 首次启动且该用户不存在时自动创建，创建后请尽快修改密码
    ADMIN_USERNAME: str = ""
    ADMIN_PASSWORD: str = ""
    ADMIN_EMAIL: str = ""


settings = Settings()
