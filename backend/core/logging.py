"""FormatAI centralized logging configuration."""

import logging
import sys


def setup_logging(level: int = logging.INFO) -> logging.Logger:
    """Configures structured console logging for the application."""
    logger = logging.getLogger("formatai")
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(
            fmt="%(asctime)s [%(levelname)s] [%(name)s]: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(level)
    return logger


logger = setup_logging()
