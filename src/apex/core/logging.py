from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from logging.config import dictConfig

from apex.core.config import Settings


class _JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        from apex.core.context import get_run_id

        payload = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        rid = get_run_id()
        if rid:
            payload["run_id"] = rid
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


class _RunIdFilter(logging.Filter):
    """Attach ``run_id`` from scheduler context for text log lines."""

    def filter(self, record: logging.LogRecord) -> bool:
        from apex.core.context import get_run_id

        rid = get_run_id()
        record.run_id = rid if rid else "-"
        return True


def configure_logging(settings: Settings) -> None:
    if settings.apex_log_json:
        dictConfig(
            {
                "version": 1,
                "disable_existing_loggers": False,
                "formatters": {
                    "json": {"()": "apex.core.logging._JsonFormatter"},
                },
                "handlers": {
                    "console": {
                        "class": "logging.StreamHandler",
                        "formatter": "json",
                        "filters": ["run_id"],
                    }
                },
                "filters": {
                    "run_id": {"()": "apex.core.logging._RunIdFilter"},
                },
                "root": {"level": settings.log_level.upper(), "handlers": ["console"]},
            }
        )
        return

    dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "default": {
                    "format": "%(asctime)s | %(levelname)s | %(run_id)s | %(name)s | %(message)s"
                }
            },
            "filters": {
                "run_id": {"()": "apex.core.logging._RunIdFilter"},
            },
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "formatter": "default",
                    "filters": ["run_id"],
                }
            },
            "root": {"level": settings.log_level.upper(), "handlers": ["console"]},
        }
    )


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
