import logging
import re
from logging.handlers import TimedRotatingFileHandler

from app.core.config import get_settings

class SensitiveDataFilter(logging.Filter):

    _patterns = (
        (re.compile(r"(api_key=)([^&\s]*)", re.IGNORECASE), r"\1***REDACTED***"),
        (re.compile(r"('api_key':\s*')([^']*)(')", re.IGNORECASE), r"\1***REDACTED***\3"),
        (re.compile(r'("api_key":\s*")([^"]*)(")', re.IGNORECASE), r'\1***REDACTED***\3'),
    )

    def filter(self, record: logging.LogRecord) -> bool:
        message = record.getMessage()

        for pattern, replacement in self._patterns:
            message = pattern.sub(replacement, message)

        record.msg = message
        record.args = ()
        return True


def setup_logging() -> None:
    settings = get_settings()

    level = getattr(logging, settings.log_level.upper(), logging.INFO)

    root_logger = logging.getLogger()

    if root_logger.handlers:
        root_logger.handlers.clear()

    root_logger.setLevel(level)

    secret_filter = SensitiveDataFilter()

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

    logging.getLogger("httpx").setLevel(logging.INFO)
    logging.getLogger("httpcore").setLevel(logging.WARNING)