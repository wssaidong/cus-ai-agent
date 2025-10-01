"""
日志工具模块
"""
import sys
from loguru import logger
from src.config import settings


def setup_logger():
    """配置日志"""
    # 移除默认处理器
    logger.remove()
    
    # 添加控制台处理器
    if settings.log_format == "json":
        logger.add(
            sys.stdout,
            format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {name}:{function}:{line} | {message}",
            level=settings.log_level,
            serialize=True,
        )
    else:
        logger.add(
            sys.stdout,
            format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
            level=settings.log_level,
            colorize=True,
        )
    
    # 添加文件处理器
    logger.add(
        "logs/app_{time:YYYY-MM-DD}.log",
        rotation="00:00",
        retention="30 days",
        level=settings.log_level,
        encoding="utf-8",
    )
    
    return logger


# 初始化日志
app_logger = setup_logger()

