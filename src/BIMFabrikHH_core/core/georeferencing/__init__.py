"""
Georeferencing functionality for BIMFabrikHH.

This module contains coordinate reference system transformations
and elevation extraction utilities.
"""

from .coordinate_transformer import CoordinateTransformer
from .coordinate_utils import convert_coordinate_to_float, convert_coordinates_batch
from .crs_transform import bbox_wgs84_to_epsg25832
from .extract_elevation import extract_elevation_df_from_geotiff, extract_elevation_point_from_geotiff

__all__ = [
    "CoordinateTransformer",
    "bbox_wgs84_to_epsg25832",
    "convert_coordinate_to_float",
    "convert_coordinates_batch",
    "extract_elevation_df_from_geotiff",
    "extract_elevation_point_from_geotiff",
]
