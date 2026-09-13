"""Pure data-processing helpers for the streets app.

Turns ALKIS ``Nutzung`` traffic polygons (:class:`StreetRecord`) into draped 3D
meshes ready for IFC export:

1. reproject exterior rings to EPSG:25832 (if needed),
2. densify long edges so the surface can follow the DGM,
3. sample ground elevation for every vertex from one or more DGM GeoTIFFs
   (reusing the terrain app's raster helpers), and
4. Delaunay-triangulate each ring in XY, keep triangles whose centroid lies
   inside the polygon, and lift them to sampled Z.

No ``ifcopenshell`` / ``ifcfactory`` calls live here; all IFC-writing logic
lives in ``generic/app.py`` (same split as the terrain app).

Public entry point:
    :func:`drape_streets` — records + DGM tiles → ``list[DrapedStreet]``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, List, Optional, Sequence, Tuple, Union

import numpy as np
from scipy.spatial import Delaunay

from BIMFabrikHH_core.core.georeferencing import sample_elevations_for_points
from BIMFabrikHH_core.config.logging_config import get_logger
from BIMFabrikHH_core.core.georeferencing.coordinate_transformer import CoordinateTransformer
from BIMFabrikHH_core.core.ogc_extractor import strip_closing_duplicate_xy
from BIMFabrikHH_core.data_models.streets import StreetRecord

logger = get_logger("streets_processing")

DEFAULT_VERTICAL_OFFSET_M: float = 0.2
DEFAULT_EDGE_SPACING_M: float = 5.0

_WGS84 = "EPSG:4326"
_UTM32 = "EPSG:25832"


@dataclass
class DrapedStreet:
    """A single Nutzung surface draped onto the DGM, ready to become one IFC element."""

    record: StreetRecord
    vertices: List[Tuple[float, float, float]] = field(default_factory=list)
    faces: List[List[int]] = field(default_factory=list)

    def is_empty(self) -> bool:
        return len(self.vertices) < 3 or len(self.faces) < 1


# ---------------------------------------------------------------------------
# CRS handling
# ---------------------------------------------------------------------------


def rings_to_epsg25832(
    rings: Sequence[Sequence[Tuple[float, float]]],
    source_crs: str,
) -> List[np.ndarray]:
    """Return each exterior ring as an open ``(N, 2)`` array in EPSG:25832 metres."""
    cleaned = [strip_closing_duplicate_xy(list(ring)) for ring in rings]
    cleaned = [r for r in cleaned if len(r) >= 3]

    if source_crs == _UTM32:
        return [np.asarray(r, dtype=float) for r in cleaned]

    transformer = CoordinateTransformer(_WGS84, _UTM32)
    out: List[np.ndarray] = []
    for ring in cleaned:
        xs = [pt[0] for pt in ring]
        ys = [pt[1] for pt in ring]
        xe, yn = transformer.transform_xy_batch(xs, ys)
        out.append(np.column_stack((xe, yn)))
    return out


# ---------------------------------------------------------------------------
# Polygon meshing
# ---------------------------------------------------------------------------


def densify_ring(ring_xy: np.ndarray, spacing: float) -> np.ndarray:
    """Insert vertices along edges longer than ``spacing`` metres."""
    if len(ring_xy) < 3 or spacing <= 0:
        return ring_xy
    out: List[np.ndarray] = []
    n = len(ring_xy)
    for i in range(n):
        a = ring_xy[i]
        b = ring_xy[(i + 1) % n]
        out.append(a)
        dist = float(np.hypot(b[0] - a[0], b[1] - a[1]))
        steps = int(dist // spacing)
        for k in range(1, steps):
            t = k / steps
            out.append(a * (1.0 - t) + b * t)
    return np.asarray(out, dtype=float)


def _point_in_ring(x: float, y: float, ring_xy: np.ndarray) -> bool:
    """Ray-cast test; ``ring_xy`` is an open exterior ring."""
    inside = False
    n = len(ring_xy)
    j = n - 1
    for i in range(n):
        xi, yi = ring_xy[i]
        xj, yj = ring_xy[j]
        intersects = (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / ((yj - yi) or 1e-12) + xi
        if intersects:
            inside = not inside
        j = i
    return inside


def build_polygon_mesh(
    ring_xy: np.ndarray,
    ring_z: np.ndarray,
    *,
    vertical_offset: float,
) -> Tuple[List[Tuple[float, float, float]], List[List[int]]]:
    """Delaunay-triangulate a draped ring and keep interior triangles."""
    if len(ring_xy) < 3:
        return [], []
    try:
        tri = Delaunay(ring_xy)
    except Exception as exc:
        logger.warning("Delaunay failed for ring with %d vertices: %s", len(ring_xy), exc)
        return [], []

    faces: List[List[int]] = []
    for simplex in tri.simplices:
        cx = float(ring_xy[simplex, 0].mean())
        cy = float(ring_xy[simplex, 1].mean())
        if _point_in_ring(cx, cy, ring_xy):
            faces.append([int(simplex[0]), int(simplex[1]), int(simplex[2])])
    if not faces:
        return [], []

    z = ring_z + vertical_offset
    vertices = [(float(x), float(y), float(zi)) for (x, y), zi in zip(ring_xy, z)]
    return vertices, faces


def _combine_rings_mesh(
    rings_xy: Sequence[np.ndarray],
    z_per_ring: Sequence[np.ndarray],
    *,
    vertical_offset: float,
) -> Tuple[List[Tuple[float, float, float]], List[List[int]]]:
    all_vertices: List[Tuple[float, float, float]] = []
    all_faces: List[List[int]] = []
    for ring_xy, ring_z in zip(rings_xy, z_per_ring):
        verts, faces = build_polygon_mesh(ring_xy, ring_z, vertical_offset=vertical_offset)
        if not verts or not faces:
            continue
        offset = len(all_vertices)
        all_vertices.extend(verts)
        all_faces.extend([[a + offset, b + offset, c + offset] for a, b, c in faces])
    return all_vertices, all_faces


# ---------------------------------------------------------------------------
# Top-level orchestrator
# ---------------------------------------------------------------------------


def drape_streets(
    records: Sequence[StreetRecord],
    tif_files: Iterable[Union[str, Path]],
    *,
    folder_path: Optional[Union[str, Path]] = None,
    vertical_offset_m: float = DEFAULT_VERTICAL_OFFSET_M,
    edge_spacing_m: float = DEFAULT_EDGE_SPACING_M,
    default_elevation: float = 0.0,
) -> List[DrapedStreet]:
    """Drape every Nutzung record onto the DGM and build surface meshes.

    Elevations for *all* vertices of *all* records are sampled together (one
    pass per tile) for efficiency, then meshed per record.
    """
    tif_list = list(tif_files)

    reprojected: List[List[np.ndarray]] = []
    flat_points: List[np.ndarray] = []
    for rec in records:
        rings_utm = [densify_ring(r, edge_spacing_m) for r in rings_to_epsg25832(rec.rings, rec.geometry_crs)]
        rings_utm = [r for r in rings_utm if len(r) >= 3]
        reprojected.append(rings_utm)
        for r in rings_utm:
            flat_points.append(r)

    if not flat_points:
        return [DrapedStreet(record=rec) for rec in records]

    stacked = np.vstack(flat_points)
    all_z = sample_elevations_for_points(
        stacked,
        tif_list,
        folder_path=folder_path,
        default_elevation=default_elevation,
    )

    cursor = 0
    draped: List[DrapedStreet] = []
    for rec, rings_utm in zip(records, reprojected):
        z_per_ring: List[np.ndarray] = []
        for r in rings_utm:
            n = len(r)
            z_per_ring.append(all_z[cursor : cursor + n])
            cursor += n
        vertices, faces = _combine_rings_mesh(
            rings_utm,
            z_per_ring,
            vertical_offset=vertical_offset_m,
        )
        draped.append(DrapedStreet(record=rec, vertices=vertices, faces=faces))

    return draped


__all__ = [
    "DEFAULT_EDGE_SPACING_M",
    "DEFAULT_VERTICAL_OFFSET_M",
    "DrapedStreet",
    "build_polygon_mesh",
    "densify_ring",
    "drape_streets",
    "rings_to_epsg25832",
]
