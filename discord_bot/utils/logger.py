"""
Logger Utility for Femmy Discord Bot
=====================================
Centralized logging with file rotation and colored console output.

Features:
    - File-based logging to logs/femmy.log
    - Log rotation (10MB max, 5 backups)
    - Console + file output
    - Colored console output for different levels

Usage:
    from utils.logger import get_logger
    logger = get_logger(__name__)
    logger.info("Bot started")
    logger.error("API failed", exc_info=True)
"""

import os
import sys
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from datetime import datetime


# ============================================
# Configuration
# ============================================

LOG_DIR = Path(__file__).parent.parent / "logs"
LOG_FILE = LOG_DIR / "femmy.log"
MAX_BYTES = 10 * 1024 * 1024  # 10 MB
BACKUP_COUNT = 5
LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


# ============================================
# Color Codes for Console
# ============================================

class Colors:
    """ANSI color codes for console output."""
    RESET = "\033[0m"
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN = "\033[96m"
    WHITE = "\033[97m"
    BOLD = "\033[1m"


class ColoredFormatter(logging.Formatter):
    """Custom formatter with colored output for console."""
    
    LEVEL_COLORS = {
        logging.DEBUG: Colors.CYAN,
        logging.INFO: Colors.GREEN,
        logging.WARNING: Colors.YELLOW,
        logging.ERROR: Colors.RED,
        logging.CRITICAL: Colors.BOLD + Colors.RED,
    }
    
    def format(self, record: logging.LogRecord) -> str:
        # Color the level name
        color = self.LEVEL_COLORS.get(record.levelno, Colors.WHITE)
        record.levelname = f"{color}{record.levelname}{Colors.RESET}"
        
        # Color the name (module)
        record.name = f"{Colors.BLUE}{record.name}{Colors.RESET}"
        
        return super().format(record)


# ============================================
# Logger Setup
# ============================================

def _ensure_log_dir() -> None:
    """Create logs directory if it doesn't exist."""
    LOG_DIR.mkdir(parents=True, exist_ok=True)


def _create_file_handler() -> RotatingFileHandler:
    """Create rotating file handler."""
    _ensure_log_dir()
    
    handler = RotatingFileHandler(
        LOG_FILE,
        maxBytes=MAX_BYTES,
        backupCount=BACKUP_COUNT,
        encoding="utf-8"
    )
    handler.setLevel(logging.DEBUG)
    handler.setFormatter(logging.Formatter(LOG_FORMAT, DATE_FORMAT))
    
    return handler


def _create_console_handler() -> logging.StreamHandler:
    """Create colored console handler."""
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.INFO)
    handler.setFormatter(ColoredFormatter(LOG_FORMAT, DATE_FORMAT))
    
    return handler


# Global handlers (shared across all loggers)
_file_handler: RotatingFileHandler | None = None
_console_handler: logging.StreamHandler | None = None
_initialized = False


def _init_handlers() -> None:
    """Initialize global handlers once."""
    global _file_handler, _console_handler, _initialized
    
    if _initialized:
        return
    
    _file_handler = _create_file_handler()
    _console_handler = _create_console_handler()
    _initialized = True


def get_logger(name: str, level: int = logging.DEBUG) -> logging.Logger:
    """
    Get a configured logger instance.
    
    Args:
        name: Logger name (usually __name__)
        level: Logging level (default: DEBUG)
        
    Returns:
        Configured logger instance
    """
    _init_handlers()
    
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Avoid duplicate handlers
    if not logger.handlers:
        logger.addHandler(_file_handler)
        logger.addHandler(_console_handler)
    
    # Don't propagate to root logger
    logger.propagate = False
    
    return logger


# ============================================
# Convenience Functions
# ============================================

def log_startup() -> None:
    """Log bot startup with separator."""
    logger = get_logger("startup")
    logger.info("=" * 50)
    logger.info(f"Femmy Bot Starting at {datetime.now().isoformat()}")
    logger.info("=" * 50)


def log_error(error: Exception, context: str = "") -> None:
    """
    Log an error with full traceback.
    
    Args:
        error: The exception to log
        context: Optional context message
    """
    logger = get_logger("error")
    message = f"{context}: {error}" if context else str(error)
    logger.error(message, exc_info=True)


def log_command(command: str, user_id: int, guild_id: int | None = None) -> None:
    """
    Log command execution.
    
    Args:
        command: Command name
        user_id: User who executed
        guild_id: Server ID (None for DMs)
    """
    logger = get_logger("commands")
    location = f"guild:{guild_id}" if guild_id else "DM"
    logger.info(f"Command !{command} by user:{user_id} in {location}")


def log_api_call(api: str, success: bool, duration_ms: float = 0) -> None:
    """
    Log API call result.
    
    Args:
        api: API name (e.g., "gemini", "vision")
        success: Whether call succeeded
        duration_ms: Call duration in milliseconds
    """
    logger = get_logger("api")
    status = "✓" if success else "✗"
    logger.info(f"API {api} {status} ({duration_ms:.0f}ms)")
