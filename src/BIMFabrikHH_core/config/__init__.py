"""
Configuration package for BIMFabrikHH.

This module contains configuration utilities, path management, and logging setup.
"""

from .logging_config import get_logger, setup_logging
from .paths import PathConfig

__all__ = [
    "PathConfig",
    "get_logger",
    "setup_logging",
]
