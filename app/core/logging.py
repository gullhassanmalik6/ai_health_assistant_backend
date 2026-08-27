"""Structured application logging. Health data and secrets must never be logged."""

from __future__ import annotations

import logging
import sys
from contextvars import ContextVar
from typing import Any

from app.core.config import settings

request_id_ctx: ContextVar[str] = ContextVar("request_id", default="-")

SENSITIVE_KEYS = {
    "password",
    "new_password",
    "confirm_password",
    "old_password",
    "id_token",
    "idtoken",
    "refresh_token",
    "authorization",
    "token",
    "access_token",
    "private_key",
    "firebase_private_key",
    "database_url",
    "api_key",
    "secret",
    "oob_code",
    "oobcode",
}


class SensitiveDataFilter(logging.Filter):
    """Drop or redact records that appear to contain secrets."""

    def filter(self, record: logging.LogRecord) -> bool:
        message = record.getMessage().lower()
        blocked = (
            "password",
            "bearer ",
            "private_key",
            "begin private",
            "id_token",
            "refresh_token",
        )
        if any(token in message for token in blocked):
            record.msg = "[redacted log record containing sensitive material]"
            record.args = ()
        return True


def setup_logging() -> None:
    level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter(
            fmt=(
                "%(asctime)s %(levelname)s request_id=%(request_id)s "
                "%(name)s %(message)s"
            )
        )
    )
    handler.addFilter(SensitiveDataFilter())

    root = logging.getLogger()
    root.handlers.clear()
    root.setLevel(level)
    root.addHandler(handler)

    logging.getLogger("uvicorn.access").handlers.clear()
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)


def extra_safe(**kwargs: Any) -> dict[str, Any]:
    """Build a logging extra dict with secrets stripped."""
    return {key: value for key, value in kwargs.items() if key.lower() not in SENSITIVE_KEYS}


old_factory = logging.getLogRecordFactory()


def _record_factory(*args: Any, **kwargs: Any) -> logging.LogRecord:
    record = old_factory(*args, **kwargs)
    record.request_id = request_id_ctx.get()
    return record


logging.setLogRecordFactory(_record_factory)
