"""Pure data-processing helpers for terrain apps.

This module holds everything that turns raw GeoTIFF inputs into a
:class:`TerrainMesh` ready for IFC export: adaptive point sampling,
boundary stitching and Delaunay triangulation. No ``ifcopenshell`` calls
live here; all IFC-writing logic lives in each app's ``app.py``.

Public entry point:
    :func:`extract_mesh_adaptive` — feature-preserving adaptive sampling
    for one or more GeoTIFFs, returning a :class:`TerrainMesh`.
"""

from __future__ import annotations

from io import BytesIO
from pathlib import Path
from typing import Iterable, List, Optional, Tuple, Union

import numpy as np
import rasterio
from rasterio.io import MemoryFile
from scipy.spatial import Delaunay

from BIMFabrikHH_core.config.logging_colors import get_level_logger
from BIMFabrikHH_core.data_models.terrain_mesh import TerrainMesh

logger = get_level_logger("terrain_processing")


# ---------------------------------------------------------------------------
# URL / raster I/O helpers
# ---------------------------------------------------------------------------


def is_url(path: Union[str, Path]) -> bool:
    """Return ``True`` if ``path`` is an HTTP(S) URL."""
    return str(path).startswith(("http://", "https://"))


def download_to_memory(url: str, timeout: int = 120) -> Optional[BytesIO]:
    """Download a file from ``url`` into memory.

    Returns a :class:`BytesIO` buffer on success, ``None`` on failure.
    Requires ``requests``; it's imported lazily so callers that never
    touch URLs don't pay the import cost.
    """
    import requests

    try:
        logger.info(f"Downloading from: {url}")
        response = requests.get(url, timeout=timeout)
        response.raise_for_status()
        buffer = BytesIO(response.content)
        logger.info(f"Downloaded {len(response.content) / 1024 / 1024:.2f} MB to memory")
        return buffer
    except Exception as e:
        logger.error(f"Failed to download: {e}")
        return None


# ---------------------------------------------------------------------------
# Terrain-feature analysis + adaptive sampling
# ---------------------------------------------------------------------------


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

    Returns:
        ``(x_coords, y_coords, z_values)`` arrays in the raster CRS.
    """
    elevation_data = np.nan_to_num(elevation_data, nan=0.0)

    importance = analyze_terrain_features(elevation_data)

    importance_range = importance.max() - importance.min()
    if importance_range > 0:
        importance = (importance - importance.min()) / importance_range
    else:
        importance = np.ones_like(importance)

    height, width = elevation_data.shape
    x = np.linspace(transform[2], transform[2] + transform[0] * width, width)
    y = np.linspace(transform[5], transform[5] + transform[4] * height, height)
    x_grid, y_grid = np.meshgrid(x, y)

    mask = importance > importance_threshold

    if np.sum(mask) < min_points:
        flat_importance = importance.flatten()
        threshold = np.sort(flat_importance)[-min_points]
        mask = importance > threshold

    return x_grid[mask], y_grid[mask], elevation_data[mask]


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


def sample_elevations_from_raster(src, x_coords: np.ndarray, y_coords: np.ndarray) -> np.ndarray:
    """Sample elevation values directly from an open rasterio dataset.

    Points that fall outside the raster return ``NaN``.
    """
    coords = list(zip(x_coords, y_coords))
    samples = list(src.sample(coords))
    return np.array([s[0] if len(s) > 0 else np.nan for s in samples])


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


# ---------------------------------------------------------------------------
# Top-level extractor
# ---------------------------------------------------------------------------


def _open_geotiff(path: Union[str, Path]):
    """Open a GeoTIFF from a local path or URL.

    Returns a context manager yielding an open rasterio dataset.
    URL fetches are buffered entirely in memory via ``MemoryFile``.
    """
    if is_url(path):
        buffer = download_to_memory(str(path))
        if buffer is None:
            raise RuntimeError(f"Failed to download GeoTIFF: {path}")
        memfile = MemoryFile(buffer)
        return _MemoryFileContext(memfile)
    return rasterio.open(str(path))


class _MemoryFileContext:
    """Adapter that opens a rasterio ``MemoryFile`` as a dataset."""

    def __init__(self, memfile: MemoryFile) -> None:
        self._memfile = memfile
        self._src = None

    def __enter__(self):
        self._src = self._memfile.__enter__().open()
        return self._src

    def __exit__(self, exc_type, exc, tb):
        try:
            if self._src is not None:
                self._src.close()
        finally:
            return self._memfile.__exit__(exc_type, exc, tb)


def extract_mesh_adaptive(
    tif_files: Iterable[Union[str, Path]],
    *,
    folder_path: Optional[Union[str, Path]] = None,
    min_points: int = 1000,
    importance_threshold: float = 0.1,
    bbox_utm: Optional[Tuple[float, float, float, float]] = None,
    buffer_meters: float = 100.0,
    move_to_origin: bool = False,
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
    expanded_bbox: Optional[Tuple[float, float, float, float]] = None

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
            with _open_geotiff(path) as src:
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

        except Exception as e:
            logger.error(f"Error processing {path}: {e}")
            continue

    if not all_x:
        return TerrainMesh(vertices=[], faces=[], nullpunkt=None)

    x_coords = np.concatenate(all_x)
    y_coords = np.concatenate(all_y)
    z_values = np.concatenate(all_z)

    logger.info(f"Combined {len(x_coords)} interior points from {len(tif_list)} files")

    if bbox_utm is not None and boundary_x is not None and boundary_z is not None:
        x_coords, y_coords, z_values = filter_and_add_boundary(
            x_coords, y_coords, z_values, boundary_x, boundary_y, boundary_z, bbox_utm
        )

    if len(x_coords) < 3:
        logger.error("Not enough valid points for triangulation")
        return TerrainMesh(vertices=[], faces=[], nullpunkt=None)

    vertices, faces = generate_delaunay_mesh(x_coords, y_coords, z_values)
    if not vertices or not faces:
        return TerrainMesh(vertices=[], faces=[], nullpunkt=None)

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
    "adaptive_sampling",
    "analyze_terrain_features",
    "create_boundary_points",
    "download_to_memory",
    "extract_mesh_adaptive",
    "filter_and_add_boundary",
    "generate_delaunay_mesh",
    "is_url",
    "sample_elevations_from_raster",
]
