"""
Georeferencing functionality for BIMFabrikHH.

This module contains coordinate reference system transformations
and elevation extraction utilities.
"""

from .coordinate_transformer import CoordinateTransformer, warn_if_degree_coordinates
from .coordinate_utils import convert_coordinate_to_float, convert_coordinates_batch
from .crs_transform import bbox_request_params_to_epsg25832, bbox_wgs84_to_epsg25832
from .extract_elevation import (
    DGM_TILE_EPSG,
    DGM_TILE_VERTICAL_EPSG,
    download_to_memory,
    invalid_z,
    is_url,
    open_geotiff,
    sample_elevations_for_points,
    sample_elevations_from_raster,
)

__all__ = [
    "CoordinateTransformer",
    "DGM_TILE_EPSG",
    "DGM_TILE_VERTICAL_EPSG",
    "bbox_request_params_to_epsg25832",
    "bbox_wgs84_to_epsg25832",
    "convert_coordinate_to_float",
    "convert_coordinates_batch",
    "download_to_memory",
    "invalid_z",
    "is_url",
    "open_geotiff",
    "sample_elevations_for_points",
    "sample_elevations_from_raster",
    "warn_if_degree_coordinates",
]
