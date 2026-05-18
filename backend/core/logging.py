"""
Structured logging configuration for GradeOps.

Provides:
- JSON-formatted logs in production for log aggregation (ELK, Datadog)
- Human-readable colored logs in development
- Request correlation IDs via contextvars
- Configurable log levels per environment
"""
import logging
import sys
import json
import uuid
from contextvars import ContextVar
from datetime import datetime, timezone
from typing import Optional

from backend.config import get_settings

# Context variable for request correlation
request_id_var: ContextVar[Optional[str]] = ContextVar("request_id", default=None)


class JSONFormatter(logging.Formatter):
    """Structured JSON log formatter for production environments."""

    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add request correlation ID if available
        req_id = request_id_var.get()
        if req_id:
            log_data["request_id"] = req_id

        # Add exception info
        if record.exc_info and record.exc_info[0]:
            log_data["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
            }

        # Add any extra fields
        for key in ("user_id", "exam_id", "task_id", "duration_ms"):
            if hasattr(record, key):
                log_data[key] = getattr(record, key)

        return json.dumps(log_data, default=str)


class DevFormatter(logging.Formatter):
    """Human-readable formatter for development."""

    COLORS = {
        "DEBUG": "\033[36m",     # Cyan
        "INFO": "\033[32m",      # Green
        "WARNING": "\033[33m",   # Yellow
        "ERROR": "\033[31m",     # Red
        "CRITICAL": "\033[35m",  # Magenta
    }
    RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        color = self.COLORS.get(record.levelname, self.RESET)
        req_id = request_id_var.get()
        prefix = f"[{req_id[:8]}] " if req_id else ""
        return (
            f"{color}{record.levelname:8s}{self.RESET} "
            f"{prefix}{record.name}: {record.getMessage()}"
        )


def setup_logging() -> None:
    """Configure logging based on environment settings."""
    settings = get_settings()

    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO))

    # Clear existing handlers
    root_logger.handlers.clear()

    handler = logging.StreamHandler(sys.stdout)

    if settings.ENVIRONMENT == "production":
        handler.setFormatter(JSONFormatter())
    else:
        handler.setFormatter(DevFormatter())

    root_logger.addHandler(handler)

    # Quiet noisy libraries
    for lib in ("uvicorn.access", "httpcore", "httpx", "sqlalchemy.engine"):
        logging.getLogger(lib).setLevel(logging.WARNING)

    logging.getLogger("uvicorn.error").setLevel(logging.INFO)


def get_logger(name: str) -> logging.Logger:
    """Get a named logger — use this instead of logging.getLogger() directly."""
    return logging.getLogger(f"gradeops.{name}")


def generate_request_id() -> str:
    """Generate a new request correlation ID."""
    return uuid.uuid4().hex[:16]
