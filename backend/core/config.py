from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator
import secrets


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False
    )

    # 应用基础配置
    APP_NAME: str = "MyPortal"
    DEBUG: bool = False
    SECRET_KEY: str = Field(default="", min_length=32)

    @field_validator("SECRET_KEY", mode="after")
    @classmethod
    def validate_secret_key(cls, v: str, info) -> str:
        if not v or len(v) < 32:
            if info.data.get("DEBUG", False):
                generated = secrets.token_urlsafe(32)
                print("WARNING: 开发模式使用随机生成的 SECRET_KEY，生产环境请务必设置")
                return generated
            raise ValueError("❌ 必须在 .env 中设置长度 ≥32 的 SECRET_KEY")
        return v

    # 数据库
    DATABASE_URL: str = "sqlite+aiosqlite:///./myportal.db"

    # Redis（可选）
    REDIS_URL: str = ""
    REDIS_ENABLED: bool = False

    @field_validator("REDIS_ENABLED", mode="before")
    @classmethod
    def set_redis_enabled(cls, v, info) -> bool:
        return bool(info.data.get("REDIS_URL", ""))

    # MeiliSearch（可选）
    MEILISEARCH_URL: str = ""
    MEILISEARCH_API_KEY: str = ""

    # JWT
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Argon2 密码哈希参数
    ARGON2_TIME_COST: int = 3
    ARGON2_MEMORY_COST: int = 65536
    ARGON2_PARALLELISM: int = 4

    # 文件上传
    UPLOAD_DIR: str = "uploads"
    PREVIEW_TEMP_DIR: str = "preview_temp"
    MAX_UPLOAD_SIZE: int = 10485760  # 10MB

    # CORS
    CORS_ORIGINS: list[str] = ["http://localhost:5173"]

    # 分页默认值
    PAGE_SIZE_DEFAULT: int = 20

    # 聊天消息长度限制
    CHAT_MESSAGE_MAX_LENGTH: int = 500

    # 数据库连接池
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20
    DB_POOL_RECYCLE: int = 3600


settings = Settings()