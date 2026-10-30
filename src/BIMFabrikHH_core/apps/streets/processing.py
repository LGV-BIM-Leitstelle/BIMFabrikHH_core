"""Pure data-processing helpers for the streets app.

Turns ALKIS ``Nutzung`` traffic polygons (:class:`StreetRecord`) into draped 3D
meshes ready for IFC export:

1. take exterior rings in the DGM tile CRS (EPSG:25832, see
   :func:`transform_record_rings` / :func:`transformer_to_dgm`),
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

from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any, Iterable, List, Optional, Sequence, Tuple, Union

import numpy as np
from scipy.spatial import Delaunay

from BIMFabrikHH_core.config.logging_config import get_logger
from BIMFabrikHH_core.core.georeferencing import (
    DGM_TILE_EPSG,
    DGM_TILE_VERTICAL_EPSG,
    CoordinateTransformer,
    sample_elevations_for_points,
)
from BIMFabrikHH_core.core.ogc_extractor import transform_ring_xy
from BIMFabrikHH_core.data_models.streets import StreetRecord

logger = get_logger("streets_processing")

DEFAULT_VERTICAL_OFFSET_M: float = 0.2
DEFAULT_EDGE_SPACING_M: float = 5.0


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


def transformer_to_dgm(source_epsg: Optional[int]) -> Optional[CoordinateTransformer]:
    """Transformer from ``source_epsg`` into the DGM tile CRS, or ``None`` without a source.

    ``None`` means the coordinates are used as they are; the caller vouches
    they match the DGM.
    """
    if source_epsg is None:
        return None
    return CoordinateTransformer.from_source_to_output(source_epsg, DGM_TILE_EPSG)


def dgm_output_transformer(output_epsg: Optional[int], *, move_to_origin: bool = False) -> CoordinateTransformer:
    """Transformer from the DGM tile CRS (heights DHHN2016) into ``output_epsg``.

    Identity when ``output_epsg`` is ``None``. Its target is the CRS the IFC
    header, basepoint and LandXML are written in.

    Raises:
        ValueError: ``move_to_origin`` together with a different ``output_epsg``;
            the shifted vertices are local and cannot be transformed.
    """
    transformer = CoordinateTransformer.from_source_to_output(DGM_TILE_EPSG, output_epsg, DGM_TILE_VERTICAL_EPSG)
    if move_to_origin and not transformer.is_identity:
        raise ValueError(f"move_to_origin cannot be combined with output_epsg EPSG:{output_epsg}")
    return transformer


def transform_draped_streets(streets: Sequence[DrapedStreet], transformer: CoordinateTransformer) -> List[DrapedStreet]:
    """Copies of ``streets`` with vertex XY transformed in one batch; Z and faces unchanged."""
    if transformer.is_identity:
        return list(streets)
    points = [v for street in streets for v in street.vertices]
    xs, ys = transformer.transform_xy_batch([p[0] for p in points], [p[1] for p in points])
    moved = iter(zip(xs, ys, (p[2] for p in points)))
    return [replace(street, vertices=[next(moved) for _ in street.vertices]) for street in streets]


def transform_record_rings(records: Sequence[Any], transformer: Optional[CoordinateTransformer]) -> List[Any]:
    """Return copies of ``records`` with every ``rings`` entry transformed by ``transformer``.

    ``None`` or an identity transformer keep the records as they are.
    """
    if transformer is None or transformer.is_identity:
        return list(records)
    return [
        rec.model_copy(update={"rings": [transformer.transform_ring(ring) for ring in rec.rings]}) for rec in records
    ]


def open_rings_xy(rings: Sequence[Sequence[Tuple[float, float]]]) -> List[np.ndarray]:
    """Return each ring with at least 3 vertices as an open ``(N, 2)`` array."""
    return [np.asarray(xy, dtype=float) for ring in rings if (xy := transform_ring_xy(list(ring), None))]


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

    Ring XY must already be in the DGM tile CRS (see :func:`transform_record_rings`).
    Elevations for *all* vertices of *all* records are sampled together (one
    pass per tile) for efficiency, then meshed per record.
    """
    tif_list = list(tif_files)

    reprojected: List[List[np.ndarray]] = []
    flat_points: List[np.ndarray] = []
    for rec in records:
        rings_utm = [densify_ring(r, edge_spacing_m) for r in open_rings_xy(rec.rings)]
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
    "dgm_output_transformer",
    "drape_streets",
    "open_rings_xy",
    "transform_draped_streets",
    "transform_record_rings",
    "transformer_to_dgm",
]
