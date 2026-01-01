"""
Configuration package for BIMFabrikHH.

This module contains configuration utilities, path management, and logging setup.
"""

from .logging_colors import get_logger
from .paths import PathConfig

__all__ = [
    "PathConfig",
    "get_logger",
]
