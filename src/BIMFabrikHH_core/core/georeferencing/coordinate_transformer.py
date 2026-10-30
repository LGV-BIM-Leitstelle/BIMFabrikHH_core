"""Thin :mod:`pyproj` wrapper for CRS transformations.

Single class used by any app that needs to reproject coordinates between
two CRSs (e.g. UTM32N ↔ Gauß-Krüger Hamburg). Extracted from
``BIMFabrikHH_intern`` so intern/core/api can share one implementation.

:meth:`CoordinateTransformer.from_source_to_output` is the output step of the
apps: the data stays in ``source_epsg`` unless ``output_epsg`` is requested,
then the finished XY are transformed into it. :attr:`CoordinateTransformer.target_epsg`
is the CRS written to the IFC header.
"""

from __future__ import annotations

from functools import cached_property, lru_cache
from typing import Iterable, List, Optional, Sequence, Tuple, Union

from pyproj import CRS, Transformer

from BIMFabrikHH_core.config.logging_config import get_logger
from BIMFabrikHH_core.data_models.pydantic_georeferencing import (
    check_projected_epsg,
    check_source_epsg,
    check_vertical_epsg,
    compound_vertical_epsg,
    horizontal_crs,
)

logger = get_logger("coordinate_transformer")


@lru_cache(maxsize=32)
def _pyproj_transformer(source_crs: CRS, target_crs: CRS) -> Transformer:
    """Build the pyproj transformer once per CRS pair; the PROJ operation search takes about 130 ms."""
    return Transformer.from_crs(source_crs, target_crs, always_xy=True)


class CoordinateTransformer:
    """Reproject points between a source and target CRS.

    When source and target are the same CRS, coordinates pass through unchanged.
    """

    def __init__(
        self,
        source_crs: Union[str, CRS],
        target_crs: Union[str, CRS],
        vertical_epsg: Optional[int] = None,
    ) -> None:
        """Initialize with source and target CRS identifiers.

        Args:
            source_crs: EPSG / PROJ string (e.g. ``"EPSG:25832"``) or
                :class:`pyproj.CRS` for the input CRS.
            target_crs: Same for the output CRS.
            vertical_epsg: EPSG code of the height system of the data, ``None``
                if unknown; heights pass through untransformed.
        """
        self.source_crs = source_crs if isinstance(source_crs, CRS) else CRS(source_crs)
        self.target_crs = target_crs if isinstance(target_crs, CRS) else CRS(target_crs)
        self.vertical_epsg = vertical_epsg
        self.is_identity = self.source_crs == self.target_crs
        self.transformer = _pyproj_transformer(self.source_crs, self.target_crs)

    @classmethod
    def from_source_to_output(
        cls,
        source_epsg: Optional[int],
        output_epsg: Optional[int],
        vertical_epsg: Optional[int] = None,
    ) -> Optional["CoordinateTransformer"]:
        """Transformer from ``source_epsg`` to ``output_epsg`` (identity when ``output_epsg`` is ``None``).

        Returns ``None`` when no code is given: the coordinates have no known
        CRS, so they are written as they are and the IFC gets no georeferencing.
        A compound ``source_epsg`` (e.g. 5555) is transformed from its
        horizontal part. Heights pass through; their system is ``vertical_epsg``,
        else the vertical part of a compound ``source_epsg``, else unknown.

        Raises:
            ValueError: ``output_epsg`` or ``vertical_epsg`` without
                ``source_epsg``, or a code rejected by :func:`check_source_epsg`,
                :func:`check_projected_epsg` or :func:`check_vertical_epsg`.
        """
        if source_epsg is None:
            if output_epsg is not None:
                raise ValueError(f"output_epsg EPSG:{output_epsg} needs source_epsg to know what to transform from")
            if vertical_epsg is not None:
                raise ValueError(
                    f"vertical_epsg EPSG:{vertical_epsg} needs source_epsg: without it the IFC gets no coordinate system"
                )
            return None
        check_source_epsg(source_epsg, output_epsg)
        if output_epsg is not None:
            check_projected_epsg(output_epsg)
        if vertical_epsg is not None:
            check_vertical_epsg(vertical_epsg, source_epsg)
        return cls(
            horizontal_crs(source_epsg),
            horizontal_crs(source_epsg if output_epsg is None else output_epsg),
            vertical_epsg=vertical_epsg if vertical_epsg is not None else compound_vertical_epsg(source_epsg),
        )

    @cached_property
    def target_epsg(self) -> int:
        """EPSG code of the target CRS.

        Raises:
            ValueError: The target CRS has no EPSG code (custom PROJ / WKT definition).
        """
        epsg = self.target_crs.to_epsg()
        if epsg is None:
            raise ValueError(f"Target CRS {self.target_crs.name} has no EPSG code")
        return epsg

    def transform_point(self, x: float, y: float, z: float = 0.0) -> Tuple[float, float, float]:
        """Transform a single point; ``z`` passes through unchanged."""
        if self.is_identity:
            return float(x), float(y), float(z)
        x_t, y_t = self.transformer.transform(x, y)
        return float(x_t), float(y_t), float(z)

    def transform_xy_batch(
        self,
        xs: Iterable[float],
        ys: Iterable[float],
    ) -> Tuple[List[float], List[float]]:
        """Transform a batch of ``(x, y)`` pairs in one pyproj call."""
        if self.is_identity:
            return [float(v) for v in xs], [float(v) for v in ys]
        xs_t, ys_t = self.transformer.transform(list(xs), list(ys))
        return [float(v) for v in xs_t], [float(v) for v in ys_t]

    def transform_ring(self, ring: Sequence[Sequence[float]]) -> List[Tuple[float, float]]:
        """Transform the XY of each ring vertex; extra ordinates are dropped."""
        if not ring:
            return []
        xs, ys = self.transform_xy_batch([p[0] for p in ring], [p[1] for p in ring])
        return list(zip(xs, ys))


def warn_if_degree_coordinates(
    points: Iterable[Sequence[float]],
    transformer: Optional[CoordinateTransformer],
) -> None:
    """Log a warning when metre coordinates are expected but all XY look like longitude / latitude.

    ``points`` holds ``(x, y, ...)`` tuples and is read once, stopping at the
    first metre-like point. Degree values cannot be told apart from small metre
    values with certainty, so this only warns. Nothing is checked when the
    source CRS is geographic.
    """
    if transformer is not None and transformer.source_crs.is_geographic:
        return
    count = 0
    for point in points:
        if abs(point[0]) > 180.0 or abs(point[1]) > 90.0:
            return
        count += 1
    if count == 0:
        return
    source = "no source_epsg" if transformer is None else f"source CRS {transformer.source_crs.name}"
    logger.warning(
        "All %d coordinates lie within ±180 / ±90 and look like longitude / latitude, but %s expects metres; "
        "pass source_epsg=4326 and an output_epsg if they are WGS84",
        count,
        source,
    )
