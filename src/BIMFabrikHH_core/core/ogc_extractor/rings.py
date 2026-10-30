"""Planar ring helpers for OGC Features / GeoJSON workflows."""

from __future__ import annotations

from typing import Optional

from BIMFabrikHH_core.core.georeferencing.coordinate_transformer import CoordinateTransformer

from .geojson import PolygonRings, Ring


def strip_closing_duplicate_xy(ring: Ring) -> Ring:
    """Drop duplicated closing position when first and last XY are equal."""
    if len(ring) >= 2 and ring[0] == ring[-1]:
        return ring[:-1]
    return ring


def transform_ring_xy(ring: Ring, transformer: Optional[CoordinateTransformer]) -> Ring:
    """Return the open ring XY transformed by ``transformer``, or ``[]`` below 3 vertices.

    ``None`` keeps the coordinates as they are.
    """
    ring = strip_closing_duplicate_xy(ring)
    if len(ring) < 3:
        return []
    if transformer is None:
        return list(ring)
    return transformer.transform_ring(ring)


def transform_polygon_rings(
    polygon: PolygonRings,
    transformer: Optional[CoordinateTransformer],
) -> Optional[PolygonRings]:
    """Return exterior and holes transformed by ``transformer`` (``None`` keeps them).

    Holes with fewer than 3 distinct vertices are dropped. Returns ``None`` if the exterior has fewer than 3.
    """
    exterior = transform_ring_xy(polygon.exterior, transformer)
    if len(exterior) < 3:
        return None

    holes = [hole_xy for hole in polygon.holes if len(hole_xy := transform_ring_xy(hole, transformer)) >= 3]
    return PolygonRings(exterior=exterior, holes=holes)


__all__ = [
    "strip_closing_duplicate_xy",
    "transform_polygon_rings",
    "transform_ring_xy",
]
