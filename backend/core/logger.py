"""日志初始化（loguru）。"""

import sys
from pathlib import Path

from loguru import logger as _logger

from backend.core.config import BASE_DIR, settings

_LOG_FORMAT = (
    "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | "
    "<cyan>{name}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
)


def setup_logging():
    """重新配置全局 logger 并返回它。"""
    _logger.remove()
    _logger.add(
        sys.stdout,
        format=_LOG_FORMAT,
        # 以 LOG_LEVEL 为准，DEBUG=True 时至少输出 DEBUG
        level="DEBUG" if settings.DEBUG else settings.LOG_LEVEL.upper(),
        colorize=True,
        backtrace=True,
        diagnose=settings.DEBUG,
    )
    if not settings.DEBUG:
        log_dir = Path(BASE_DIR) / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        _logger.add(
            log_dir / "app_{time:YYYY-MM-DD}.log",
            rotation="00:00",
            retention="30 days",
            compression="zip",
            level=settings.LOG_LEVEL.upper(),
            backtrace=True,
            encoding="utf-8",
        )
    return _logger


# 初始化全局 logger
logger = setup_logging()
