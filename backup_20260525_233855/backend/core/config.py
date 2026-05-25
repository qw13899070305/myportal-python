import os
from pathlib import Path
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "myportal-python"
    VERSION: str = "0.1.0"
    DEBUG: bool = True

    SECRET_KEY: str = os.getenv("SECRET_KEY", "")
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./data.db")

    UPLOAD_DIR: Path = Path(os.getenv("UPLOAD_DIR", "./uploads"))
    PREVIEW_TEMP_DIR: Path = Path(os.getenv("PREVIEW_TEMP_DIR", "./preview_temp"))

    CHAT_MAX_MESSAGES: int = 500
    CHAT_RECALL_WINDOW_MINUTES: int = 2

    class Config:
        env_file = ".env"

settings = Settings()

if not settings.SECRET_KEY or len(settings.SECRET_KEY) < 32:
    raise ValueError("❌ 必须在 .env 中设置长度 ≥32 的 SECRET_KEY")
