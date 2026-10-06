"""Structured logging setup.

Emits one JSON object per line when `logging.format: json` in
configs/config.yaml, or a flat human-readable line with `console`.

Conventions for callers:
  - one line per meaningful event, not per function call
  - pass structured data via `extra={...}`, never f-string it into the message
  - name events dotted and resource-first: "terminology.search", "db.slow_query"
"""

import json
import logging
import sys
from typing import Any, ClassVar

from app.core.config import settings

# Attributes the stdlib puts on every LogRecord. Anything NOT in here came from
# a caller's extra={...} and gets merged into the emitted object.
_RESERVED_ATTRS = {
    "name",
    "msg",
    "args",
    "levelname",
    "levelno",
    "pathname",
    "filename",
    "module",
    "exc_info",
    "exc_text",
    "stack_info",
    "lineno",
    "funcName",
    "created",
    "msecs",
    "relativeCreated",
    "thread",
    "threadName",
    "processName",
    "process",
    "taskName",
}


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log_record: dict[str, Any] = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for key, value in record.__dict__.items():
            if key not in _RESERVED_ATTRS and key not in log_record:
                log_record[key] = value
        if record.exc_info:
            log_record["traceback"] = self.formatException(record.exc_info)
        return json.dumps(log_record, default=str)


class ConsoleFormatter(logging.Formatter):
    """Same data as the JSON formatter, laid out for eyes instead of an indexer."""

    # Set by logging.Formatter.format() itself — already rendered in `base`.
    _FORMATTER_SET: ClassVar[frozenset[str]] = frozenset({"message", "asctime"})

    def __init__(self) -> None:
        super().__init__("%(asctime)s %(levelname)-8s %(name)s | %(message)s")

    def format(self, record: logging.LogRecord) -> str:
        base = super().format(record)
        extras = {
            k: v
            for k, v in record.__dict__.items()
            if k not in _RESERVED_ATTRS and k not in self._FORMATTER_SET
        }
        suffix = " " + " ".join(f"{k}={v}" for k, v in extras.items()) if extras else ""
        line = f"{base}{suffix}"
        if record.exc_info:
            line += "\n" + self.formatException(record.exc_info)
        return line


def setup_logging() -> None:
    """Configure the root logger from settings.logging. Idempotent — replaces
    any previously installed handlers rather than stacking another one."""
    log_settings = settings.logging

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        ConsoleFormatter() if log_settings.format == "console" else JsonFormatter()
    )

    root = logging.getLogger()
    root.setLevel(log_settings.level)
    root.handlers.clear()
    root.addHandler(handler)

    # SQLAlchemy's engine logger is driven explicitly by logging.sql_echo
    # (see app.core.database), not inherited from the root level.
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
