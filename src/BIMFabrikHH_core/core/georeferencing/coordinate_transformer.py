"""Thin :mod:`pyproj` wrapper for CRS transformations.

Single class used by any app that needs to reproject coordinates between
two CRSs (e.g. UTM32N ↔ Gauß-Krüger Hamburg). Extracted from
``BIMFabrikHH_intern`` so intern/core/api can share one implementation.
"""

from __future__ import annotations

from typing import Iterable, List, Tuple

from pyproj import CRS, Transformer


class CoordinateTransformer:
    """Reproject points between a source and target CRS."""

    def __init__(self, source_crs: str, target_crs: str) -> None:
        """Initialize with source and target CRS identifiers.

        Args:
            source_crs: EPSG / PROJ string for the input CRS (e.g.
                ``"EPSG:25832"``).
            target_crs: EPSG / PROJ string for the output CRS.
        """
        self.source_crs = CRS(source_crs)
        self.target_crs = CRS(target_crs)
        self.transformer = Transformer.from_crs(self.source_crs, self.target_crs, always_xy=True)

    def transform_point(self, x: float, y: float, z: float = 0.0) -> Tuple[float, float, float]:
        """Transform a single point; ``z`` passes through unchanged."""
        x_t, y_t = self.transformer.transform(x, y)
        return float(x_t), float(y_t), float(z)

    def transform_xy_batch(
        self,
        xs: Iterable[float],
        ys: Iterable[float],
    ) -> Tuple[List[float], List[float]]:
        """Transform a batch of ``(x, y)`` pairs in one pyproj call."""
        xs_t, ys_t = self.transformer.transform(list(xs), list(ys))
        return [float(v) for v in xs_t], [float(v) for v in ys_t]
