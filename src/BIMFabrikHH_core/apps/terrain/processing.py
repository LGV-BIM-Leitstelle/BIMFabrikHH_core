"""Pure data-processing helpers for terrain apps.

This module holds everything that turns raw GeoTIFF inputs into a
:class:`TerrainMesh` ready for IFC export: adaptive point sampling,
boundary stitching and Delaunay triangulation. No ``ifcopenshell`` calls
live here; all IFC-writing logic lives in each app's ``app.py``.

Public entry point:
    :func:`extract_mesh_adaptive` — feature-preserving adaptive sampling
    for one or more GeoTIFFs, returning a :class:`TerrainMesh`. Optional
    ALKIS ``Nutzung`` rings (``guide_records``) are used as **Bruchkanten**
    (constrained edges) in a Constrained Delaunay triangulation.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, FrozenSet, Iterable, List, Optional, Sequence, Tuple, Union

import numpy as np
from scipy.spatial import Delaunay

from BIMFabrikHH_core.config.logging_config import get_logger
from BIMFabrikHH_core.core.georeferencing.extract_elevation import (
    invalid_z,
    is_url,
    open_geotiff,
    sample_elevations_from_raster,
)
from BIMFabrikHH_core.core.georeferencing.coordinate_transformer import CoordinateTransformer
from BIMFabrikHH_core.core.ogc_extractor import strip_closing_duplicate_xy
from BIMFabrikHH_core.data_models.streets import (
    PARCELS_LABEL,
    PARCEL_NUTZARTEN,
    load_guide_records_from_oaf,
    nutzung_split_label,
)
from BIMFabrikHH_core.data_models.terrain_mesh import TerrainMesh

logger = get_logger("terrain_processing")

DEFAULT_GUIDE_EDGE_SPACING_M: float = 5.0
NUTZART_ORDER: Tuple[str, ...] = (
    "Strassenverkehr|Fahrbahn",
    "Strassenverkehr|Begleitfläche Straßenverkehr",
    "Strassenverkehr|Busbahnhof",
    "Strassenverkehr|Fußgängerzone",
    "Strassenverkehr|Parkplatz",
    "Strassenverkehr",
    "Weg",
    "Bahnverkehr",
    "Platz",
    "Wohnbauflaeche",
    "Industrie Und Gewerbeflaeche",
    "Flaeche Gemischter Nutzung",
    "Flaeche Besonderer Funktionaler Praegung",
    "Sport Freizeit Und Erholungsflaeche",
    "Fliessgewaesser",
    "Stehendes Gewaesser",
    "Hafenbecken",
    "Meer",
    "Schiffsverkehr",
    "Unland Vegetationslose Flaeche",
)
WATER_EMPTY_INTERIOR: FrozenSet[str] = frozenset(
    {
        "Fliessgewaesser",
        "Stehendes Gewaesser",
        "Hafenbecken",
        "Meer",
        "Schiffsverkehr",
    }
)
# One horizontal plane per ring. Opposite Ufer often differ by metres (quay
# vs path); along-ring smoothing kept that and tilted the water surface.
WATER_PLANAR: FrozenSet[str] = WATER_EMPTY_INTERIOR
WATER_FLOWING: FrozenSet[str] = frozenset()
DEFAULT_FLOWING_WATER_WINDOW_M: float = 30.0
_WGS84 = "EPSG:4326"
_UTM32 = "EPSG:25832"


@dataclass(frozen=True)
class GuideRing:
    """One ALKIS Nutzung exterior ring in EPSG:25832, with its split label."""

    xy: np.ndarray
    nutzart: str = ""
    bez: str = ""
    label: str = ""


# ---------------------------------------------------------------------------
# Terrain-feature analysis + adaptive sampling
# ---------------------------------------------------------------------------

_MIN_FACE_AREA_XY = 1e-3


def analyze_terrain_features(elevation_data: np.ndarray) -> np.ndarray:
    """Detect important terrain features using gradient analysis.

    Importance is a weighted sum of slope and absolute curvature:
    ``0.7 * slope + 0.3 * |curvature|``. Steeper / more curved pixels
    get a higher score and are preferred during adaptive sampling.

    Args:
        elevation_data: 2D array of elevation values (any floating dtype).

    Returns:
        2D array of importance values, same shape as ``elevation_data``.
    """
    elevation_data = np.nan_to_num(elevation_data, nan=0.0, posinf=None, neginf=None)

    gradient_y, gradient_x = np.gradient(elevation_data)
    gradient_x = np.nan_to_num(gradient_x, nan=0.0)
    gradient_y = np.nan_to_num(gradient_y, nan=0.0)

    slope = np.sqrt(gradient_x**2 + gradient_y**2)
    curvature = np.gradient(gradient_x)[0] + np.gradient(gradient_y)[1]
    curvature = np.nan_to_num(curvature, nan=0.0)

    return 0.7 * slope + 0.3 * np.abs(curvature)


def adaptive_sampling(
    elevation_data: np.ndarray,
    transform,
    *,
    min_points: int = 1000,
    importance_threshold: float = 0.1,
    nodata: Optional[float] = None,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Sample points adaptively based on terrain importance.

    Args:
        elevation_data: 2D array of elevation values.
        transform: Affine transform from ``rasterio`` for pixel → world
            coordinate conversion.
        min_points: Lower bound on the number of sampled points; if the
            importance filter would drop below this, the top-N points by
            importance are kept instead.
        importance_threshold: Minimum normalized importance to retain a
            point (0–1 scale).
        nodata: Raster nodata value. Those cells, non-finite values, and
            the ``0.0`` Hamburg DGM fill are never sampled.

    Returns:
        ``(x_coords, y_coords, z_values)`` arrays in the raster CRS.
    """
    elevation = np.asarray(elevation_data, dtype=float)
    valid = ~invalid_z(elevation, nodata)
    if not np.any(valid):
        return np.array([]), np.array([]), np.array([])

    filled = elevation.copy()
    filled[~valid] = float(np.median(elevation[valid]))
    importance = analyze_terrain_features(filled)
    importance[~valid] = 0.0

    importance_range = importance.max() - importance.min()
    if importance_range > 0:
        importance = (importance - importance.min()) / importance_range
    else:
        importance = np.ones_like(importance)
        importance[~valid] = 0.0

    height, width = elevation.shape
    x = np.linspace(transform[2], transform[2] + transform[0] * width, width)
    y = np.linspace(transform[5], transform[5] + transform[4] * height, height)
    x_grid, y_grid = np.meshgrid(x, y)

    mask = (importance > importance_threshold) & valid

    if int(np.sum(mask)) < min_points:
        ranked = np.argsort(importance.ravel())
        take = ranked[-min_points:]
        top = np.zeros_like(importance, dtype=bool)
        top.ravel()[take] = True
        mask = top & valid

    return x_grid[mask], y_grid[mask], elevation[mask]


# ---------------------------------------------------------------------------
# Boundary stitching
# ---------------------------------------------------------------------------


def create_boundary_points(
    bbox: Tuple[float, float, float, float], spacing: float = 5.0
) -> Tuple[np.ndarray, np.ndarray]:
    """Create regularly spaced boundary points along all four bbox edges.

    Returns ``(boundary_x, boundary_y)`` arrays. Elevations are sampled
    separately via :func:`sample_elevations_from_raster`.
    """
    min_x, min_y, max_x, max_y = bbox
    width = max_x - min_x
    height = max_y - min_y
    n_points_x = max(2, int(width / spacing) + 1)
    n_points_y = max(2, int(height / spacing) + 1)

    boundary_x: List[float] = []
    boundary_y: List[float] = []

    for x in np.linspace(min_x, max_x, n_points_x):
        boundary_x.append(x)
        boundary_y.append(min_y)
    for x in np.linspace(min_x, max_x, n_points_x):
        boundary_x.append(x)
        boundary_y.append(max_y)
    for y in np.linspace(min_y, max_y, n_points_y)[1:-1]:
        boundary_x.append(min_x)
        boundary_y.append(y)
    for y in np.linspace(min_y, max_y, n_points_y)[1:-1]:
        boundary_x.append(max_x)
        boundary_y.append(y)

    return np.array(boundary_x), np.array(boundary_y)


# ---------------------------------------------------------------------------
# Optional ALKIS street-outline guide (soft constraint)
# ---------------------------------------------------------------------------


def _densify_ring_xy(ring_xy: np.ndarray, spacing: float) -> np.ndarray:
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


def _clip_ring_to_bbox(
    ring_xy: np.ndarray,
    bbox: Tuple[float, float, float, float],
) -> Optional[np.ndarray]:
    """Sutherland–Hodgman clip of a closed ring to an axis-aligned rectangle."""
    min_x, min_y, max_x, max_y = bbox
    if max_x <= min_x or max_y <= min_y or len(ring_xy) < 3:
        return None

    def _clip(
        poly: List[Tuple[float, float]],
        inside,
        intersect,
    ) -> List[Tuple[float, float]]:
        if not poly:
            return []
        out: List[Tuple[float, float]] = []
        prev = poly[-1]
        prev_in = inside(prev)
        for curr in poly:
            curr_in = inside(curr)
            if curr_in:
                if not prev_in:
                    out.append(intersect(prev, curr))
                out.append(curr)
            elif prev_in:
                out.append(intersect(prev, curr))
            prev = curr
            prev_in = curr_in
        return out

    def _lerp_x(a: Tuple[float, float], b: Tuple[float, float], x: float) -> Tuple[float, float]:
        ax, ay = a
        bx, by = b
        dx = bx - ax
        t = 0.0 if dx == 0.0 else (x - ax) / dx
        return (x, ay + t * (by - ay))

    def _lerp_y(a: Tuple[float, float], b: Tuple[float, float], y: float) -> Tuple[float, float]:
        ax, ay = a
        bx, by = b
        dy = by - ay
        t = 0.0 if dy == 0.0 else (y - ay) / dy
        return (ax + t * (bx - ax), y)

    poly = [(float(x), float(y)) for x, y in ring_xy]
    poly = _clip(poly, lambda p: p[0] >= min_x, lambda a, b: _lerp_x(a, b, min_x))
    poly = _clip(poly, lambda p: p[0] <= max_x, lambda a, b: _lerp_x(a, b, max_x))
    poly = _clip(poly, lambda p: p[1] >= min_y, lambda a, b: _lerp_y(a, b, min_y))
    poly = _clip(poly, lambda p: p[1] <= max_y, lambda a, b: _lerp_y(a, b, max_y))
    if len(poly) < 3:
        return None
    arr = np.asarray(poly, dtype=float)
    arr[:, 0] = np.clip(arr[:, 0], min_x, max_x)
    arr[:, 1] = np.clip(arr[:, 1], min_y, max_y)
    return arr


def collect_guide_rings(
    records: Sequence[Any],
    *,
    spacing: float = DEFAULT_GUIDE_EDGE_SPACING_M,
    bbox_utm: Optional[Tuple[float, float, float, float]] = None,
) -> List[GuideRing]:
    """Densify ALKIS Nutzung exterior rings to ``(N, 2)`` arrays in EPSG:25832.

    ``records`` are :class:`StreetRecord`-like objects (``rings``, ``geometry_crs``).
    When ``bbox_utm`` is set, each ring is clipped to that rectangle so Bruchkanten
    cannot extend the TIN past the same crop used for the unguided DGM.
    """
    transformer: Optional[CoordinateTransformer] = None
    out: List[GuideRing] = []

    for rec in records:
        rings = getattr(rec, "rings", None) or []
        source_crs = getattr(rec, "geometry_crs", _UTM32)
        nutzart = str(getattr(rec, "nutzart", "") or "")
        bez = str(getattr(rec, "bez", "") or "")
        label = nutzung_split_label(nutzart, bez)
        for ring in rings:
            cleaned = strip_closing_duplicate_xy(list(ring))
            if len(cleaned) < 3:
                continue
            if source_crs == _UTM32:
                arr = np.asarray(cleaned, dtype=float)
            else:
                if transformer is None:
                    transformer = CoordinateTransformer(_WGS84, _UTM32)
                xe, yn = transformer.transform_xy_batch([p[0] for p in cleaned], [p[1] for p in cleaned])
                arr = np.column_stack((xe, yn))
            if bbox_utm is not None:
                arr = _clip_ring_to_bbox(arr, bbox_utm)
                if arr is None:
                    continue
            arr = _densify_ring_xy(arr, spacing)
            if len(arr) >= 2:
                out.append(GuideRing(xy=arr, nutzart=nutzart, bez=bez, label=label))
    return out


def collect_guide_xy(
    records: Sequence[Any],
    *,
    spacing: float = DEFAULT_GUIDE_EDGE_SPACING_M,
    bbox_utm: Optional[Tuple[float, float, float, float]] = None,
) -> Tuple[np.ndarray, np.ndarray]:
    """Flatten :func:`collect_guide_rings` to ``(x, y)`` arrays."""
    rings = collect_guide_rings(records, spacing=spacing, bbox_utm=bbox_utm)
    if not rings:
        return np.empty(0, dtype=float), np.empty(0, dtype=float)
    stacked = np.vstack([r.xy for r in rings])
    return stacked[:, 0], stacked[:, 1]


def drop_sliver_faces(
    vertices: List[List[float]],
    faces: List[List[int]],
    *,
    min_area_xy: float = _MIN_FACE_AREA_XY,
) -> Tuple[List[List[float]], List[List[int]]]:
    """Remove triangles with near-zero XY area (collinear frame slivers)."""
    if not vertices or not faces:
        return vertices, faces
    verts = np.asarray(vertices, dtype=float)
    tris = np.asarray(faces, dtype=int)
    if tris.ndim != 2 or tris.shape[1] < 3:
        return vertices, faces
    a, b, c = verts[tris[:, 0]], verts[tris[:, 1]], verts[tris[:, 2]]
    area = 0.5 * np.abs((b[:, 0] - a[:, 0]) * (c[:, 1] - a[:, 1]) - (b[:, 1] - a[:, 1]) * (c[:, 0] - a[:, 0]))
    keep = area >= min_area_xy
    dropped = int((~keep).sum())
    if dropped:
        logger.info("Dropped %d sliver faces (XY area < %g m²)", dropped, min_area_xy)
    kept = tris[keep]
    if len(kept) == 0:
        return [], []
    used = np.unique(kept)
    remap = {int(old): new for new, old in enumerate(used)}
    return verts[used].tolist(), [[remap[int(i)] for i in tri] for tri in kept]


def filter_and_add_boundary(
    x_coords: np.ndarray,
    y_coords: np.ndarray,
    z_values: np.ndarray,
    boundary_x: np.ndarray,
    boundary_y: np.ndarray,
    boundary_z: np.ndarray,
    bbox: Tuple[float, float, float, float],
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Crop interior points to ``bbox`` and merge with boundary points.

    Drops boundary points whose elevation could not be sampled (``NaN``).
    """
    min_x, min_y, max_x, max_y = bbox

    inside_mask = (x_coords >= min_x) & (x_coords <= max_x) & (y_coords >= min_y) & (y_coords <= max_y)
    x_coords = x_coords[inside_mask]
    y_coords = y_coords[inside_mask]
    z_values = z_values[inside_mask]

    valid_boundary = ~np.isnan(boundary_z)
    boundary_x = boundary_x[valid_boundary]
    boundary_y = boundary_y[valid_boundary]
    boundary_z = boundary_z[valid_boundary]

    combined_x = np.concatenate([x_coords, boundary_x])
    combined_y = np.concatenate([y_coords, boundary_y])
    combined_z = np.concatenate([z_values, boundary_z])

    logger.info(f"Added {len(boundary_x)} boundary points (from GeoTIFF), {len(x_coords)} interior points")

    return combined_x, combined_y, combined_z


# ---------------------------------------------------------------------------
# Mesh generation
# ---------------------------------------------------------------------------


def generate_delaunay_mesh(
    x_coords: np.ndarray, y_coords: np.ndarray, z_values: np.ndarray
) -> Tuple[List[List[float]], List[List[int]]]:
    """Delaunay-triangulate a point cloud in XY and lift it to 3D.

    Returns ``(vertices, faces)``. Returns empty lists if fewer than
    three points are available.
    """
    if len(x_coords) < 3:
        logger.error("Not enough points for triangulation (minimum 3 required)")
        return [], []

    try:
        points_2d = np.column_stack((x_coords, y_coords))
        tri = Delaunay(points_2d)
        vertices = np.column_stack((x_coords, y_coords, z_values)).tolist()
        faces = tri.simplices.tolist()
        return vertices, faces
    except Exception as e:
        logger.error(f"Error during mesh generation: {e}")
        return [], []


def generate_constrained_mesh(
    x_coords: np.ndarray,
    y_coords: np.ndarray,
    z_values: np.ndarray,
    rings_xy: Sequence[np.ndarray],
    rings_z: Sequence[np.ndarray],
    *,
    snap_decimals: int = 3,
) -> Tuple[List[List[float]], List[List[int]]]:
    """Constrained Delaunay TIN with ALKIS rings as Bruchkanten.

    Terrain points and breakline vertices are snapped in XY, then Shewchuk
    Triangle honours consecutive ring edges whose both endpoints have a
    valid DGM height. Requires the ``triangle`` package.
    """
    try:
        import triangle as tr
    except ImportError as exc:
        raise ImportError(
            "Hard Bruchkanten need the 'triangle' package (Shewchuk Triangle). "
            "Install it with: pip install triangle"
        ) from exc

    index_of: dict[Tuple[float, float], int] = {}
    points_xy: List[List[float]] = []
    points_z: List[float] = []

    def _add(px: float, py: float, pz: float) -> int:
        key = (round(float(px), snap_decimals), round(float(py), snap_decimals))
        existing = index_of.get(key)
        if existing is not None:
            return existing
        idx = len(points_xy)
        index_of[key] = idx
        points_xy.append([float(px), float(py)])
        points_z.append(float(pz))
        return idx

    for px, py, pz in zip(x_coords, y_coords, z_values):
        if np.isnan(pz):
            continue
        _add(px, py, pz)

    segments: List[List[int]] = []
    for ring_xy, ring_z in zip(rings_xy, rings_z):
        if len(ring_xy) < 2:
            continue
        idxs: List[Optional[int]] = []
        for (px, py), pz in zip(ring_xy, ring_z):
            if np.isnan(pz):
                idxs.append(None)
            else:
                idxs.append(_add(px, py, pz))
        n = len(idxs)
        for i in range(n):
            a, b = idxs[i], idxs[(i + 1) % n]
            if a is not None and b is not None and a != b:
                segments.append([a, b])

    if len(points_xy) < 3:
        logger.error("Not enough points for constrained triangulation")
        return [], []

    if not segments:
        logger.warning("No valid Bruchkante segments; falling back to unconstrained Delaunay")
        return generate_delaunay_mesh(
            np.asarray(points_xy)[:, 0],
            np.asarray(points_xy)[:, 1],
            np.asarray(points_z),
        )

    try:
        result = tr.triangulate(
            {"vertices": np.asarray(points_xy, dtype=float), "segments": np.asarray(segments, dtype=np.int32)},
            "pc",
        )
        tri_xy = np.asarray(result["vertices"], dtype=float)
        faces_arr = np.asarray(result["triangles"], dtype=int)
        if faces_arr.size and faces_arr.min() >= 1 and faces_arr.max() == len(tri_xy):
            faces_arr = faces_arr - 1
        z_of = {
            (round(float(p[0]), snap_decimals), round(float(p[1]), snap_decimals)): float(z)
            for p, z in zip(points_xy, points_z)
        }
        vertices: List[List[float]] = []
        for x, y in tri_xy:
            z = z_of.get((round(float(x), snap_decimals), round(float(y), snap_decimals)))
            if z is None and points_xy:
                d2 = (np.asarray(points_xy)[:, 0] - x) ** 2 + (np.asarray(points_xy)[:, 1] - y) ** 2
                z = points_z[int(np.argmin(d2))]
            vertices.append([float(x), float(y), float(z if z is not None else 0.0)])
        valid = (faces_arr >= 0) & (faces_arr < len(vertices))
        faces = faces_arr[valid.all(axis=1)].tolist() if faces_arr.size else []
        logger.info(
            "CDT mesh: %d vertices, %d faces, %d Bruchkante segments",
            len(vertices),
            len(faces),
            len(segments),
        )
        return vertices, faces
    except Exception as e:
        logger.error("Error during constrained triangulation: %s", e)
        return [], []


def _points_in_ring(px: np.ndarray, py: np.ndarray, ring_xy: np.ndarray) -> np.ndarray:
    """Vectorized ray-cast; ``px``/``py`` are 1-D, ``ring_xy`` is an open exterior ring."""
    x = ring_xy[:, 0]
    y = ring_xy[:, 1]
    x2 = np.roll(x, -1)
    y2 = np.roll(y, -1)
    yi = y[:, None]
    yj = y2[:, None]
    xi = x[:, None]
    xj = x2[:, None]
    denom = yj - yi
    denom = np.where(denom == 0.0, 1e-12, denom)
    intersects = ((yi > py) != (yj > py)) & (px < (xj - xi) * (py - yi) / denom + xi)
    return np.mod(intersects.sum(axis=0), 2).astype(bool)


def _points_near_ring(px: np.ndarray, py: np.ndarray, ring_xy: np.ndarray, tol: float) -> np.ndarray:
    """True when each point lies within ``tol`` metres of a ring edge.

    A point within ``tol`` of any edge must lie in the ring AABB expanded by
    ``tol``. Reject the rest first so the ``(n_pts × n_edges)`` distance
    matrix is only built for candidates (same snap set as the full broadcast).
    """
    n = len(px)
    if n == 0:
        return np.zeros(0, dtype=bool)
    pad = float(tol) + 1e-9
    cand = (
        (px >= float(ring_xy[:, 0].min()) - pad)
        & (px <= float(ring_xy[:, 0].max()) + pad)
        & (py >= float(ring_xy[:, 1].min()) - pad)
        & (py <= float(ring_xy[:, 1].max()) + pad)
    )
    if not np.any(cand):
        return np.zeros(n, dtype=bool)
    x1, y1 = ring_xy[:, 0], ring_xy[:, 1]
    x2, y2 = np.roll(x1, -1), np.roll(y1, -1)
    dx, dy = x2 - x1, y2 - y1
    length2 = dx * dx + dy * dy
    length2 = np.where(length2 == 0.0, 1.0, length2)
    cpx, cpy = px[cand], py[cand]
    t = ((cpx[:, None] - x1) * dx + (cpy[:, None] - y1) * dy) / length2
    t = np.clip(t, 0.0, 1.0)
    dist2 = (cpx[:, None] - (x1 + t * dx)) ** 2 + (cpy[:, None] - (y1 + t * dy)) ** 2
    out = np.zeros(n, dtype=bool)
    out[cand] = np.any(dist2 <= tol * tol, axis=1)
    return out


def _points_in_or_on_ring(
    px: np.ndarray,
    py: np.ndarray,
    ring_xy: np.ndarray,
    *,
    tol: float = 0.05,
) -> np.ndarray:
    """Inside the ring or on its outline (CDT vertices sit on Bruchkanten)."""
    inside = _points_in_ring(px, py, ring_xy)
    todo = ~inside
    if not np.any(todo):
        return inside
    near = _points_near_ring(px[todo], py[todo], ring_xy, tol)
    inside = inside.copy()
    inside[np.flatnonzero(todo)[near]] = True
    return inside


def drop_points_inside_rings(
    x_coords: np.ndarray,
    y_coords: np.ndarray,
    z_values: np.ndarray,
    rings: Sequence[GuideRing],
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Remove points whose XY lies inside any of ``rings`` (water interiors)."""
    if len(x_coords) == 0 or not rings:
        return x_coords, y_coords, z_values
    inside = np.zeros(len(x_coords), dtype=bool)
    for ring in rings:
        if len(ring.xy) < 3:
            continue
        xmin, ymin = ring.xy.min(axis=0)
        xmax, ymax = ring.xy.max(axis=0)
        cand = (~inside) & (x_coords >= xmin) & (x_coords <= xmax) & (y_coords >= ymin) & (y_coords <= ymax)
        if not np.any(cand):
            continue
        idx = np.flatnonzero(cand)
        hit = _points_in_ring(x_coords[idx], y_coords[idx], ring.xy)
        inside[idx[hit]] = True
    n_drop = int(np.sum(inside))
    if n_drop:
        logger.info("Dropped %d interior points inside water Flächen", n_drop)
    keep = ~inside
    return x_coords[keep], y_coords[keep], z_values[keep]


def flatten_planar_water_z(
    rings: Sequence[GuideRing],
    rings_z: Sequence[np.ndarray],
    *,
    planar_nutzarten: FrozenSet[str] = WATER_PLANAR,
) -> None:
    """Set each water ring to one Z (median shoreline), including canals."""
    for ring, ring_z in zip(rings, rings_z):
        if ring.nutzart not in planar_nutzarten:
            continue
        valid = ring_z[~np.isnan(ring_z)]
        if valid.size == 0:
            logger.warning("No shoreline Z for planar water %s; ring left unset", ring.nutzart)
            continue
        plane_z = float(np.median(valid))
        ring_z[:] = plane_z
        logger.info(
            "Planar water %s: %d vertices at Z=%.3f (median shoreline)",
            ring.nutzart,
            len(ring_z),
            plane_z,
        )


def _along_ring_median_z(xy: np.ndarray, z: np.ndarray, window_m: float) -> np.ndarray:
    """Replace each Z with the median of vertices within ``window_m`` along the ring."""
    n = len(xy)
    out = np.asarray(z, dtype=float).copy()
    if n == 0 or window_m <= 0.0:
        return out
    dx = np.diff(xy[:, 0], append=xy[0, 0])
    dy = np.diff(xy[:, 1], append=xy[0, 1])
    seg = np.hypot(dx, dy)
    perimeter = float(seg.sum())
    if perimeter <= 0.0:
        return out
    valid = ~np.isnan(out)
    if not np.any(valid):
        return out
    if window_m >= 0.5 * perimeter:
        out[:] = float(np.median(out[valid]))
        return out
    cum = np.empty(n, dtype=float)
    cum[0] = 0.0
    if n > 1:
        cum[1:] = np.cumsum(seg[:-1])
    cum3 = np.concatenate([cum, cum + perimeter, cum + 2.0 * perimeter])
    z3 = np.concatenate([out, out, out])
    for i in range(n):
        center = cum[i] + perimeter
        lo = int(np.searchsorted(cum3, center - window_m, side="left"))
        hi = int(np.searchsorted(cum3, center + window_m, side="right"))
        window = z3[lo:hi]
        window = window[~np.isnan(window)]
        if window.size:
            out[i] = float(np.median(window))
    return out


def smooth_flowing_water_z(
    rings: Sequence[GuideRing],
    rings_z: Sequence[np.ndarray],
    *,
    window_m: float = DEFAULT_FLOWING_WATER_WINDOW_M,
    flowing_nutzarten: FrozenSet[str] = WATER_FLOWING,
) -> None:
    """Smooth Fließgewässer shoreline Z with an along-ring median.

    Each vertex takes the median of neighbours within ``window_m`` of
    shoreline length (wraps around the ring). The long slope stays;
    short DGM spikes do not. Standing water is left to
    :func:`flatten_planar_water_z`. Writes into ``rings_z`` before CDT
    so the water mesh and constraint vertices share the same Z. No
    all-TIN bank snap.
    """
    for ring, ring_z in zip(rings, rings_z):
        if ring.nutzart not in flowing_nutzarten or len(ring.xy) < 3:
            continue
        z = np.asarray(ring_z, dtype=float)
        if z.size != len(ring.xy):
            continue
        smoothed = _along_ring_median_z(np.asarray(ring.xy, dtype=float), z, window_m)
        ring_z[:] = smoothed
        logger.info(
            "Flowing water %s: %d vertices, along-ring median window=%.1f m",
            ring.nutzart,
            len(ring_z),
            window_m,
        )


def snap_vertices_to_planar_water_z(
    vertices: List[List[float]],
    rings: Sequence[GuideRing],
    rings_z: Sequence[np.ndarray],
    *,
    tol: float = 0.05,
    planar_nutzarten: FrozenSet[str] = WATER_PLANAR,
) -> List[List[float]]:
    """Set TIN vertices on a standing-water ring to that ring's median Z.

    Fließgewässer are not snapped here (along-ring median is already in
    ``rings_z`` before CDT). Land then meets still water with no vertical
    gap. ``tol`` is metres in XY.
    """
    if not vertices or not rings:
        return vertices
    arr = np.asarray(vertices, dtype=float)
    snapped = 0
    for ring, ring_z in zip(rings, rings_z):
        if ring.nutzart not in planar_nutzarten or len(ring.xy) < 3:
            continue
        valid = np.asarray(ring_z, dtype=float)
        valid = valid[~np.isnan(valid)]
        if valid.size == 0:
            continue
        plane_z = float(np.median(valid))
        on_bank = _points_near_ring(arr[:, 0], arr[:, 1], ring.xy, tol)
        if not np.any(on_bank):
            continue
        snapped += int(np.sum(on_bank))
        arr[on_bank, 2] = plane_z
    if snapped:
        logger.info("Snapped %d bank vertex(es) to planar water median Z", snapped)
    return arr.tolist()


def _ring_signed_area_xy(xy: np.ndarray) -> float:
    x, y = xy[:, 0], xy[:, 1]
    return float(0.5 * np.sum(x * np.roll(y, -1) - np.roll(x, -1) * y))


def _dedupe_ring_xy(xy: np.ndarray, z: np.ndarray, *, decimals: int = 3) -> Tuple[np.ndarray, np.ndarray]:
    """Drop consecutive-duplicate XY after snapping so Delaunay can run."""
    keys = np.round(xy, decimals)
    keep: List[int] = []
    seen: set[Tuple[float, float]] = set()
    for i, (x, y) in enumerate(keys):
        key = (float(x), float(y))
        if key in seen:
            continue
        seen.add(key)
        keep.append(i)
    if len(keep) == len(xy):
        return xy, z
    idx = np.asarray(keep, dtype=int)
    return xy[idx], z[idx]


def _triangulate_polygon_xy(xy: np.ndarray) -> Tuple[np.ndarray, List[List[int]]]:
    """Fill a simple ring to the Ufer (constrained PSLG, not convex Delaunay).

    Unconstrained Delaunay + ``centroid inside`` drops triangles whose
    chord spans a concave bay (Alster Ufer). Shewchuk ``p`` keeps the
    Bruchkante and fills the Fläche. Returns ``(vertices, faces)``;
    Triangle may add Steiner points.
    """
    if len(xy) < 3:
        return np.asarray(xy, dtype=float), []
    pts = np.asarray(xy, dtype=float)
    n = len(pts)
    segments = np.column_stack(
        (np.arange(n, dtype=np.int32), np.roll(np.arange(n, dtype=np.int32), -1))
    )
    try:
        import triangle as tr

        result = tr.triangulate({"vertices": pts, "segments": segments}, "p")
        out_xy = np.asarray(result["vertices"], dtype=float)
        faces_arr = np.asarray(result["triangles"], dtype=int)
        if faces_arr.size == 0:
            return out_xy, []
        if faces_arr.min() >= 1 and faces_arr.max() == len(out_xy):
            faces_arr = faces_arr - 1
        return out_xy, [[int(a), int(b), int(c)] for a, b, c in faces_arr]
    except Exception as exc:
        logger.warning("Water ring CDT failed (%s); falling back to in-polygon Delaunay", exc)
    try:
        tri = Delaunay(pts)
    except Exception as exc:
        logger.warning("Water ring Delaunay failed (%s); skipping ring", exc)
        return pts, []
    faces: List[List[int]] = []
    for simplex in np.asarray(tri.simplices, dtype=int):
        corner = pts[simplex]
        cx = float(corner[:, 0].mean())
        cy = float(corner[:, 1].mean())
        if bool(_points_in_ring(np.array([cx]), np.array([cy]), pts)[0]):
            faces.append([int(simplex[0]), int(simplex[1]), int(simplex[2])])
    return pts, faces


def build_water_polygon_meshes(
    rings: Sequence[GuideRing],
    rings_z: Sequence[np.ndarray],
    *,
    origin_shift: Optional[Tuple[float, float]] = None,
) -> Dict[str, TerrainMesh]:
    """Triangulated water surfaces with no interior DGM points.

    Each water ring is filled with a constrained triangulation so the
    surface reaches the Ufer (concave bays stay inside the Fläche).
    Rings of the same ``nutzart`` are grouped into one mesh. Vertices
    keep shoreline Z (planar median or Fließgewässer along-ring
    median already written into ``rings_z``).
    """
    grouped: Dict[str, List[Tuple[np.ndarray, np.ndarray]]] = {}
    for ring, ring_z in zip(rings, rings_z):
        if ring.nutzart not in WATER_EMPTY_INTERIOR or len(ring.xy) < 3:
            continue
        z = np.asarray(ring_z, dtype=float)
        if z.size != len(ring.xy):
            continue
        if np.all(np.isnan(z)):
            continue
        fill = float(np.nanmedian(z))
        z = np.where(np.isnan(z), fill, z)
        grouped.setdefault(ring.nutzart, []).append((ring.xy, z))

    out: Dict[str, TerrainMesh] = {}
    ox, oy = origin_shift if origin_shift is not None else (0.0, 0.0)
    for nutzart, items in grouped.items():
        vertices: List[List[float]] = []
        faces: List[List[int]] = []
        for xy, z in items:
            xy, z = _dedupe_ring_xy(np.asarray(xy, dtype=float), np.asarray(z, dtype=float))
            if len(xy) < 3:
                continue
            if _ring_signed_area_xy(xy) < 0:
                xy = xy[::-1]
                z = z[::-1]
            out_xy, local = _triangulate_polygon_xy(xy)
            if not local:
                continue
            if len(out_xy) == len(xy) and np.allclose(out_xy, xy):
                z_out = z
            else:
                d2 = (out_xy[:, None, 0] - xy[None, :, 0]) ** 2 + (out_xy[:, None, 1] - xy[None, :, 1]) ** 2
                z_out = z[np.argmin(d2, axis=1)]
            start = len(vertices)
            for (x, y), zi in zip(out_xy, z_out):
                vertices.append([float(x) - ox, float(y) - oy, float(zi)])
            faces.extend([[start + a, start + b, start + c] for a, b, c in local])
        if vertices and faces:
            vertices, faces = drop_sliver_faces(vertices, faces)
        if vertices and faces:
            out[nutzart] = TerrainMesh(vertices=vertices, faces=faces)
            logger.info(
                "Water triangles %s: %d face(s), %d vertices (no interior points)",
                nutzart,
                len(faces),
                len(vertices),
            )
    return out


def _submesh(mesh: TerrainMesh, face_indices: Sequence[int]) -> TerrainMesh:
    """Copy ``mesh`` faces ``face_indices`` and remap unused vertices away."""
    if not face_indices:
        return TerrainMesh(vertices=[], faces=[], nullpunkt=mesh.nullpunkt)
    faces = [mesh.faces[i] for i in face_indices]
    used = sorted({int(i) for face in faces for i in face})
    remap = {old: new for new, old in enumerate(used)}
    vertices = [mesh.vertices[i] for i in used]
    remapped = [[remap[a], remap[b], remap[c]] for a, b, c in faces]
    return TerrainMesh(vertices=vertices, faces=remapped, nullpunkt=mesh.nullpunkt)


def subtract_rings_from_mesh(mesh: TerrainMesh, rings: Sequence[GuideRing]) -> TerrainMesh:
    """Drop faces whose centroid lies in any of ``rings``.

    Used to cut water Flächen out of land / leftover DGM. Bank triangles
    whose centroid stays on land are kept.
    """
    if mesh.is_empty() or not rings:
        return mesh
    verts = np.asarray(mesh.vertices, dtype=float)
    faces = np.asarray(mesh.faces, dtype=int)
    if faces.ndim != 2 or faces.shape[1] < 3:
        return mesh
    cx = verts[faces, 0].mean(axis=1)
    cy = verts[faces, 1].mean(axis=1)
    inside = np.zeros(len(faces), dtype=bool)
    for ring in rings:
        if len(ring.xy) < 3:
            continue
        xmin, ymin = ring.xy.min(axis=0)
        xmax, ymax = ring.xy.max(axis=0)
        cand = (~inside) & (cx >= xmin) & (cx <= xmax) & (cy >= ymin) & (cy <= ymax)
        if not np.any(cand):
            continue
        idx = np.flatnonzero(cand)
        hit = _points_in_ring(cx[idx], cy[idx], ring.xy)
        inside[idx[hit]] = True
    keep = np.flatnonzero(~inside)
    dropped = int(inside.sum())
    if dropped:
        logger.info("Cut %d face(s) under water Flächen from mesh", dropped)
    if len(keep) == 0:
        return TerrainMesh(vertices=[], faces=[], nullpunkt=mesh.nullpunkt)
    if dropped == 0:
        return mesh
    return _submesh(mesh, keep.tolist())


def cut_water_from_parts(
    parts: Dict[str, TerrainMesh],
    rings: Sequence[GuideRing],
) -> Dict[str, TerrainMesh]:
    """Remove water interiors from every non-water part; water keys unchanged."""
    water_rings = [r for r in rings if r.nutzart in WATER_EMPTY_INTERIOR]
    if not water_rings:
        return parts
    out: Dict[str, TerrainMesh] = {}
    for key, part in parts.items():
        if key in WATER_EMPTY_INTERIOR:
            out[key] = part
            continue
        cut = subtract_rings_from_mesh(part, water_rings)
        if not cut.is_empty():
            out[key] = cut
        else:
            logger.info("Part %s is empty after cutting water Flächen", key)
    return out


def split_mesh_by_nutzart(
    mesh: TerrainMesh,
    rings: Sequence[GuideRing],
    *,
    nutzarten: Sequence[str] = NUTZART_ORDER,
) -> Dict[str, TerrainMesh]:
    """Split a TIN into one mesh per Nutzung type plus leftover ``DGM``.

    A triangle belongs to a Fläche only when its centroid **and all three
    vertices** lie in that same ring (vertices on the outline count). That
    stops CDT faces that jump the gap between two nearby rings of the same
    type. All Flächen of one ``nutzart`` are still one IFC object; they are
    just no longer stitched together. Faces that miss every ring stay ``DGM``.
    """
    if mesh.is_empty() or not rings:
        return {"DGM": mesh}

    verts = np.asarray(mesh.vertices, dtype=float)
    faces = np.asarray(mesh.faces, dtype=int)
    cx = verts[faces, 0].mean(axis=1)
    cy = verts[faces, 1].mean(axis=1)

    labels = np.full(len(faces), "DGM", dtype=object)
    by_type: Dict[str, List[GuideRing]] = {}
    for ring in rings:
        key = ring.label or nutzung_split_label(ring.nutzart, ring.bez) or ring.nutzart
        if not key:
            continue
        by_type.setdefault(key, []).append(ring)

    assigned = np.zeros(len(faces), dtype=bool)
    ordered = [k for k in nutzarten if k in by_type]
    ordered.extend(sorted(k for k in by_type if k not in nutzarten))
    for key in ordered:
        todo = ~assigned
        if not np.any(todo):
            break
        inside = np.zeros(len(faces), dtype=bool)
        for ring in by_type[key]:
            xmin, ymin = ring.xy.min(axis=0)
            xmax, ymax = ring.xy.max(axis=0)
            cand = todo & (cx >= xmin) & (cx <= xmax) & (cy >= ymin) & (cy <= ymax)
            if not np.any(cand):
                continue
            idx = np.flatnonzero(cand)
            hit = _points_in_ring(cx[idx], cy[idx], ring.xy)
            idx = idx[hit]
            if len(idx) == 0:
                continue
            in_same = np.ones(len(idx), dtype=bool)
            for corner in range(3):
                in_same &= _points_in_or_on_ring(
                    verts[faces[idx, corner], 0],
                    verts[faces[idx, corner], 1],
                    ring.xy,
                )
            inside[idx[in_same]] = True
        labels[inside] = key
        assigned |= inside

    parts: Dict[str, TerrainMesh] = {}
    for key in ("DGM", *ordered):
        idxs = np.flatnonzero(labels == key)
        if len(idxs) == 0:
            continue
        part = _submesh(mesh, idxs.tolist())
        if not part.is_empty():
            parts[key] = part
            logger.info("Split %s: %d faces, %d vertices", key, len(part.faces), len(part.vertices))
    return parts or {"DGM": mesh}


def combine_terrain_meshes(meshes: Sequence[TerrainMesh]) -> TerrainMesh:
    """Concatenate meshes and remap face indices. Empty inputs are skipped."""
    vertices: List[List[float]] = []
    faces: List[List[int]] = []
    nullpunkt = None
    offset = 0
    for mesh in meshes:
        if mesh.is_empty():
            continue
        if nullpunkt is None:
            nullpunkt = mesh.nullpunkt
        vertices.extend(mesh.vertices)
        faces.extend([[a + offset, b + offset, c + offset] for a, b, c in mesh.faces])
        offset += len(mesh.vertices)
    return TerrainMesh(vertices=vertices, faces=faces, nullpunkt=nullpunkt)


def _is_parcel_split_key(key: str) -> bool:
    base = key.split("|", 1)[0]
    return key in PARCEL_NUTZARTEN or base in PARCEL_NUTZARTEN


def merge_parcel_meshes(parts: Dict[str, TerrainMesh]) -> Dict[str, TerrainMesh]:
    """Fold Siedlung and Unland into one ``Parcels`` mesh.

    Leftover DGM stays its own object. Merging it back in would refill the
    gaps between getrennte Flächen and stitch them together. Bruchkanten
    stay in the TIN; this only joins IFC / LandXML parts. Traffic,
    Grünfläche, and water keys are left unchanged.
    """
    merged: List[TerrainMesh] = []
    out: Dict[str, TerrainMesh] = {}
    for key, part in parts.items():
        if _is_parcel_split_key(key):
            if not part.is_empty():
                merged.append(part)
        else:
            out[key] = part
    combined = combine_terrain_meshes(merged)
    if not combined.is_empty():
        out[PARCELS_LABEL] = combined
    return out


def resolve_guide_records(
    guide_records: Optional[Sequence[Any]],
    bbox_wgs84: Optional[Tuple[float, float, float, float]],
    *,
    guide_from_oaf: bool,
    write_geojson: bool = False,
    output_dir: Optional[Union[str, Path]] = None,
) -> Optional[Sequence[Any]]:
    """Return the guide records to use, fetching from the Hamburg OAF if asked.

    Writer-neutral: both :class:`TerrainGenericApp` and :class:`TerrainRustApp`
    call this. When ``guide_records`` is already provided (or ``guide_from_oaf``
    is ``False``) it is returned unchanged. ``guide_from_oaf=True`` with no
    records pulls ALKIS ``Nutzung`` for ``bbox_wgs84``; ``write_geojson`` then
    persists the response next to ``output_dir``.
    """
    if guide_from_oaf and guide_records is None:
        if bbox_wgs84 is None:
            logger.warning("guide_from_oaf=True needs RequestParams.bbox")
            return guide_records
        out_dir = Path(output_dir) if output_dir is not None else None
        if write_geojson and out_dir is None:
            logger.warning("write_geojson=True needs output_path to know where to save")
        return load_guide_records_from_oaf(
            bbox_wgs84,
            write_geojson=bool(write_geojson and out_dir is not None),
            output_dir=out_dir,
        )
    if write_geojson:
        logger.warning("write_geojson=True is ignored unless guide_from_oaf fetches Nutzung")
    return guide_records


def build_landuse_parts(
    mesh: TerrainMesh,
    guide_records: Optional[Sequence[Any]],
    *,
    bbox_utm: Optional[Tuple[float, float, float, float]] = None,
    water_meshes: Optional[Dict[str, TerrainMesh]] = None,
    spacing: float = DEFAULT_GUIDE_EDGE_SPACING_M,
    split_by_landuse: bool = False,
    merge_parcels: bool = True,
) -> List[Tuple[str, TerrainMesh]]:
    """Split a TIN into ordered, labeled land-use parts (writer-neutral).

    Shared by :class:`TerrainGenericApp` and :class:`TerrainRustApp` so the
    geometry is identical regardless of the IFC writer. Returns an ordered
    ``[(label, mesh), ...]`` list; **psets are the caller's job**. The list is
    empty when there is nothing to split (no ``guide_records`` or neither
    ``split_by_landuse`` nor ``merge_parcels``), in which case the caller
    writes a single DGM mesh.

    ``merge_parcels`` folds Siedlung / Unland into one ``Parcels`` part;
    ``split_by_landuse`` keeps one part per Nutzung type and wins over it.
    Water triangles from ``water_meshes`` are re-inserted, then water rings are
    cut out of every other part.
    """
    if not guide_records or not (split_by_landuse or merge_parcels):
        if split_by_landuse and not guide_records:
            logger.warning("split_by_landuse=True needs guide_records; writing a single DGM")
        return []

    rings = collect_guide_rings(guide_records, spacing=spacing, bbox_utm=bbox_utm)
    split = split_mesh_by_nutzart(mesh, rings)
    split = cut_water_from_parts(split, rings)
    for key, water_mesh in (water_meshes or {}).items():
        if not water_mesh.is_empty():
            split[key] = water_mesh
            logger.info(
                "Water triangles %s: %d face(s), %d vertices",
                key,
                len(water_mesh.faces),
                len(water_mesh.vertices),
            )
    if not split_by_landuse:
        split = merge_parcel_meshes(split)

    ordered = [key for key in (PARCELS_LABEL, "DGM", *NUTZART_ORDER) if key in split]
    ordered.extend(sorted(key for key in split if key not in ordered))
    return [(key, split[key]) for key in ordered]


# ---------------------------------------------------------------------------
# Top-level extractor
# ---------------------------------------------------------------------------


def extract_mesh_adaptive(
    tif_files: Iterable[Union[str, Path]],
    *,
    folder_path: Optional[Union[str, Path]] = None,
    min_points: int = 1000,
    importance_threshold: float = 0.1,
    bbox_utm: Optional[Tuple[float, float, float, float]] = None,
    buffer_meters: float = 100.0,
    move_to_origin: bool = False,
    guide_records: Optional[Sequence[Any]] = None,
    guide_edge_spacing_m: float = DEFAULT_GUIDE_EDGE_SPACING_M,
    water_meshes: Optional[Dict[str, TerrainMesh]] = None,
) -> TerrainMesh:
    """Extract a :class:`TerrainMesh` from one or more GeoTIFFs.

    This is the full adaptive-sampling pipeline: per-file feature-aware
    point sampling, optional bbox cropping with a buffer, regular
    boundary points sampled directly from the rasters, Delaunay
    triangulation of the combined cloud, and optional translation so the
    mesh origin sits at ``(0, 0)``.

    Args:
        tif_files: Paths or URLs (absolute, or relative to ``folder_path``).
        folder_path: Optional parent folder / URL root. When provided,
            ``tif_files`` are interpreted as names within it.
        min_points: Minimum points to keep per file (see
            :func:`adaptive_sampling`).
        importance_threshold: Importance filter threshold (0–1).
        bbox_utm: Optional ``(min_x, min_y, max_x, max_y)`` in the
            project CRS (EPSG:25832). When ``None`` the full raster is
            used and no boundary stitching happens.
        buffer_meters: Half-width of the buffer applied to ``bbox_utm``
            when collecting interior points (not the final bbox used for
            boundary stitching, which is unbuffered).
        move_to_origin: When ``True`` and ``bbox_utm`` is provided, the
            output mesh is translated so ``(bbox.min_x, bbox.min_y)``
            becomes ``(0, 0)`` and the nullpunkt reflects that.
        guide_records: Optional ALKIS ``Nutzung`` records. When given,
            densified ring edges become Bruchkanten in a constrained
            Delaunay TIN. Water rings drop interior DGM points; standing
            water / harbour / sea / Fließgewässer use one shoreline-median
            Z per ring and land vertices on those rings are snapped to
            that plane. When
            ``water_meshes`` is a dict, each water type is stored there
            as a triangulated ring (no interior points). ``None`` / empty
            keeps the original unconstrained mesh.
        guide_edge_spacing_m: Spacing of vertices along each Bruchkante
            (DGM Z is sampled on those points). Extra samples *around*
            the street are not added.

    Returns:
        A :class:`TerrainMesh`. ``nullpunkt`` is set to the bbox corner
        (or ``(0, 0)`` when ``move_to_origin`` is requested); when no
        bbox is given, it's set to the minimum ``(x, y)`` of the mesh.
    """
    tif_list: List[Union[str, Path]] = list(tif_files)

    all_x: List[np.ndarray] = []
    all_y: List[np.ndarray] = []
    all_z: List[np.ndarray] = []

    boundary_x: Optional[np.ndarray] = None
    boundary_y: Optional[np.ndarray] = None
    boundary_z: Optional[np.ndarray] = None
    guide_rings: List[GuideRing] = []
    guide_rings_z: List[np.ndarray] = []
    expanded_bbox: Optional[Tuple[float, float, float, float]] = None

    if guide_records:
        guide_rings = collect_guide_rings(guide_records, spacing=guide_edge_spacing_m, bbox_utm=bbox_utm)
        guide_rings_z = [np.full(len(r.xy), np.nan) for r in guide_rings]
        if guide_rings:
            logger.info(
                "Prepared %d ALKIS rings (%d vertices) as Bruchkanten",
                len(guide_rings),
                int(sum(len(r.xy) for r in guide_rings)),
            )

    if bbox_utm is not None:
        expanded_bbox = (
            bbox_utm[0] - buffer_meters,
            bbox_utm[1] - buffer_meters,
            bbox_utm[2] + buffer_meters,
            bbox_utm[3] + buffer_meters,
        )
        logger.info(f"Expanded BBox (UTM): {expanded_bbox}")
        boundary_x, boundary_y = create_boundary_points(bbox_utm, spacing=5.0)
        boundary_z = np.full(len(boundary_x), np.nan)

    for file in tif_list:
        if folder_path is not None:
            path: Union[str, Path] = f"{folder_path}/{file}" if is_url(folder_path) else Path(folder_path) / file
        else:
            path = file
        logger.info(f"Processing {path}...")

        try:
            with open_geotiff(path) as src:
                elevation_data = src.read(1)
                if elevation_data.size == 0:
                    logger.warning(f"Empty elevation data in file: {path}")
                    continue

                transform = src.transform
                logger.info(f"Raster bounds: {src.bounds}")

                x_coords, y_coords, z_values = adaptive_sampling(
                    elevation_data,
                    transform,
                    min_points=min_points,
                    importance_threshold=importance_threshold,
                    nodata=src.nodata,
                )

                if expanded_bbox is not None:
                    inside = (
                        (x_coords >= expanded_bbox[0])
                        & (x_coords <= expanded_bbox[2])
                        & (y_coords >= expanded_bbox[1])
                        & (y_coords <= expanded_bbox[3])
                    )
                    x_coords = x_coords[inside]
                    y_coords = y_coords[inside]
                    z_values = z_values[inside]

                if len(x_coords) > 0:
                    all_x.append(x_coords)
                    all_y.append(y_coords)
                    all_z.append(z_values)
                    logger.info(f"Added {len(x_coords)} points from {path}")

                if boundary_x is not None and len(boundary_x) > 0 and boundary_z is not None:
                    bounds = src.bounds
                    in_raster = (
                        (boundary_x >= bounds.left)
                        & (boundary_x <= bounds.right)
                        & (boundary_y >= bounds.bottom)
                        & (boundary_y <= bounds.top)
                    )
                    if np.any(in_raster):
                        sampled_z = sample_elevations_from_raster(src, boundary_x[in_raster], boundary_y[in_raster])
                        boundary_z[in_raster] = np.where(
                            np.isnan(boundary_z[in_raster]), sampled_z, boundary_z[in_raster]
                        )
                        logger.info(f"Sampled {np.sum(in_raster)} boundary elevations from GeoTIFF")

                if guide_rings:
                    bounds = src.bounds
                    sampled_n = 0
                    for ring, ring_z in zip(guide_rings, guide_rings_z):
                        ring_xy = ring.xy
                        todo = np.isnan(ring_z)
                        in_raster = (
                            todo
                            & (ring_xy[:, 0] >= bounds.left)
                            & (ring_xy[:, 0] <= bounds.right)
                            & (ring_xy[:, 1] >= bounds.bottom)
                            & (ring_xy[:, 1] <= bounds.top)
                        )
                        if not np.any(in_raster):
                            continue
                        sampled_z = sample_elevations_from_raster(src, ring_xy[in_raster, 0], ring_xy[in_raster, 1])
                        ring_z[in_raster] = sampled_z
                        sampled_n += int(np.sum(in_raster))
                    if sampled_n:
                        logger.info("Sampled %d Bruchkante elevations from GeoTIFF", sampled_n)

        except Exception as e:
            logger.error(f"Error processing {path}: {e}")
            continue

    if not all_x:
        return TerrainMesh(vertices=[], faces=[], nullpunkt=None)

    x_coords = np.concatenate(all_x)
    y_coords = np.concatenate(all_y)
    z_values = np.concatenate(all_z)
    keep_z = ~invalid_z(z_values)
    if not np.all(keep_z):
        logger.info("Dropped %d interior points with nodata/fill Z", int((~keep_z).sum()))
        x_coords, y_coords, z_values = x_coords[keep_z], y_coords[keep_z], z_values[keep_z]

    logger.info(f"Combined {len(x_coords)} interior points from {len(tif_list)} files")

    if guide_rings:
        water_rings = [r for r in guide_rings if r.nutzart in WATER_EMPTY_INTERIOR]
        if water_rings:
            x_coords, y_coords, z_values = drop_points_inside_rings(
                x_coords, y_coords, z_values, water_rings
            )
        flatten_planar_water_z(guide_rings, guide_rings_z)
        smooth_flowing_water_z(guide_rings, guide_rings_z)
        if water_meshes is not None:
            shift = (bbox_utm[0], bbox_utm[1]) if (move_to_origin and bbox_utm is not None) else None
            water_meshes.update(build_water_polygon_meshes(guide_rings, guide_rings_z, origin_shift=shift))

    if bbox_utm is not None and boundary_x is not None and boundary_z is not None:
        x_coords, y_coords, z_values = filter_and_add_boundary(
            x_coords, y_coords, z_values, boundary_x, boundary_y, boundary_z, bbox_utm
        )

    if len(x_coords) < 3:
        logger.error("Not enough valid points for triangulation")
        return TerrainMesh(vertices=[], faces=[], nullpunkt=None)

    t_tri = time.perf_counter()
    if guide_rings:
        vertices, faces = generate_constrained_mesh(
            x_coords, y_coords, z_values, [r.xy for r in guide_rings], guide_rings_z
        )
        logger.info("Triangulation (CDT) took %.3f s", time.perf_counter() - t_tri)
    else:
        vertices, faces = generate_delaunay_mesh(x_coords, y_coords, z_values)
        logger.info("Triangulation (Delaunay) took %.3f s", time.perf_counter() - t_tri)
    if not vertices or not faces:
        return TerrainMesh(vertices=[], faces=[], nullpunkt=None)
    vertices, faces = drop_sliver_faces(vertices, faces)
    if not vertices or not faces:
        return TerrainMesh(vertices=[], faces=[], nullpunkt=None)
    if guide_rings:
        vertices = snap_vertices_to_planar_water_z(vertices, guide_rings, guide_rings_z)

    arr = np.array(vertices)
    arr[:, 0] = np.round(arr[:, 0], 6)
    arr[:, 1] = np.round(arr[:, 1], 6)
    arr[:, 2] = np.round(arr[:, 2], 4)

    if move_to_origin and bbox_utm is not None:
        arr[:, 0] -= bbox_utm[0]
        arr[:, 1] -= bbox_utm[1]
        nullpunkt: Tuple[float, float] = (0.0, 0.0)
    elif bbox_utm is not None:
        nullpunkt = (bbox_utm[0], bbox_utm[1])
    else:
        nullpunkt = (float(arr[:, 0].min()), float(arr[:, 1].min()))

    logger.info(f"Created mesh with {len(arr)} vertices and {len(faces)} faces")

    return TerrainMesh(vertices=arr.tolist(), faces=faces, nullpunkt=nullpunkt)


__all__ = [
    "DEFAULT_GUIDE_EDGE_SPACING_M",
    "GuideRing",
    "NUTZART_ORDER",
    "build_landuse_parts",
    "resolve_guide_records",
    "combine_terrain_meshes",
    "merge_parcel_meshes",
    "WATER_EMPTY_INTERIOR",
    "WATER_FLOWING",
    "WATER_PLANAR",
    "DEFAULT_FLOWING_WATER_WINDOW_M",
    "drop_sliver_faces",
    "drop_points_inside_rings",
    "flatten_planar_water_z",
    "smooth_flowing_water_z",
    "snap_vertices_to_planar_water_z",
    "build_water_polygon_meshes",
    "adaptive_sampling",
    "analyze_terrain_features",
    "collect_guide_rings",
    "collect_guide_xy",
    "generate_constrained_mesh",
    "split_mesh_by_nutzart",
    "subtract_rings_from_mesh",
    "cut_water_from_parts",
    "create_boundary_points",
    "extract_mesh_adaptive",
    "filter_and_add_boundary",
    "generate_delaunay_mesh",
    "is_url",
    "sample_elevations_from_raster",
]
