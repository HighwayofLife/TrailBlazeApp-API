import logging
import sys
from pathlib import Path
from typing import Dict, Any

from app.config import get_settings


def configure_logging() -> Dict[str, Any]:
    """Configure logging for the application.
    
    Returns:
        Dict: Logging configuration dictionary
    """
    settings = get_settings()
    log_path = Path("logs")
    log_path.mkdir(exist_ok=True)
    
    log_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": {
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S",
            },
            "json": {
                "()": "pythonjsonlogger.jsonlogger.JsonFormatter",
                "format": "%(asctime)s %(name)s %(levelname)s %(message)s",
            },
        },
        "handlers": {
            "console": {
                "level": settings.LOG_LEVEL,
                "class": "logging.StreamHandler",
                "formatter": "default",
                "stream": sys.stdout,
            },
            "file": {
                "level": settings.LOG_LEVEL,
                "class": "logging.handlers.RotatingFileHandler",
                "formatter": "json",
                "filename": log_path / "app.log",
                "maxBytes": 10485760,  # 10MB
                "backupCount": 5,
                "encoding": "utf-8",
            },
        },
        "loggers": {
            "app": {
                "handlers": ["console", "file"],
                "level": settings.LOG_LEVEL,
                "propagate": False,
            },
            "uvicorn": {
                "handlers": ["console", "file"],
                "level": settings.LOG_LEVEL,
                "propagate": False,
            },
            "sqlalchemy.engine": {
                "handlers": ["console", "file"],
                "level": "WARNING",
                "propagate": False,
            },
        },
    }
    
    return log_config


def get_logger(name: str) -> logging.Logger:
    """Get a logger with the specified name.
    
    Args:
        name: Name for the logger
        
    Returns:
        logging.Logger: Configured logger instance
    """
    return logging.getLogger(f"app.{name}")
