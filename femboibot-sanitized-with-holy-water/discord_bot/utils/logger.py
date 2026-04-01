"""
Logger Utility for Femmy Discord Bot
=====================================
Centralized logging with file rotation and colored console output.
"""

import json
import logging
import sys
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path


LOG_DIR = Path(__file__).parent.parent / "logs"
LOG_FILE = LOG_DIR / "femmy.log"
MAX_BYTES = 10 * 1024 * 1024
BACKUP_COUNT = 5
LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


class Colors:
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
    LEVEL_COLORS = {
        logging.DEBUG: Colors.CYAN,
        logging.INFO: Colors.GREEN,
        logging.WARNING: Colors.YELLOW,
        logging.ERROR: Colors.RED,
        logging.CRITICAL: Colors.BOLD + Colors.RED,
    }

    def format(self, record: logging.LogRecord) -> str:
        color = self.LEVEL_COLORS.get(record.levelno, Colors.WHITE)
        record.levelname = f"{color}{record.levelname}{Colors.RESET}"
        record.name = f"{Colors.BLUE}{record.name}{Colors.RESET}"
        return super().format(record)


def _ensure_log_dir() -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)


def _create_file_handler() -> RotatingFileHandler:
    _ensure_log_dir()
    handler = RotatingFileHandler(
        LOG_FILE,
        maxBytes=MAX_BYTES,
        backupCount=BACKUP_COUNT,
        encoding="utf-8",
    )
    handler.setLevel(logging.DEBUG)
    handler.setFormatter(logging.Formatter(LOG_FORMAT, DATE_FORMAT))
    return handler


def _create_console_handler() -> logging.StreamHandler:
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.INFO)
    handler.setFormatter(ColoredFormatter(LOG_FORMAT, DATE_FORMAT))
    return handler


_file_handler: RotatingFileHandler | None = None
_console_handler: logging.StreamHandler | None = None
_initialized = False


def _init_handlers() -> None:
    global _file_handler, _console_handler, _initialized
    if _initialized:
        return
    _file_handler = _create_file_handler()
    _console_handler = _create_console_handler()
    _initialized = True


def get_logger(name: str, level: int = logging.DEBUG) -> logging.Logger:
    _init_handlers()
    logger = logging.getLogger(name)
    logger.setLevel(level)
    if not logger.handlers:
        logger.addHandler(_file_handler)
        logger.addHandler(_console_handler)
    logger.propagate = False
    return logger


def log_startup() -> None:
    logger = get_logger("startup")
    logger.info("=" * 50)
    logger.info("Femmy Bot Starting at %s", datetime.now().isoformat())
    logger.info("=" * 50)


def log_error(error: Exception, context: str = "") -> None:
    logger = get_logger("error")
    message = f"{context}: {error}" if context else str(error)
    logger.error(message, exc_info=True)


def log_command(command: str, user_id: int, guild_id: int | None = None) -> None:
    logger = get_logger("commands")
    location = f"guild:{guild_id}" if guild_id else "DM"
    logger.info("Command !%s by user:%s in %s", command, user_id, location)


def log_api_call(api: str, success: bool, duration_ms: float = 0) -> None:
    logger = get_logger("api")
    status = "OK" if success else "FAIL"
    logger.info("API %s %s (%.0fms)", api, status, duration_ms)


def log_stream_event(name: str, **fields) -> None:
    logger = get_logger(name)
    logger.info("stream_event %s", json.dumps(fields, ensure_ascii=False, default=str, sort_keys=True))


def log_stream_result(name: str, **fields) -> None:
    logger = get_logger(name)
    logger.info("stream_result %s", json.dumps(fields, ensure_ascii=False, default=str, sort_keys=True))
