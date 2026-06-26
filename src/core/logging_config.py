"""Application logging configuration."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

_LOG_FORMAT = "%(asctime)s %(levelname)s [%(name)s] %(message)s"

# uvicorn --reload uses watchfiles; its INFO "N change(s) detected" lines are
# written through the root logger and, with LOG_TO_FILE, append to app.log —
# which triggers another change event (feedback loop that fills the log file).
_QUIET_THIRD_PARTY_LOGGERS: tuple[str, ...] = ("watchfiles",)


def setup_logging(level: str = "INFO", *, log_file: Path | None = None) -> None:
    """Configure root logger for console and optional file output."""
    numeric = getattr(logging, level.upper(), logging.INFO)
    handlers: list[logging.Handler] = [logging.StreamHandler(sys.stderr)]

    if log_file is not None:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        handlers.append(logging.FileHandler(log_file, encoding="utf-8"))

    logging.basicConfig(
        level=numeric,
        format=_LOG_FORMAT,
        handlers=handlers,
        force=True,
    )

    for logger_name in _QUIET_THIRD_PARTY_LOGGERS:
        logging.getLogger(logger_name).setLevel(logging.WARNING)
