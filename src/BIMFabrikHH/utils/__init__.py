"""
Utility functions for BIMFabrikHH.

This module contains utility functions for mathematical operations,
folder management, and other helper functions.
"""

from .folder_utils import check_folder_exists, get_src_dir
from .math_operations import MathTool

__all__ = [
    "MathTool",
    "get_src_dir",
    "check_folder_exists",
]
