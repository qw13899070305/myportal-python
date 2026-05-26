from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False
    )

    APP_NAME: str = "MyPortal"
    DEBUG: bool = False
    # 强制必须设置，不再自动生成
    SECRET_KEY: str = Field(..., min_length=32)

    @field_validator("SECRET_KEY", mode="after")
    @classmethod
    def validate_secret_key(cls, v: str) -> str:
        if len(v) < 32:
            raise ValueError("SECRET_KEY 长度必须至少为 32 个字符")
        return v

    DATABASE_URL: str = "sqlite+aiosqlite:///./myportal.db"
    REDIS_URL: str = ""
    REDIS_ENABLED: bool = False

    @field_validator("REDIS_ENABLED", mode="before")
    @classmethod
    def set_redis_enabled(cls, v, info) -> bool:
        return bool(info.data.get("REDIS_URL", ""))

    MEILISEARCH_URL: str = ""
    MEILISEARCH_API_KEY: str = ""

    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    ARGON2_TIME_COST: int = 3
    ARGON2_MEMORY_COST: int = 65536
    ARGON2_PARALLELISM: int = 4

    UPLOAD_DIR: str = "uploads"
    PREVIEW_TEMP_DIR: str = "preview_temp"
    MAX_UPLOAD_SIZE: int = 10 * 1024 * 1024  # 10MB

    CORS_ORIGINS: list[str] = ["http://localhost:5173"]
    PAGE_SIZE_DEFAULT: int = 20
    CHAT_MESSAGE_MAX_LENGTH: int = 500

    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20
    DB_POOL_RECYCLE: int = 3600
    DB_POOL_PRE_PING: bool = False


settings = Settings()