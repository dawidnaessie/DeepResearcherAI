"""Production-grade structured logging subsystem using Loguru.

Configures:
1. Colorized console output to sys.stdout.
2. logs/app.log: Structured JSON sink (INFO+) with 10MB rotation, 7-day retention, zip compression.
3. logs/error.log: Diagnostic stack trace sink (ERROR+) with backtrace and diagnose enabled.
4. Interception of standard library logging records.
"""

import json
import logging
from pathlib import Path
import sys
from typing import Any
from loguru import logger

# Directory for structured log files
LOGS_DIR = Path("logs")


def _json_formatter(record: dict[str, Any]) -> str:
    """Format log record as a structured single-line JSON string."""
    # Exclude internal serialization key if present
    extra_payload = {
        k: v for k, v in record["extra"].items() if k != "_json_payload"
    }

    log_payload = {
        "timestamp": record["time"].strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
        "level": record["level"].name,
        "module": record["module"],
        "function": record["function"],
        "message": record["message"],
        "extra": extra_payload,
    }

    record["extra"]["_json_payload"] = json.dumps(log_payload, default=str)
    return "{extra[_json_payload]}\n"


class InterceptHandler(logging.Handler):
    """Intercept standard library logging and forward to Loguru."""

    def emit(self, record: logging.LogRecord) -> None:
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        frame, depth = logging.currentframe(), 2
        while frame and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(
            level, record.getMessage()
        )


def setup_logging(log_dir: Path | str = LOGS_DIR) -> None:
    """Initialize and configure centralized Loguru logging sinks.

    Args:
        log_dir: Base directory where log files will be persisted.
    """
    target_dir = Path(log_dir)
    target_dir.mkdir(parents=True, exist_ok=True)

    # Remove default Loguru handler
    logger.remove()

    # 1. Console Output: Human-readable, colorized stream
    logger.add(
        sys.stdout,
        level="INFO",
        format=(
            "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
            "<level>{message}</level>"
        ),
        colorize=True,
        backtrace=False,
        diagnose=False,
    )

    # 2. General App Log: Structured JSON sink (INFO and above)
    app_log_path = target_dir / "app.log"
    logger.add(
        str(app_log_path),
        level="INFO",
        format=_json_formatter,
        rotation="10 MB",
        retention="7 days",
        compression="zip",
        encoding="utf-8",
        enqueue=True,  # Thread-safe async queueing
    )

    # 3. Error Diagnostic Log: Full stack traces and diagnose (ERROR and above)
    error_log_path = target_dir / "error.log"
    logger.add(
        str(error_log_path),
        level="ERROR",
        format=(
            "{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | "
            "{name}:{function}:{line} - {message}\n{exception}"
        ),
        rotation="10 MB",
        retention="7 days",
        compression="zip",
        encoding="utf-8",
        backtrace=True,
        diagnose=True,
        enqueue=True,
    )

    # Intercept standard library logging (FastAPI, uvicorn, etc.)
    logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)
    for logger_name in ("uvicorn", "uvicorn.access", "uvicorn.error", "fastapi"):
        logging_logger = logging.getLogger(logger_name)
        logging_logger.handlers = [InterceptHandler()]
        logging_logger.propagate = False


def get_logger(name: str | None = None):
    """Return a logger bound with an optional context name."""
    if name:
        return logger.bind(logger_name=name)
    return logger


# Automatically configure logging on module import
setup_logging()
