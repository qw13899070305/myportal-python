import sys
from pathlib import Path
from loguru import logger
from backend.core.config import settings

def setup_logging():
    logger.remove()
    logger.add(
        sys.stdout,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
        level="DEBUG" if settings.DEBUG else "INFO",
        colorize=True,
        backtrace=True,
        diagnose=settings.DEBUG,
    )
    if not settings.DEBUG:
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        logger.add(
            log_dir / "app_{time:YYYY-MM-DD}.log",
            rotation="00:00",
            retention="30 days",
            compression="zip",
            level="INFO",
            backtrace=True,
        )
    return logger

# 初始化全局 logger
logger = setup_logging()