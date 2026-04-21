"""Coordinate conversion helpers.

Pure, float-safe utilities for turning raw coordinate values (often strings
or mixed-type scalars coming back from APIs / Excel / CAD attributes) into
``float`` values suitable for downstream CRS work.

These helpers used to live in ``BIMFabrikHH_intern`` (cadaster app). They
are generic and not vegetation-specific, so they live in core.
"""

from __future__ import annotations

import logging
import math
from typing import Any, Iterable, List, Mapping, Tuple

import pandas as pd

logger = logging.getLogger(__name__)


def convert_coordinate_to_float(coord: Any) -> float:
    """Convert a single coordinate value to ``float``.

    Accepts ``str``, ``int``, ``float``, ``None`` and ``NaN`` inputs.

    Args:
        coord: Raw coordinate value.

    Returns:
        The coordinate as a finite ``float``.

    Raises:
        ValueError: If ``coord`` is ``None``/``NaN``/``inf`` or cannot be
            parsed as a number.
    """
    if coord is None or pd.isna(coord):
        raise ValueError(f"Cannot convert None or NaN coordinate: {coord!r}")
    try:
        value = float(coord)
    except (TypeError, ValueError) as e:
        raise ValueError(f"Cannot convert coordinate to float: {coord!r} (type={type(coord).__name__})") from e
    if math.isinf(value) or math.isnan(value):
        raise ValueError(f"Coordinate is infinite or NaN: {coord!r}")
    return value


def convert_coordinates_batch(
    rows: Iterable[Mapping[str, Any]],
    *,
    x_key: str = "Easting",
    y_key: str = "Northing",
    name_key: str = "name",
) -> Tuple[List[float], List[float], List[int]]:
    """Convert a batch of ``(x, y)`` coordinates from mapping rows.

    For rows whose coordinates fail conversion, ``float('nan')`` is written
    at the matching position in ``xs``/``ys`` and the row index is appended
    to ``invalid_indices`` so callers can filter them out before a bulk
    transform.

    Args:
        rows: Iterable of mappings containing at least ``x_key`` and
            ``y_key``.
        x_key: Mapping key for the x/easting coordinate.
        y_key: Mapping key for the y/northing coordinate.
        name_key: Mapping key used only to label warnings; falls back to
            the row index when absent.

    Returns:
        ``(xs, ys, invalid_indices)`` with ``len(xs) == len(ys) == len(rows)``.
    """
    xs: List[float] = []
    ys: List[float] = []
    invalid_indices: List[int] = []

    for idx, row in enumerate(rows):
        try:
            xs.append(convert_coordinate_to_float(row.get(x_key)))
            ys.append(convert_coordinate_to_float(row.get(y_key)))
        except ValueError as e:
            label = row.get(name_key, idx)
            logger.warning("Row %s has invalid coordinates: %s", label, e)
            invalid_indices.append(idx)
            xs.append(float("nan"))
            ys.append(float("nan"))

    if invalid_indices:
        logger.warning(
            "Found %d row(s) with invalid coordinates out of %d.",
            len(invalid_indices),
            len(xs),
        )

    return xs, ys, invalid_indices
