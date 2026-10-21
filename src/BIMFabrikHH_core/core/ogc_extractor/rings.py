"""Planar ring helpers for OGC Features / GeoJSON workflows (CRS → EPSG:25832)."""

from __future__ import annotations

from typing import Literal, Optional

from BIMFabrikHH_core.core.georeferencing.coordinate_transformer import CoordinateTransformer

from .geojson import PolygonRings, Ring

OgcGeometryCrs = Literal["EPSG:4326", "EPSG:25832"]

_WGS84_TO_UTM32: tuple[str, str] = ("EPSG:4326", "EPSG:25832")


def strip_closing_duplicate_xy(ring: Ring) -> Ring:
    """Drop duplicated closing position when first and last XY are equal."""
    if len(ring) >= 2 and ring[0] == ring[-1]:
        return ring[:-1]
    return ring


def ring_xy_to_epsg25832(
    ring: Ring,
    source_crs: OgcGeometryCrs,
) -> Ring:
    """Return ring vertices in EPSG:25832 (metres). ``source_crs`` is the CRS of ``ring`` XY."""
    ring = strip_closing_duplicate_xy(ring)
    if len(ring) < 3:
        return []
    if source_crs == "EPSG:25832":
        return list(ring)
    xs = [p[0] for p in ring]
    ys = [p[1] for p in ring]
    t = CoordinateTransformer(_WGS84_TO_UTM32[0], _WGS84_TO_UTM32[1])
    xe, yn = t.transform_xy_batch(xs, ys)
    return list(zip(xe, yn))


def polygon_rings_to_epsg25832(
    polygon: PolygonRings,
    source_crs: OgcGeometryCrs,
) -> Optional[PolygonRings]:
    """Return exterior and hole vertices in EPSG:25832 (metres).

    Holes with fewer than 3 distinct vertices are dropped. Returns ``None`` if the exterior has fewer than 3.
    """
    exterior_epsg25832 = ring_xy_to_epsg25832(polygon.exterior, source_crs)
    if len(exterior_epsg25832) < 3:
        return None

    holes_epsg25832 = [hole_xy for hole in polygon.holes if len(hole_xy := ring_xy_to_epsg25832(hole, source_crs)) >= 3]
    return PolygonRings(exterior=exterior_epsg25832, holes=holes_epsg25832)


__all__ = [
    "OgcGeometryCrs",
    "ring_xy_to_epsg25832",
    "polygon_rings_to_epsg25832",
    "strip_closing_duplicate_xy",
]
