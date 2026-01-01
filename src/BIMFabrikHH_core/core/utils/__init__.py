"""
Utility functions for BIMFabrikHH.

This module contains utility functions for mathematical operations,
geometry operations, spatial operations, data processing, and other helper functions.
"""

from .data_utils import preprocess_elevation_data
from .geometry_utils import convert_to_indexed_geometry, extract_polygon_points, group3
from .math_operations import MathTool
from .spatial_utils import get_angle_from_2pts, is_building_in_bbox, parse_coordinates

__all__ = [
    "MathTool",
    "convert_to_indexed_geometry",
    "group3",
    "extract_polygon_points",
    "is_building_in_bbox",
    "get_angle_from_2pts",
    "parse_coordinates",
    "preprocess_elevation_data",
]
