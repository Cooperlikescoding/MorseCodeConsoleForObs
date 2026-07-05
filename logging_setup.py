"""Central logging setup: every diagnostic message the app would
otherwise print to stderr also lands in a log file, so the terminal's
`logs` command has something real to tail during event troubleshooting.
"""

from __future__ import annotations

import logging
from pathlib import Path

LOG_FILE = Path(__file__).resolve().parent / "morse_console.log"

_configured_loggers: set[str] = set()


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if name not in _configured_loggers:
        logger.setLevel(logging.INFO)
        file_handler = logging.FileHandler(LOG_FILE)
        file_handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
        logger.addHandler(file_handler)
        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(logging.Formatter("%(message)s"))
        logger.addHandler(stream_handler)
        logger.propagate = False
        _configured_loggers.add(name)
    return logger
