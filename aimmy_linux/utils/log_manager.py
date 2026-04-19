"""
Logging module for Aimmy Linux.
Port of Other/LogManager.cs
"""

import logging
import sys
from datetime import datetime
from enum import Enum
from pathlib import Path

logger = logging.getLogger("aimmy")


class LogLevel(Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"


# Global reference to notification callback (set by UI layer)
_notify_callback = None


def set_notify_callback(callback):
    """Set the UI notification callback. Called by GUI on init.
    Signature: callback(message: str, duration_ms: int)
    """
    global _notify_callback
    _notify_callback = callback


def log(level: LogLevel, message: str, notify_user: bool = False, waiting_time: int = 4000):
    """Log a message and optionally notify the user via UI.

    Args:
        level: Log severity level
        message: The log message
        notify_user: If True, show a UI notification bar
        waiting_time: Duration of the notification in ms
    """
    # Console/file logging
    if level == LogLevel.INFO:
        logger.info(message)
    elif level == LogLevel.WARNING:
        logger.warning(message)
    elif level == LogLevel.ERROR:
        logger.error(message)

    # UI notification
    if notify_user and _notify_callback is not None:
        try:
            _notify_callback(message, waiting_time)
        except Exception:
            pass  # Don't let notification errors break the app

    # Debug file logging
    from utils.config_manager import config
    if config.toggle_state.get("Debug Mode", False):
        try:
            with open("debug.txt", "a") as f:
                f.write(f"[{datetime.now()}] [{level.value}]: {message}\n")
        except Exception:
            pass


def setup_logging(debug: bool = False):
    """Initialize the logging system."""
    level = logging.DEBUG if debug else logging.INFO
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter(
        "[%(asctime)s] [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S"
    ))
    logger.setLevel(level)
    logger.addHandler(handler)
