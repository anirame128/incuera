"""Logging configuration for the application."""
import logging
import sys
from app.config import settings

# Configure root logger
logger = logging.getLogger("app")
logger.setLevel(logging.DEBUG if settings.environment == "development" else logging.INFO)

# Create console handler
handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.DEBUG if settings.environment == "development" else logging.INFO)

# Create formatter
formatter = logging.Formatter(
    "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
handler.setFormatter(formatter)

# Add handler to logger if not already added
if not logger.handlers:
    logger.addHandler(handler)

# Prevent duplicate logs
logger.propagate = False

__all__ = ["logger"]
