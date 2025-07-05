"""
Georeferencing functionality for BIMFabrikHH.

This module contains coordinate reference system transformations
and elevation extraction utilities.
"""

from .crs_transform import bbox_wgs84_to_epsg25832
from .extract_elevation import extract_elevation_df_from_geotiff, extract_elevation_point_from_geotiff

__all__ = [
    "bbox_wgs84_to_epsg25832",
    "extract_elevation_df_from_geotiff",
    "extract_elevation_point_from_geotiff",
]
