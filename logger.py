"""
===============================================================================
logger.py
Telegram Directory Bot v2.0
===============================================================================

Centralized logging configuration.

Features:
    • Console Logging
    • Rotating File Logging
    • Automatic Log Folder Creation
===============================================================================
"""

from __future__ import annotations

import logging
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path

from config import config


LOG_DIRECTORY = Path("logs")
LOG_DIRECTORY.mkdir(parents=True, exist_ok=True)

LOG_FILE = LOG_DIRECTORY / "bot.log"


def setup_logger(name: str = "TelegramDirectoryBot") -> logging.Logger:
    """
    Creates and returns a configured logger.

    Calling this function multiple times returns
    the same logger without duplicate handlers.
    """

    logger = logging.getLogger(name)

    if logger.handlers:
        return logger

    logger.setLevel(getattr(logging, config.LOG_LEVEL.upper(), logging.INFO))

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # -------------------------------------------------------------------------
    # Console Handler
    # -------------------------------------------------------------------------

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    # -------------------------------------------------------------------------
    # Daily Rotating File Handler
    # -------------------------------------------------------------------------

    file_handler = TimedRotatingFileHandler(
        filename=LOG_FILE,
        when="midnight",
        interval=1,
        backupCount=30,
        encoding="utf-8",
    )

    file_handler.setFormatter(formatter)

    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    logger.propagate = False

    return logger


logger = setup_logger()
