"""
Logging configuration for Healthclaim Guardian.

Provides a standardized logging setup across all pipeline components.
"""

import logging
import sys
from typing import Optional


def setup_logger(
    name: str,
    level: int = logging.INFO,
    log_format: Optional[str] = None,
) -> logging.Logger:
    """
    Set up and return a logger with standardized formatting.

    Args:
        name: Logger name (typically __name__ of the module)
        level: Logging level (default: INFO)
        log_format: Custom format string (optional)

    Returns:
        Configured logger instance
    """
    if log_format is None:
        log_format = (
            "%(asctime)s | %(levelname)-8s | %(name)s | %(funcName)s:%(lineno)d "
            "| %(message)s"
        )

    formatter = logging.Formatter(log_format, datefmt="%Y-%m-%d %H:%M:%S")

    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Avoid adding duplicate handlers
    if not logger.handlers:
        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    return logger


def get_logger(name: str) -> logging.Logger:
    """Get a logger by name."""
    return logging.getLogger(name)


# Default logger for the package
default_logger = setup_logger("healthclaim_guardian")
