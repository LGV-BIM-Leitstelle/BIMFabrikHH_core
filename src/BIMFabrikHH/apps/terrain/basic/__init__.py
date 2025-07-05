"""
Digital Terrain Model (DGM) application for BIMFabrikHH.

This module contains functionality for processing GeoTIFF files and
converting them to IFC terrain models.
"""

from .app import create_combined_terrain_ifc, process_terrain_folder_to_ifc

__all__ = [
    "process_terrain_folder_to_ifc",
    "create_combined_terrain_ifc",
]
