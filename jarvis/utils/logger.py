import logging
import sys
from pathlib import Path
from jarvis.utils.config import LOG_LEVEL, DATA_DIR

_initialized = False


def get_logger(name: str) -> logging.Logger:
    global _initialized
    if not _initialized:
        _setup()
    return logging.getLogger(name)


def _setup():
    global _initialized
    log_dir = DATA_DIR / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    level = getattr(logging, LOG_LEVEL.upper(), logging.INFO)
    fmt = logging.Formatter(
        "%(asctime)s  %(levelname)-8s  %(name)-20s  %(message)s",
        datefmt="%H:%M:%S",
    )

    root = logging.getLogger("jarvis")
    root.setLevel(level)

    if not root.handlers:
        ch = logging.StreamHandler(sys.stdout)
        ch.setFormatter(fmt)
        ch.setLevel(level)
        root.addHandler(ch)

        fh = logging.FileHandler(log_dir / "jarvis.log", encoding="utf-8")
        fh.setFormatter(fmt)
        fh.setLevel(logging.DEBUG)
        root.addHandler(fh)

    _initialized = True
