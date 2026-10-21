"""Planar ring helpers for OGC Features / GeoJSON workflows (CRS → EPSG:25832)."""

from __future__ import annotations

from typing import List, Literal, Tuple

from BIMFabrikHH_core.core.georeferencing.coordinate_transformer import \
    CoordinateTransformer

from .geojson import Polygon, Ring

OgcGeometryCrs = Literal["EPSG:4326", "EPSG:25832"]

_WGS84_TO_UTM32: tuple[str, str] = ("EPSG:4326", "EPSG:25832")


def strip_closing_duplicate_xy(ring: Ring) -> Ring:
    """Drop duplicated closing position when first and last XY are equal."""
    if len(ring) >= 2 and ring[0] == ring[-1]:
        return ring[:-1]
    return ring


def point_xy_to_epsg25832(
    point: Tuple[float, float],
    source_crs: OgcGeometryCrs,
) -> Tuple[float, float]:
    """Return vertex in EPSG:25832 (metres). ``source_crs`` is the CRS of ``point`` XY."""
    if source_crs == "EPSG:25832":
        return point
    x = point[0]
    y = point[1]
    t = CoordinateTransformer(_WGS84_TO_UTM32[0], _WGS84_TO_UTM32[1])
    xe, yn, _ = t.transform_point(x, y)
    return (xe, yn)


def line_xy_to_epsg25832(
    line: Ring,
    source_crs: OgcGeometryCrs,
) -> Ring:
    """Return line vertices in EPSG:25832 (metres). ``source_crs`` is the CRS of ``line`` XY."""
    line = strip_closing_duplicate_xy(line)
    if len(line) < 3:
        return []
    if source_crs == "EPSG:25832":
        return list(line)
    xs = [p[0] for p in line]
    ys = [p[1] for p in line]
    t = CoordinateTransformer(_WGS84_TO_UTM32[0], _WGS84_TO_UTM32[1])
    xe, yn = t.transform_xy_batch(xs, ys)
    return list(zip(xe, yn))


def polygon_rings_to_epsg25832(
    polygon: Polygon,
    source_crs: OgcGeometryCrs,
) -> Polygon | None:
    """Return ring vertices in EPSG:25832 (metres). Return ``None`` if the exterior ring is empty or has ``len<3``."""
    exterior_epsg25832 = line_xy_to_epsg25832(polygon.exterior, source_crs)
    if not exterior_epsg25832 or len(exterior_epsg25832) < 3:
        return None

    holes_epsg25832 = [
        line_xy_to_epsg25832(hole, source_crs) for hole in polygon.holes if hole
    ]  # filter out [] entries

    polygon_epsg25832 = Polygon(exterior=exterior_epsg25832, holes=holes_epsg25832)
    return polygon_epsg25832


__all__ = [
    "OgcGeometryCrs",
    "line_xy_to_epsg25832",
    "strip_closing_duplicate_xy",
]
