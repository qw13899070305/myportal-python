from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", case_sensitive=True, extra="ignore")
    PROJECT_NAME: str = "myportal-python"
    VERSION: str = "0.1.0"
    DEBUG: bool = True
    HOST: str = "::"
    PORT: int = 8000
    DATABASE_URL: str = "sqlite+aiosqlite:///./myportal.db"
    SECRET_KEY: str = "change-me-in-production-please!!"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    UPLOAD_DIR: Path = Path("./uploads")
    PREVIEW_TEMP_DIR: Path = Path("./preview_temp")
    MAX_UPLOAD_SIZE: int = 100 * 1024 * 1024
    ALLOWED_EXTENSIONS: list[str] = ["jpg","jpeg","png","gif","pdf","doc","docx","xls","xlsx","ppt","pptx","txt","zip","rar","mp4","avi"]
    LOGIN_MAX_ATTEMPTS: int = 5
    LOGIN_LOCKOUT_MINUTES: int = 15
    CHAT_MAX_MESSAGES: int = 200
    CHAT_RECALL_WINDOW_MINUTES: int = 5
    SHARE_LINK_EXPIRE_HOURS: int = 24
    CSP_POLICY: str = "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com; font-src 'self' https://cdnjs.cloudflare.com; img-src 'self' data:; media-src 'self'; frame-src 'self' https://view.officeapps.live.com; connect-src 'self' ws: wss:"
settings = Settings()
