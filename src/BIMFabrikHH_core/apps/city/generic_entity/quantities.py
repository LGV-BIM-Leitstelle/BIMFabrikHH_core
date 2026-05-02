"""Geometric quantity computation for CityGML boundary polygon rings.

All quantities are computed directly from the 3D ring coordinates — no IFC
geometry engine is involved. This gives reliable results for thin-shell
`IfcFacetedBrep` geometry where `ifc5d` returns 0 or bogus values.

Typical usage:

```python
from BIMFabrikHH_core.apps.city.generic_entity.quantities import (
    compute_boundary_quantities,
)

qty = compute_boundary_quantities(boundary_polygon)
print(qty.gross_area_m2, qty.slope_deg)
```
"""

from __future__ import annotations

import math
from typing import List, Optional, Sequence

import numpy as np
from pydantic import BaseModel, Field

from BIMFabrikHH_core.apps.city.generic_entity.models import BoundaryPolygon, Point3
from BIMFabrikHH_core.data_models.pydantic_psets_city_model import Pset_BIMFabrikHH_Quantities


# ---------------------------------------------------------------------------
# Result model
# ---------------------------------------------------------------------------


class FaceQuantities(BaseModel):
    """Geometric quantities for one boundary polygon."""

    surface_type: str = Field(description="RoofSurface, WallSurface, …")

    gross_area_m2: float = Field(
        description="True 3-D surface area of the polygon ring [m²].",
        ge=0.0,
    )
    perimeter_m: float = Field(
        description="Total ring perimeter [m].",
        ge=0.0,
    )
    slope_deg: float = Field(
        description=(
            "Inclination angle from horizontal [°].  "
            "0 ° = flat, 90 ° = vertical wall.  "
            "Computed from the polygon's face normal."
        ),
        ge=0.0,
        le=90.0,
    )


# ---------------------------------------------------------------------------
# Low-level geometry helpers (pure NumPy, no extra dependencies)
# ---------------------------------------------------------------------------


def _ring_to_array(ring: Sequence[Point3]) -> np.ndarray:
    """Return an (N, 3) float64 array from a sequence of (x, y, z) tuples."""
    return np.array(ring, dtype=np.float64)


def polygon_gross_area(ring: Sequence[Point3]) -> float:
    """True 3-D surface area of a planar polygon ring [m²].

    Uses the cross-product (vector area) method which handles arbitrary
    3-D orientations — flat, inclined, or vertical.

    Args:
        ring: Ordered sequence of `(x, y, z)` vertices. The ring may or
            may not repeat the first vertex at the end; both cases are handled.

    Returns:
        Area in the same length unit as the input coordinates (metres for
        EPSG:25833 / UTM).
    """
    pts = _ring_to_array(ring)
    # Drop duplicate closing vertex if present
    if np.allclose(pts[0], pts[-1]):
        pts = pts[:-1]
    n = len(pts)
    if n < 3:
        return 0.0

    # Fan triangulation from vertex 0; area = 0.5 * |Σ cross(v_i, v_{i+1})|
    v0 = pts[0]
    cross_sum = np.zeros(3, dtype=np.float64)
    for i in range(1, n - 1):
        cross_sum += np.cross(pts[i] - v0, pts[i + 1] - v0)
    return float(0.5 * np.linalg.norm(cross_sum))


def polygon_perimeter(ring: Sequence[Point3]) -> float:
    """Total 3-D perimeter of the ring [m].

    Args:
        ring: Ordered sequence of `(x, y, z)` vertices. If the ring does
            not close (first ≠ last), the closing edge is added automatically.

    Returns:
        Perimeter [m].
    """
    pts = _ring_to_array(ring)
    if np.allclose(pts[0], pts[-1]):
        pts = pts[:-1]
    if len(pts) < 2:
        return 0.0

    edges = np.roll(pts, -1, axis=0) - pts
    return float(np.sum(np.linalg.norm(edges, axis=1)))


def polygon_slope_deg(ring: Sequence[Point3]) -> float:
    """Inclination angle from horizontal [°], derived from the face normal.

    `0°` = perfectly flat (horizontal), `90°` = vertical wall.

    Args:
        ring: Ordered sequence of `(x, y, z)` vertices.

    Returns:
        Slope in degrees `[0, 90]`. Returns `0.0` if the ring is
        degenerate (< 3 non-collinear points).
    """
    pts = _ring_to_array(ring)
    if np.allclose(pts[0], pts[-1]):
        pts = pts[:-1]
    if len(pts) < 3:
        return 0.0

    # Compute the face normal via cross product of first two non-parallel edges
    v0 = pts[0]
    normal = np.zeros(3, dtype=np.float64)
    for i in range(1, len(pts) - 1):
        candidate = np.cross(pts[i] - v0, pts[i + 1] - v0)
        if np.linalg.norm(candidate) > 1e-9:
            normal = candidate
            break

    norm_len = np.linalg.norm(normal)
    if norm_len < 1e-9:
        return 0.0

    # Angle between normal and vertical axis (0, 0, 1)
    cos_theta = abs(float(normal[2])) / norm_len
    # Clamp for floating-point safety
    cos_theta = min(1.0, max(0.0, cos_theta))
    # angle between normal and vertical = angle between surface and horizontal
    return float(math.degrees(math.acos(cos_theta)))


# ---------------------------------------------------------------------------
# High-level convenience
# ---------------------------------------------------------------------------


def compute_boundary_quantities(boundary: BoundaryPolygon) -> FaceQuantities:
    """Compute all geometric quantities for one :class:`BoundaryPolygon`.

    Args:
        boundary: A parsed CityGML boundary surface with its ring coordinates.

    Returns:
        :class:`FaceQuantities` with area, projected area, perimeter and slope.
    """
    ring = boundary.ring
    return FaceQuantities(
        surface_type=boundary.surface_type,
        gross_area_m2=polygon_gross_area(ring),
        perimeter_m=polygon_perimeter(ring),
        slope_deg=polygon_slope_deg(ring),
    )


def face_quantities_to_pset(q: FaceQuantities) -> Pset_BIMFabrikHH_Quantities:
    """Convert a `FaceQuantities` result into an IFC property set instance.

    Args:
        q: Computed quantities for one boundary polygon.

    Returns:
        `Pset_BIMFabrikHH_Quantities` ready to pass to `BIMFactoryElement(psets=[…])`.
    """
    return Pset_BIMFabrikHH_Quantities(
        GrossArea=round(q.gross_area_m2, 4),
        Perimeter=round(q.perimeter_m, 4),
        Tilt=round(q.slope_deg, 2),
        SurfaceType=q.surface_type,
    )


__all__ = [
    "FaceQuantities",
    "Pset_BIMFabrikHH_Quantities",
    "compute_boundary_quantities",
    "compute_building_quantities",
    "face_quantities_to_pset",
    "polygon_gross_area",
    "polygon_perimeter",
    "polygon_slope_deg",
]
