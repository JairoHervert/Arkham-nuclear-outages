import logging
import re
from logging.handlers import TimedRotatingFileHandler

from app.core.config import get_settings

"""
Centralized logging setup for the backend service.

Responsibilities:
- configure console and file logging
- rotate log files daily
- hide sensitive values such as API keys
- keep third-party logger noise under control
"""

class SensitiveDataFilter(logging.Filter):
    # Regex patterns used to redact API keys from URLs and JSON-like strings in log messages
    _patterns = (
        (re.compile(r"(api_key=)([^&\s]*)", re.IGNORECASE), r"\1***REDACTED***"),
        (re.compile(r"('api_key':\s*')([^']*)(')", re.IGNORECASE), r"\1***REDACTED***\3"),
        (re.compile(r'("api_key":\s*")([^"]*)(")', re.IGNORECASE), r'\1***REDACTED***\3'),
    )

    def filter(self, record: logging.LogRecord) -> bool:
        # Render the final log message first, then replace any sensitive values before it is emitted
        message = record.getMessage()

        for pattern, replacement in self._patterns:
            message = pattern.sub(replacement, message)

        record.msg = message
        record.args = ()
        return True


def setup_logging() -> None:
    settings = get_settings()

    # Resolve the configured log level dynamically and fall back to INFO if it's invalid
    level = getattr(logging, settings.log_level.upper(), logging.INFO)

    # Configure the root logger once, so all modules in the application inherit this configuration.
    root_logger = logging.getLogger()

    if root_logger.handlers:
        root_logger.handlers.clear()

    root_logger.setLevel(level)

    secret_filter = SensitiveDataFilter()

    # Console and file are kept concise for readability, but the file formatter includes filename and line number for easier debugging when needed.
    console_formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    )

    file_formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(filename)s:%(lineno)d | %(message)s"
    )

    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_handler.setFormatter(console_formatter)
    console_handler.addFilter(secret_filter)

    # Keep a rolling log history by rotating the active file at midnight
    # The current log file remains app.log, while older files are renamed
    # Retain logs for the configured number of days
    file_handler = TimedRotatingFileHandler(
        filename=settings.logs_dir / "app.log",
        when="midnight",
        interval=1,
        backupCount=settings.log_retention_days,
        encoding="utf-8",
    )
    file_handler.setLevel(level)
    file_handler.setFormatter(file_formatter)
    file_handler.addFilter(secret_filter)

    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)

    # Keep request-level visibility for httpx
    logging.getLogger("httpx").setLevel(logging.INFO)
    logging.getLogger("httpcore").setLevel(logging.WARNING)