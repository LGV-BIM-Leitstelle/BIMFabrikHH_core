"""
OGC Extractor functionality for BIMFabrikHH.

This module contains OGC API integration and data extraction utilities
for retrieving geospatial data from Hamburg's OGC services, plus GeoJSON
FeatureCollection parsing and projected ring helpers for feature payloads.
"""

from .config import OGCExtractorSettings, ogc_extractor_settings
from .geojson import (
    ensure_feature_collection,
    feature_identifier,
    geojson_feature_properties,
    iter_geojson_features,
    parse_feature_linestring_path,
    parse_feature_multilinestring_paths,
    parse_feature_polygon_exterior_ring,
    positions_to_xy_ring,
)
from .ogc_values_extractor import extract_level_of_geometry, extract_project_info, extract_psets_basepoint
from .rings import OgcGeometryCrs, ring_xy_to_epsg25832, strip_closing_duplicate_xy

__all__ = [
    "OGCExtractorSettings",
    "ogc_extractor_settings",
    "extract_project_info",
    "extract_level_of_geometry",
    "extract_psets_basepoint",
    "OgcGeometryCrs",
    "ensure_feature_collection",
    "feature_identifier",
    "geojson_feature_properties",
    "iter_geojson_features",
    "parse_feature_linestring_path",
    "parse_feature_multilinestring_paths",
    "parse_feature_polygon_exterior_ring",
    "positions_to_xy_ring",
    "ring_xy_to_epsg25832",
    "strip_closing_duplicate_xy",
]
