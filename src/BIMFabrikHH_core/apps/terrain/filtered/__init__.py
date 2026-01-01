"""
Filtered terrain modeling functionality for BIMFabrikHH.

This module contains filtered terrain processing functions for optimized
terrain model generation with filtering capabilities.
"""

from .app import create_terrain_ifc, process_terrain_folder_to_ifc

__all__ = [
    "process_terrain_folder_to_ifc",
    "create_terrain_ifc",
]
