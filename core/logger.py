"""
jarvis/core/logger.py
──────────────────────
Strukturlaşdırılmış logging — həm konsola, həm fayla yazır.
Bütün modullar bu logger-i import edir.
"""

import logging
import sys

from core.config import LOG_FILE, LOG_LEVEL


def _build_logger() -> logging.Logger:
    logger = logging.getLogger("JARVIS")
    if logger.handlers:  # ikinci dəfə çağırılmasın
        return logger

    logger.setLevel(LOG_LEVEL)

    fmt = logging.Formatter(
        fmt="[%(asctime)s] %(levelname)-8s %(name)s | %(message)s",
        datefmt="%H:%M:%S",
    )

    # Konsol handler
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.DEBUG)
    ch.setFormatter(fmt)
    logger.addHandler(ch)

    # Fayl handler (rotating-style manual)
    try:
        fh = logging.FileHandler(LOG_FILE, encoding="utf-8")
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(fmt)
        logger.addHandler(fh)
    except OSError as exc:
        logger.warning("Log faylı açıla bilmədi: %s", exc)

    return logger


log = _build_logger()
