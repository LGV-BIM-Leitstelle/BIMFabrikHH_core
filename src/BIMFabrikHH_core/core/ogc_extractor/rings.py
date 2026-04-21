"""Planar ring helpers for OGC Features / GeoJSON workflows (CRS → EPSG:25832)."""

from __future__ import annotations

from typing import List, Literal, Tuple

from BIMFabrikHH_core.core.georeferencing.coordinate_transformer import CoordinateTransformer

OgcGeometryCrs = Literal["EPSG:4326", "EPSG:25832"]

_WGS84_TO_UTM32: tuple[str, str] = ("EPSG:4326", "EPSG:25832")


def strip_closing_duplicate_xy(ring: List[Tuple[float, float]]) -> List[Tuple[float, float]]:
    """Drop duplicated closing position when first and last XY are equal."""
    if len(ring) >= 2 and ring[0] == ring[-1]:
        return ring[:-1]
    return ring


def ring_xy_to_epsg25832(
    ring: List[Tuple[float, float]],
    source_crs: OgcGeometryCrs,
) -> List[Tuple[float, float]]:
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


__all__ = [
    "OgcGeometryCrs",
    "ring_xy_to_epsg25832",
    "strip_closing_duplicate_xy",
]
