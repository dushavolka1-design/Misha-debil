from __future__ import annotations

import logging
import re
from typing import Any

_SECRET_KEYS = re.compile(
    r"(password|secret|token|authorization|api[_-]?key|session|cookie|dsn|database_url)",
    re.IGNORECASE,
)


class RedactingFilter(logging.Filter):
    """Drop or mask likely secrets and request bodies from log records."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.msg = _redact(str(record.msg))
        if record.args:
            if isinstance(record.args, dict):
                record.args = {k: _redact_value(k, v) for k, v in record.args.items()}
            elif isinstance(record.args, tuple):
                # Preserve non-str args (e.g. httpx status_code for "%d") — only redact strings.
                record.args = tuple(_redact(a) if isinstance(a, str) else a for a in record.args)
        return True


def _redact_value(key: str, value: Any) -> Any:
    if _SECRET_KEYS.search(key):
        return "[REDACTED]"
    return _redact(str(value)) if isinstance(value, str) else value


def _redact(text: str) -> str:
    text = re.sub(r"(?i)(Bearer\s+)[A-Za-z0-9\-._~+/]+=*", r"\1[REDACTED]", text)
    text = re.sub(
        r"(?i)(password|secret|token|api_key|session_secret)\s*[:=]\s*\S+",
        r"\1=[REDACTED]",
        text,
    )
    return text


def configure_logging(level: str = "INFO") -> None:
    root = logging.getLogger()
    root.handlers.clear()
    handler = logging.StreamHandler()
    handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s"),
    )
    handler.addFilter(RedactingFilter())
    root.addHandler(handler)
    root.setLevel(level.upper())
    # Never attach request body loggers by default
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
