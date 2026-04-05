import logging
import logging.handlers
import os
import sys

from pythonjsonlogger.json import JsonFormatter

LOG_DIR = os.environ.get("LOG_DIR", "logs")
LOG_FILE = os.path.join(LOG_DIR, "app.log")
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO").upper()
# Keep last 10 MB across 5 rotated files
_MAX_BYTES = 10 * 1024 * 1024
_BACKUP_COUNT = 5

_FMT = "%(asctime)s %(levelname)s %(name)s %(message)s"


def setup_logging() -> None:
    os.makedirs(LOG_DIR, exist_ok=True)

    formatter = JsonFormatter(_FMT)

    # Stdout handler (JSON)
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(formatter)

    # Rotating file handler (JSON)
    file_handler = logging.handlers.RotatingFileHandler(
        LOG_FILE, maxBytes=_MAX_BYTES, backupCount=_BACKUP_COUNT
    )
    file_handler.setFormatter(formatter)

    root = logging.getLogger()
    root.setLevel(LOG_LEVEL)
    # Avoid adding duplicate handlers on repeated calls (e.g. tests)
    if not root.handlers:
        root.addHandler(stream_handler)
        root.addHandler(file_handler)

    # Silence noisy third-party loggers
    logging.getLogger("peewee").setLevel(logging.WARNING)
    logging.getLogger("werkzeug").setLevel(logging.WARNING)
