import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # 应用基础配置
    APP_NAME: str = "MyPortal"
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
    SECRET_KEY: str = os.getenv("SECRET_KEY", "")
    if not SECRET_KEY or len(SECRET_KEY) < 32:
        if DEBUG:
            import secrets
            SECRET_KEY = secrets.token_urlsafe(32)
            print("WARNING: 开发模式使用随机生成的 SECRET_KEY，生产环境请务必设置")
        else:
            raise ValueError("❌ 必须在 .env 中设置长度 ≥32 的 SECRET_KEY")

    # 数据库
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./myportal.db")

    # Redis（可选）
    REDIS_URL: str = os.getenv("REDIS_URL", "")
    REDIS_ENABLED: bool = bool(REDIS_URL)

    # MeiliSearch（可选）
    MEILISEARCH_URL: str = os.getenv("MEILISEARCH_URL", "")
    MEILISEARCH_API_KEY: str = os.getenv("MEILISEARCH_API_KEY", "")

    # JWT
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
    REFRESH_TOKEN_EXPIRE_DAYS: int = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))

    # 文件上传
    UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", "uploads")
    MAX_UPLOAD_SIZE: int = int(os.getenv("MAX_UPLOAD_SIZE", "10485760"))  # 10MB

    # CORS
    CORS_ORIGINS: list = os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")

    # 分页默认值
    PAGE_SIZE_DEFAULT: int = 20

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()